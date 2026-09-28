# -*- coding: utf-8 -*-
"""
gen_zp.py — зарплата из iiko за месяц: по сотрудникам и по подразделениям.

Как устроена ЗП в iiko у завода:
  • счёт «Зарплата» (6.01, EXPENSES) — начисления по каждому человеку.
    Типы проводок: TARIFF_HOUR — почасовой тариф, EMPLOYEE_PAYMENT — фиксированная
    ставка (оклад), BONUS — премия, PENALTY — штраф (уменьшает начисление),
    CUSTOM — служебные и распределительные проводки без сотрудника;
  • счета подразделений — 2.1.ЗП Производство, 2.1.1.ЗП Зал, 2.5.2.ЗП ОтделПродаж,
    2.5.11.ЗП Доставка, 3.1.1.ЗП АУП: сюда ЗП разносится по статьям ОПиУ;
  • «Удержания из ЗП» (7.05) и налоги — отдельными счетами.

Период — переменные ZP_FROM / ZP_TO (ГГГГ-ММ-ДД, верхняя граница не включается),
по умолчанию август 2026. Только чтение.
Пишет зп_сотрудники.csv, зп_свод.csv, зп_LOG.txt.
"""
import sys, os, re, csv, json, hashlib, warnings
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

ZP_ACC   = "Зарплата"
DEPT_ACC = ["2.1.ЗП Производство", "2.1.1.ЗП Зал", "2.5.2.ЗП ОтделПродаж",
            "2.5.11.ЗП Доставка", "3.1.1.ЗП АУП", "1.Зарплата"]
OTHER    = ["Удержания из ЗП", "2.5.Налоги Производство", "3.1.4. Налоги АУП",
            "4-Подотчет", "Авансы выданные", "Доход от невыплаченной зп"]
TYPE_RU  = {"TARIFF_HOUR": "Тариф (часы)", "EMPLOYEE_PAYMENT": "Оклад (фикс)",
            "BONUS": "Премия", "PENALTY": "Штраф", "CUSTOM": "Прочее"}

LOG = open(os.path.join(HERE, "зп_LOG.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

s = requests.Session()
tok = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
            verify=False, timeout=60).text.strip().strip('"')
log("iiko ok. период: %s — %s (верхняя граница не включается)" % (D1, D2))

def olap(body):
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers={"Cookie": f"key={tok}", "Content-Type": "application/json"},
               data=json.dumps(body), verify=False, timeout=300)
    if r.status_code != 200: raise RuntimeError("OLAP %s: %s" % (r.status_code, r.text[:200]))
    return r.json().get("data", [])

RNG = {"filterType": "DateRange", "periodType": "CUSTOM", "from": D1.isoformat(), "to": D2.isoformat(),
       "includeLow": True, "includeHigh": False}

# ── 1. начисления по людям ──────────────────────────────────────────────
rows = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
             "groupByRowFields": ["Counteragent.Name", "TransactionType"],
             "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
             "filters": {"DateTime.DateTyped": RNG,
                         "Account.Name": {"filterType": "IncludeValues", "values": [ZP_ACC]}}})
emp = {}
for r0 in rows:
    nm = (r0.get("Counteragent.Name") or "").strip()
    if not nm: nm = "— без сотрудника (служебные проводки)"
    t = r0.get("TransactionType") or "?"
    v = (r0.get("Sum.Incoming") or 0) - (r0.get("Sum.Outgoing") or 0)
    emp.setdefault(nm, {}).setdefault(t, 0.0)
    emp[nm][t] += v
log("сотрудников со ЗП-проводками: %d, строк OLAP: %d" % (len(emp), len(rows)))

# ── 2. подразделение человека — по счёту, куда разнесена его ЗП ─────────
rows2 = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
              "groupByRowFields": ["Account.Name", "Counteragent.Name"],
              "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
              "filters": {"DateTime.DateTyped": RNG,
                          "Account.Name": {"filterType": "IncludeValues", "values": DEPT_ACC}}})
dept = {}
for r0 in rows2:
    nm = (r0.get("Counteragent.Name") or "").strip()
    a  = (r0.get("Account.Name") or "").strip()
    v  = abs((r0.get("Sum.Incoming") or 0) - (r0.get("Sum.Outgoing") or 0))
    if not nm or v <= 0: continue
    if nm not in dept or v > dept[nm][1]: dept[nm] = (a, v)
log("привязка к подразделению найдена для %d человек" % len(dept))

# ── 3. свод по счетам ───────────────────────────────────────────────────
rows3 = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
              "groupByRowFields": ["Account.Name"],
              "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
              "filters": {"DateTime.DateTyped": RNG,
                          "Account.Name": {"filterType": "IncludeValues", "values": DEPT_ACC + OTHER + [ZP_ACC]}}})

# ── файлы ───────────────────────────────────────────────────────────────
TYPES = ["EMPLOYEE_PAYMENT", "TARIFF_HOUR", "BONUS", "PENALTY", "CUSTOM"]
with open(os.path.join(HERE, "зп_сотрудники.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Сотрудник", "Подразделение"] + [TYPE_RU[t] for t in TYPES] + ["Итого начислено"])
    tot = {t: 0.0 for t in TYPES}; grand = 0.0
    for nm in sorted(emp, key=lambda x: -sum(emp[x].values())):
        d = dept.get(nm, ("", 0))[0]
        vals = [round(emp[nm].get(t, 0.0)) for t in TYPES]
        itg = round(sum(emp[nm].values()))
        for t, v in zip(TYPES, vals): tot[t] += v
        grand += itg
        w.writerow([nm, d] + vals + [itg])
    w.writerow(["ИТОГО", ""] + [round(tot[t]) for t in TYPES] + [round(grand)])
log("итого начислено по людям: %.0f" % grand)

with open(os.path.join(HERE, "зп_свод.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Счёт", "Приход", "Расход", "Сальдо"])
    for r0 in sorted(rows3, key=lambda x: -abs((x.get("Sum.Incoming") or 0) - (x.get("Sum.Outgoing") or 0))):
        i, o = r0.get("Sum.Incoming") or 0, r0.get("Sum.Outgoing") or 0
        w.writerow([r0.get("Account.Name"), round(i), round(o), round(i - o)])
        log("   %-28s приход %14.0f  расход %14.0f  сальдо %14.0f" % (str(r0.get("Account.Name"))[:28], i, o, i - o))

log("\nготово: зп_сотрудники.csv, зп_свод.csv")
