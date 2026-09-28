# -*- coding: utf-8 -*-
"""Разведка-2: сходится ли сальдо по счёту «Задолженность перед поставщиками»
из айко с колонкой «КЗ на 25.09.2026» в гугл-таблице."""
import sys, os, re, json, hashlib, warnings
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

def saldo(account, to_excl):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": ["Counteragent.Name"],
            "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
            "filters": {"DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                               "from": "2015-01-01", "to": to_excl,
                                               "includeLow": True, "includeHigh": False},
                        "Account.Name": {"filterType": "IncludeValues", "values": [account]}}}
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers=H, data=json.dumps(body),
               verify=False, timeout=900)
    r.raise_for_status()
    out = {}
    for x in r.json().get("data", []):
        n = (x.get("Counteragent.Name") or "").strip()
        if n: out[n] = (x.get("Sum.Incoming") or 0.0, x.get("Sum.Outgoing") or 0.0)
    return out

ETALON = {"Витамин+ ТОО": 27241484, "Глобал Фуд ТОО": 23613072, "Handy Yummy ИП": 10003160,
          "Иналка Фуд Сервис ТОО": 9258290, "Adolar Group ТОО": 7301854,
          "KazBeef Processing (КазБиф Процессинг) ТОО": 7250000, "Элита-Трейд ТОО": 6961875}

for acct in ("Задолженность перед поставщиками", "Авансы выданные", "5-Дебит.задолж."):
    d = saldo(acct, "2026-09-26")
    print(f"\n===== {acct}: контрагентов {len(d)} =====")
    tot_i = sum(v[0] for v in d.values()); tot_o = sum(v[1] for v in d.values())
    print(f"  всего приход {tot_i:,.0f}  расход {tot_o:,.0f}  разница {tot_i-tot_o:,.0f}".replace(",", " "))
    print("  — сверка с гугл-таблицей на 25.09 —")
    for n, e in ETALON.items():
        v = d.get(n)
        if not v:
            near = [k for k in d if k.split()[0].lower() in n.lower()][:2]
            print(f"   {n[:40]:<42} нет в айко   похожие: {near}")
            continue
        i, o = v
        print(f"   {n[:40]:<42} прих-расх {i-o:>15,.0f}   расх-прих {o-i:>15,.0f}   таблица {e:>13,.0f}".replace(",", " "))
    top = sorted(d.items(), key=lambda kv: -abs(kv[1][0]-kv[1][1]))[:10]
    print("  — крупнейшие сальдо —")
    for n,(i,o) in top:
        print(f"   {n[:44]:<46} {i-o:>16,.0f}".replace(",", " "))
