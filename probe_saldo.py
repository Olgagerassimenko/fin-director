# -*- coding: utf-8 -*-
"""Разведка: какие счета в айко держат расчёты с контрагентами."""
import sys, os, re, json, hashlib, warnings
from datetime import date
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"', src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"', src).group(1)

s = requests.Session()
tok = s.get(f"{URL}/resto/api/auth",
            params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
            verify=False, timeout=60).text.strip().strip('"')
H = {"Cookie": f"key={tok}", "Content-Type": "application/json"}

acc = s.get(f"{URL}/resto/api/v2/entities/accounts/list",
            params={"key": tok}, verify=False, timeout=120).json()
print(f"счетов всего: {len(acc)}\n")
pat = re.compile(r"поставщ|покупател|расч[её]т|контрагент|дебитор|кредитор|аванс", re.I)
for a in acc:
    n = a.get("name") or ""
    if pat.search(n):
        print(f"  {a.get('code','')!s:>8}  {n}   [{a.get('type')}]")

def olap(body):
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers=H, data=json.dumps(body),
               verify=False, timeout=600)
    r.raise_for_status()
    return r.json().get("data", [])

print("\n— обороты по счетам с контрагентами за 2026 —")
rows = olap({"reportType": "TRANSACTIONS", "buildSummary": "true",
             "groupByRowFields": ["Account.Name"],
             "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
             "filters": {"DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                                "from": "2026-01-01", "to": date.today().isoformat(),
                                                "includeLow": True, "includeHigh": True}}})
rows.sort(key=lambda x: -(abs(x.get("Sum.Incoming") or 0) + abs(x.get("Sum.Outgoing") or 0)))
for x in rows[:40]:
    print(f"  {x.get('Account.Name','')!s:<46} приход {x.get('Sum.Incoming') or 0:>18,.0f}   расход {x.get('Sum.Outgoing') or 0:>18,.0f}".replace(",", " "))
