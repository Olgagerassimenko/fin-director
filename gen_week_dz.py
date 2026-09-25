# -*- coding: utf-8 -*-
"""
gen_week_dz.py — отгрузка и поступление ДС по контрагентам за одну неделю,
в порядке строк листа «ДЗ-» таблицы «Баланс по поставщикам и дебиторам».

Зачем: колонки «Отгрузка с ДД.ММ по ДД.ММ» и «Поступление ДС с ДД.ММ по ДД.ММ»
в этой таблице заполняются руками. Скрипт собирает обе колонки из iiko и
кладёт рядом с названиями контрагентов ровно в том порядке, в котором они
идут в таблице, — остаётся вставить два столбца.

Откуда что берётся:
  • отгрузка   — проводки OUTGOING_INVOICE_REVENUE минус возвраты
                 INCOMING_RETURNED_INVOICE_REVENUE (так же считает iiko_export.py);
  • поступление — приход на денежные счета по статье «1.Выручка»
                 (та же логика, что revenue_by_contr в dds_pryamoy.py).

Период задаётся переменными окружения WEEK_FROM и WEEK_TO (ГГГГ-ММ-ДД),
верхняя граница НЕ включается. По умолчанию — прошедшая неделя сб–пт.

Только чтение. Пишет неделя_дз.csv и неделя_дз_LOG.txt.
"""
import sys, os, re, csv, io, json, hashlib, warnings
from datetime import date, timedelta, datetime
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"',   src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"',  src).group(1)

SHEET_ID = "13iFd16Hah1Yi5y2QptmyUrw51rSFfAmtnzhf0U2g_wc"
DZ_GID   = "597090672"
DEPT     = "Фуд завод"
REVCAT   = "1.Выручка"
ACTIVE   = ["99Главная касса", "Касса Взаиморасчеты", "ФЗ Айдана каспи", "ФЗ Жусан Банк",
            "ФЗ Каспи", "ФЗ Каспи копилка", "ФЗ РБК Каламкас", "Цой Д.Л.Каспи",
            "ФЗ Ермагамбет отдел продаж"]
SHIP_T   = ["OUTGOING_INVOICE_REVENUE"]
RET_T    = ["INCOMING_RETURNED_INVOICE_REVENUE"]

LOG = open(os.path.join(HERE, "неделя_дз_LOG.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a)
    print(t); LOG.write(t + "\n"); LOG.flush()

def week_bounds():
    f, t = os.environ.get("WEEK_FROM"), os.environ.get("WEEK_TO")
    if f and t:
        return date.fromisoformat(f), date.fromisoformat(t)
    today = date.today()
    fri = today - timedelta(days=(today.weekday() - 4) % 7 or 7)   # последняя прошедшая пятница
    return fri - timedelta(days=6), fri + timedelta(days=1)

D1, D2 = week_bounds()
log("период: с %s по %s включительно" % (D1.strftime("%d.%m.%Y"), (D2 - timedelta(days=1)).strftime("%d.%m.%Y")))

s = requests.Session()
tok = s.get(f"{URL}/resto/api/auth",
            params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
            verify=False, timeout=60).text.strip().strip('"')
log("iiko: авторизация ok")

def olap(body):
    r = s.post(f"{URL}/resto/api/v2/reports/olap",
               headers={"Cookie": f"key={tok}", "Content-Type": "application/json"},
               data=json.dumps(body), verify=False, timeout=300)
    if r.status_code != 200:
        raise RuntimeError("OLAP %s: %s" % (r.status_code, r.text[:300]))
    return r.json().get("data", [])

def rng():
    return {"filterType": "DateRange", "periodType": "CUSTOM",
            "from": D1.isoformat(), "to": D2.isoformat(),
            "includeLow": True, "includeHigh": False}

def by_contr_ship(types):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": ["Counteragent.Name"],
            "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
            "filters": {"DateTime.DateTyped": rng(),
                        "Department": {"filterType": "IncludeValues", "values": [DEPT]},
                        "TransactionType": {"filterType": "IncludeValues", "values": types}}}
    out = {}
    for row in olap(body):
        nm = (row.get("Counteragent.Name") or "").strip()
        v = (row.get("Sum.Incoming") or 0) - (row.get("Sum.Outgoing") or 0)
        if nm: out[nm] = out.get(nm, 0.0) + v
    return out

def by_contr_pay():
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": ["Counteragent.Name"],
            "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
            "filters": {"DateTime.DateTyped": rng(),
                        "Department": {"filterType": "IncludeValues", "values": [DEPT]},
                        "Account.Name": {"filterType": "IncludeValues", "values": ACTIVE},
                        "CashFlowCategory": {"filterType": "IncludeValues", "values": [REVCAT]}}}
    out = {}
    for row in olap(body):
        nm = (row.get("Counteragent.Name") or "").strip()
        v = (row.get("Sum.Incoming") or 0) - (row.get("Sum.Outgoing") or 0)
        if nm: out[nm] = out.get(nm, 0.0) + v
    return out

ship = by_contr_ship(SHIP_T)
rets = by_contr_ship(RET_T)
for k, v in rets.items():
    ship[k] = ship.get(k, 0.0) - v
pay = by_contr_pay()
log("iiko: отгрузка по %d контрагентам, поступления по %d" % (len(ship), len(pay)))

# ── порядок строк берём из самой таблицы ────────────────────────────────
r = requests.get(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={DZ_GID}", timeout=60)
r.raise_for_status()
try:    text = r.content.decode("utf-8-sig")
except Exception: text = r.content.decode("cp1251", errors="replace")
rows = list(csv.reader(io.StringIO(text)))
log("таблица: %d строк" % len(rows))

def norm(x):
    x = (x or "").replace("\xa0", " ").strip().lower()
    return re.sub(r"\s+", " ", x)

SHIP_N = {norm(k): v for k, v in ship.items()}
PAY_N  = {norm(k): v for k, v in pay.items()}

out_rows, hit_s, hit_p = [], set(), set()
for i, row in enumerate(rows):
    nm = (row[0] if row else "").strip()
    n = norm(nm)
    if not n:
        out_rows.append([i + 1, nm, "", ""]); continue
    sv, pv = SHIP_N.get(n), PAY_N.get(n)
    if sv is not None: hit_s.add(n)
    if pv is not None: hit_p.add(n)
    out_rows.append([i + 1, nm,
                     "" if sv is None else round(sv, 2),
                     "" if pv is None else round(pv, 2)])

with open(os.path.join(HERE, "неделя_дз.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["строка", "контрагент",
                "Отгрузка с %s по %s" % (D1.strftime("%d.%m.%Y"), (D2 - timedelta(days=1)).strftime("%d.%m.%Y")),
                "Поступление ДС с %s по %s" % (D1.strftime("%d.%m.%Y"), (D2 - timedelta(days=1)).strftime("%d.%m.%Y"))])
    w.writerows(out_rows)

miss_s = sorted(set(SHIP_N) - hit_s)
miss_p = sorted(set(PAY_N) - hit_p)
log("сопоставлено: отгрузка %d из %d, поступления %d из %d" % (len(hit_s), len(SHIP_N), len(hit_p), len(PAY_N)))
if miss_s:
    log("\nЕСТЬ В IIKO, НЕТ В ТАБЛИЦЕ — отгрузка:")
    for n in miss_s: log("   %-55s %15.2f" % (n[:55], SHIP_N[n]))
if miss_p:
    log("\nЕСТЬ В IIKO, НЕТ В ТАБЛИЦЕ — поступления:")
    for n in miss_p: log("   %-55s %15.2f" % (n[:55], PAY_N[n]))
log("\nитого отгрузка %.2f, поступления %.2f" % (sum(ship.values()), sum(pay.values())))
log("готово: неделя_дз.csv")
