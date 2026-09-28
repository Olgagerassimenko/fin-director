# -*- coding: utf-8 -*-
"""
gen_zp.py — разведка по зарплате в iiko: что вообще есть.
Первый прогон только смотрит и пишет зп_РАЗВЕДКА.txt, ничего не считает набело.
"""
import sys, os, re, json, hashlib, warnings
from datetime import date
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"',   src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"',  src).group(1)
D1, D2 = date(2026, 8, 1), date(2026, 9, 1)

LOG = open(os.path.join(HERE, "зп_РАЗВЕДКА.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

s = requests.Session()
tok = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
            verify=False, timeout=60).text.strip().strip('"')
log("iiko ok, период %s — %s" % (D1, D2))

# 1. счета, похожие на зарплатные
try:
    acc = s.get(f"{URL}/resto/api/v2/entities/accounts/list", params={"key": tok}, verify=False, timeout=120).json()
    log("\n=== СЧЕТА со словом зарплат/зп/оплат труда (всего счетов %d)" % len(acc))
    for a in acc:
        n = (a.get("name") or "")
        if re.search(r"зарплат|з/п|\bзп\b|оплат[аы] труда|аванс|подотчёт|подотчет", n, re.I):
            log("   %-45s тип=%-18s код=%s" % (n[:45], a.get("type"), a.get("code")))
except Exception as e:
    log("счета: ошибка %s" % e)

# 2. сотрудники
for ep in ("/resto/api/employees", "/resto/api/v2/employees"):
    try:
        r = s.get(f"{URL}{ep}", params={"key": tok}, verify=False, timeout=120)
        log("\n=== %s -> %s, %d байт" % (ep, r.status_code, len(r.content)))
        if r.status_code == 200:
            txt = r.text[:1500]
            log(txt.replace("\n", " ")[:1500])
    except Exception as e:
        log("%s: ошибка %s" % (ep, e))

# 3. OLAP по зарплатному счёту за август: кто, сколько, каким типом проводки
def olap(body):
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers={"Cookie": f"key={tok}", "Content-Type": "application/json"},
               data=json.dumps(body), verify=False, timeout=300)
    return r.json().get("data", []) if r.status_code == 200 else [{"ОШИБКА": r.status_code, "текст": r.text[:200]}]

rng = {"filterType": "DateRange", "periodType": "CUSTOM", "from": D1.isoformat(), "to": D2.isoformat(),
       "includeLow": True, "includeHigh": False}

log("\n=== OLAP: счёт «Зарплата», группировка сотрудник × тип проводки")
rows = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
             "groupByRowFields": ["Counteragent.Name", "TransactionType"],
             "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
             "filters": {"DateTime.DateTyped": rng,
                         "Account.Name": {"filterType": "IncludeValues", "values": ["Зарплата"]}}})
log("строк: %d" % len(rows))
for r0 in rows[:60]:
    log("   %s" % json.dumps(r0, ensure_ascii=False)[:200])

log("\n=== OLAP: все счета, где в августе есть проводки с сотрудниками (топ по обороту)")
rows2 = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
              "groupByRowFields": ["Account.Name"],
              "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
              "filters": {"DateTime.DateTyped": rng}})
rows2 = [x for x in rows2 if re.search(r"зарплат|зп|труд|аванс|налог|удержан|питан", str(x.get("Account.Name") or ""), re.I)]
for r0 in sorted(rows2, key=lambda x: -(abs(x.get("Sum.Incoming") or 0) + abs(x.get("Sum.Outgoing") or 0)))[:40]:
    log("   %-50s вх %14.0f  исх %14.0f" % (str(r0.get("Account.Name"))[:50],
                                             r0.get("Sum.Incoming") or 0, r0.get("Sum.Outgoing") or 0))
log("\nготово")
