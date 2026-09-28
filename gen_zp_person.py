# -*- coding: utf-8 -*-
"""
gen_zp_person.py — личная карточка сотрудника по зарплате: все проводки
по всем счетам за период, без агрегации. Кого смотреть — ZP_WHO (часть ФИО).
Только чтение. Пишет зп_карточка.txt.
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
WHO = os.environ.get("ZP_WHO") or "Яковлев"
D1 = date.fromisoformat(os.environ.get("ZP_FROM") or "2026-06-01")
D2 = date.fromisoformat(os.environ.get("ZP_TO")   or "2026-09-01")

LOG = open(os.path.join(HERE, "зп_карточка.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

s = requests.Session()
tok = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
            verify=False, timeout=60).text.strip().strip('"')
log("КАРТОЧКА: «%s», период %s — %s (верхняя граница не включается)\n" % (WHO, D1, D2))

def olap(body):
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers={"Cookie": f"key={tok}", "Content-Type": "application/json"},
               data=json.dumps(body), verify=False, timeout=300)
    if r.status_code != 200: raise RuntimeError("OLAP %s: %s" % (r.status_code, r.text[:200]))
    return r.json().get("data", [])
RNG = {"filterType": "DateRange", "periodType": "CUSTOM", "from": D1.isoformat(), "to": D2.isoformat(),
       "includeLow": True, "includeHigh": False}

# 1. кто в справочнике подходит под имя
import xml.etree.ElementTree as ET
ROLE = {}
r = s.get(f"{URL}/resto/api/employees/roles", params={"key": tok}, verify=False, timeout=120)
if r.status_code == 200 and r.content.strip().startswith(b"<"):
    for e in ET.fromstring(r.content):
        if e.findtext("id"): ROLE[e.findtext("id")] = (e.findtext("name") or "").strip()
r = s.get(f"{URL}/resto/api/employees", params={"key": tok}, verify=False, timeout=180)
hits = []
for e in ET.fromstring(r.content):
    nm = (e.findtext("name") or "").strip()
    if WHO.lower() in nm.lower():
        hits.append((nm, e.findtext("code"), ROLE.get(e.findtext("mainRoleId") or "", ""),
                     e.findtext("hireDate"), e.findtext("deleted"), e.findtext("id")))
log("В СПРАВОЧНИКЕ СОТРУДНИКОВ — совпадений %d:" % len(hits))
for h in hits:
    log("   имя: %s" % h[0])
    log("      табельный %s | должность: %s" % (h[1], h[2]))
    log("      принят %s | удалён: %s | id %s" % (h[3], h[4], h[5]))

# 2. все проводки по этому контрагенту, помесячно, по счетам и типам
log("\nВСЕ ПРОВОДКИ ПО СЧЕТАМ (месяц × счёт × тип):")
rows = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
             "groupByRowFields": ["DateTime.DateTyped.Month", "Account.Name", "TransactionType"],
             "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
             "filters": {"DateTime.DateTyped": RNG}})
mine = [x for x in rows]
# фильтр по контрагенту делаем вторым запросом — с группировкой по контрагенту
rows = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
             "groupByRowFields": ["Counteragent.Name", "DateTime.DateTyped.Month", "Account.Name", "TransactionType"],
             "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
             "filters": {"DateTime.DateTyped": RNG}})
mine = [x for x in rows if WHO.lower() in str(x.get("Counteragent.Name") or "").lower()]
if not mine:
    log("   проводок не найдено")
for x in sorted(mine, key=lambda y: (str(y.get("DateTime.DateTyped.Month")), str(y.get("Account.Name")))):
    log("   %-10s %-28s %-26s вх %12.0f  исх %12.0f" % (
        str(x.get("DateTime.DateTyped.Month"))[:10], str(x.get("Account.Name"))[:28],
        str(x.get("TransactionType"))[:26], x.get("Sum.Incoming") or 0, x.get("Sum.Outgoing") or 0))

# 3. по дням — детально
log("\nПО ДНЯМ:")
rows = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
             "groupByRowFields": ["Counteragent.Name", "DateTime.DateTyped", "Account.Name", "TransactionType"],
             "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
             "filters": {"DateTime.DateTyped": RNG}})
mine = [x for x in rows if WHO.lower() in str(x.get("Counteragent.Name") or "").lower()]
for x in sorted(mine, key=lambda y: str(y.get("DateTime.DateTyped"))):
    log("   %-12s %-28s %-24s вх %12.0f  исх %12.0f" % (
        str(x.get("DateTime.DateTyped"))[:12], str(x.get("Account.Name"))[:28],
        str(x.get("TransactionType"))[:24], x.get("Sum.Incoming") or 0, x.get("Sum.Outgoing") or 0))

# 4. остатки на границы периода по всем счетам
ACC = {a["id"]: (a.get("name") or "") for a in
       s.get(f"{URL}/resto/api/v2/entities/accounts/list", params={"key": tok}, verify=False, timeout=120).json()}
ids = {h[5] for h in hits}
for dt in (D1, D2):
    js = s.get(f"{URL}/resto/api/v2/reports/balance/counteragents",
               params={"key": tok, "timestamp": dt.strftime("%Y-%m-%dT00:00:00")}, verify=False, timeout=240).json()
    log("\nОСТАТКИ НА %s:" % dt)
    found = False
    for x in js:
        if x.get("counteragent") in ids and abs(x.get("sum") or 0) > 0.5:
            log("   %-34s %14.0f" % (ACC.get(x.get("account"), "?")[:34], x.get("sum") or 0)); found = True
    if not found: log("   остатков нет")
log("\nготово")
