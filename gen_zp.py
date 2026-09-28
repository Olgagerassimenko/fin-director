# -*- coding: utf-8 -*-
"""
gen_zp.py — платёжная ведомость по зарплате из iiko за месяц, с градацией ШР.

Что собирает по каждому человеку — ровно те колонки, что в ведомости iiko:
  табельный номер, должность, остаток на начало, начислено, удержано,
  выплачено, остаток на конец.

Откуда:
  • остатки на начало и конец — /reports/balance/counteragents на дату,
    по счёту «Зарплата» (6.01);
  • начислено и удержано — проводки по счёту «Зарплата» за период:
    EMPLOYEE_PAYMENT — оклад (фикс), TARIFF_HOUR — тариф по часам,
    BONUS — премия, PENALTY — штраф;
  • выплачено выводится из тождества ведомости:
    остаток на начало + начислено − удержано − выплачено = остаток на конец;
  • должность — роль сотрудника в iiko, в том же виде «Подразделение/ Должность»,
    что в ведомости;
  • категория A/B/C/D — из файла зп_категории.csv, собранного с листа «ШР ЭТАЛОН»:
    A — топ-менеджмент, B — АУП, C — АУП производство, D — сотрудники.

Период — ZP_FROM / ZP_TO (ГГГГ-ММ-ДД, верхняя граница не включается).
Только чтение. Пишет зп_сотрудники.csv, зп_свод.csv, зп_LOG.txt.
"""
import sys, os, re, csv, json, hashlib, warnings
import xml.etree.ElementTree as ET
from datetime import date
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"',   src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"',  src).group(1)

D1 = date.fromisoformat(os.environ.get("ZP_FROM") or "2026-08-01")
D2 = date.fromisoformat(os.environ.get("ZP_TO")   or "2026-09-01")
ZP_ACC = "Зарплата"
GRP = {"A": "Топ-менеджмент", "B": "АУП", "C": "АУП производство", "D": "Сотрудники"}

LOG = open(os.path.join(HERE, "зп_LOG.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

s = requests.Session()
tok = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
            verify=False, timeout=60).text.strip().strip('"')
log("iiko ok. период: %s — %s" % (D1, D2))

# ── справочник категорий из ШР ──────────────────────────────────────────
KAT = {}
def nk(x): return re.sub(r"\s+", " ", (x or "").replace(" ", " ")).strip().lower()
p = os.path.join(HERE, "зп_категории.csv")
if os.path.exists(p):
    for row in list(csv.reader(open(p, encoding="utf-8-sig"), delimiter=";"))[1:]:
        if len(row) >= 2 and row[0].strip(): KAT[nk(row[0])] = row[1].strip().upper()
log("категорий из ШР: %d" % len(KAT))

# ── роли (должности) ────────────────────────────────────────────────────
ROLE = {}
for ep in ("/resto/api/employees/roles", "/resto/api/v2/employees/roles"):
    try:
        r = s.get(f"{URL}{ep}", params={"key": tok}, verify=False, timeout=120)
        if r.status_code == 200 and r.content.strip().startswith(b"<"):
            for e in ET.fromstring(r.content):
                i = e.findtext("id"); n = e.findtext("name")
                if i and n: ROLE[i] = n.strip()
            if ROLE: log("роли: %d (через %s)" % (len(ROLE), ep)); break
    except Exception as e:
        log("роли %s: %s" % (ep, e))

# ── сотрудники ──────────────────────────────────────────────────────────
EMP = {}
r = s.get(f"{URL}/resto/api/employees", params={"key": tok}, verify=False, timeout=180)
for e in ET.fromstring(r.content):
    nm = (e.findtext("name") or "").strip()
    if not nm: continue
    EMP[nk(nm)] = {"name": nm, "code": (e.findtext("code") or "").strip(),
                   "role": ROLE.get(e.findtext("mainRoleId") or "", ""),
                   "deleted": (e.findtext("deleted") or "").strip() == "true",
                   "id": e.findtext("id")}
log("сотрудников в справочнике: %d" % len(EMP))

# ── остатки по счёту «Зарплата» на дату ─────────────────────────────────
ACC = {a["id"]: (a.get("name") or "") for a in
       s.get(f"{URL}/resto/api/v2/entities/accounts/list", params={"key": tok}, verify=False, timeout=120).json()}
ZP_IDS = {i for i, n in ACC.items() if n == ZP_ACC}
CA = {}
try:
    for c in s.get(f"{URL}/resto/api/v2/entities/list", params={"key": tok, "rootType": "Supplier"},
                   verify=False, timeout=180).json():
        CA[c.get("id")] = (c.get("name") or "").strip()
except Exception as e:
    log("контрагенты: %s" % e)
log("счетов «Зарплата»: %d, контрагентов: %d" % (len(ZP_IDS), len(CA)))

def bal(d):
    js = s.get(f"{URL}/resto/api/v2/reports/balance/counteragents",
               params={"key": tok, "timestamp": d.strftime("%Y-%m-%dT00:00:00")},
               verify=False, timeout=240).json()
    out = {}
    for x in js:
        if x.get("account") in ZP_IDS:
            nm = CA.get(x.get("counteragent")) or ""
            if nm: out[nk(nm)] = out.get(nk(nm), 0.0) + (x.get("sum") or 0)
    return out
B1, B2 = bal(D1), bal(D2)
log("остатки: на начало %d чел, на конец %d чел" % (len(B1), len(B2)))

# ── начисления и удержания за период ────────────────────────────────────
def olap(body):
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers={"Cookie": f"key={tok}", "Content-Type": "application/json"},
               data=json.dumps(body), verify=False, timeout=300)
    if r.status_code != 200: raise RuntimeError("OLAP %s: %s" % (r.status_code, r.text[:200]))
    return r.json().get("data", [])

rows = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
             "groupByRowFields": ["Counteragent.Name", "TransactionType"],
             "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
             "filters": {"DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                                "from": D1.isoformat(), "to": D2.isoformat(),
                                                "includeLow": True, "includeHigh": False},
                         "Account.Name": {"filterType": "IncludeValues", "values": [ZP_ACC]}}})
MOVE = {}
for r0 in rows:
    nm = (r0.get("Counteragent.Name") or "").strip()
    if not nm: continue
    t = r0.get("TransactionType") or "?"
    MOVE.setdefault(nk(nm), {"name": nm})
    MOVE[nk(nm)][t] = MOVE[nk(nm)].get(t, 0.0) + (r0.get("Sum.Incoming") or 0) - (r0.get("Sum.Outgoing") or 0)

keys = set(MOVE) | set(B1) | set(B2)
log("человек в ведомости: %d" % len(keys))

# ── файл по сотрудникам ─────────────────────────────────────────────────
noKat = {}
out = []
for k in keys:
    m = MOVE.get(k, {})
    e = EMP.get(k, {})
    nm = m.get("name") or e.get("name") or k
    role = e.get("role", "")
    kat = KAT.get(nk(role), "")
    if role and not kat: noKat[role] = noKat.get(role, 0) + 1
    okl = round(m.get("EMPLOYEE_PAYMENT", 0.0))
    tar = round(m.get("TARIFF_HOUR", 0.0))
    bon = round(m.get("BONUS", 0.0))
    pen = round(-m.get("PENALTY", 0.0))          # штраф приходит со знаком минус
    nach = okl + tar + bon
    b1, b2 = round(B1.get(k, 0.0)), round(B2.get(k, 0.0))
    vyp = round(b1 + nach - pen - b2)
    out.append([nm, e.get("code", ""), role, kat, GRP.get(kat, ""), okl, tar, bon, nach, pen, vyp, b1, b2])

order = {"A": 0, "B": 1, "C": 2, "D": 3, "": 4}
out.sort(key=lambda x: (order.get(x[3], 4), -x[8]))
HEAD = ["Сотрудник", "Табельный номер", "Должность", "Категория", "Группа",
        "Оклад (фикс)", "Тариф (часы)", "Премия", "НАЧИСЛЕНО", "Удержано",
        "Выплачено", "Остаток на начало", "Остаток на конец"]
with open(os.path.join(HERE, "зп_сотрудники.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(HEAD)
    for r0 in out: w.writerow(r0)
    tot = ["ИТОГО", "", "", "", ""] + [sum(r0[i] for r0 in out) for i in range(5, 13)]
    w.writerow(tot)
log("начислено всего: %s, удержано %s, выплачено %s" % (tot[8], tot[9], tot[10]))

# ── свод по категориям ──────────────────────────────────────────────────
with open(os.path.join(HERE, "зп_свод.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Категория", "Группа", "Человек", "Оклад (фикс)", "Тариф (часы)", "Премия",
                "НАЧИСЛЕНО", "Удержано", "Выплачено", "Доля в начислениях"])
    all_n = sum(r0[8] for r0 in out) or 1
    for k in ["A", "B", "C", "D", ""]:
        g = [r0 for r0 in out if r0[3] == k]
        if not g: continue
        w.writerow([k or "—", GRP.get(k, "без категории"), len(g)] +
                   [sum(r0[i] for r0 in g) for i in (5, 6, 7, 8, 9, 10)] +
                   ["%.1f%%" % (100.0 * sum(r0[8] for r0 in g) / all_n)])
        log("   %-18s %3d чел, начислено %12d" % (GRP.get(k, "без категории"), len(g), sum(r0[8] for r0 in g)))

if noKat:
    log("\nДОЛЖНОСТИ БЕЗ КАТЕГОРИИ В ШР (%d):" % len(noKat))
    for r0, c in sorted(noKat.items(), key=lambda x: -x[1])[:40]: log("   %-70s %d чел" % (r0[:70], c))
log("\nготово")
