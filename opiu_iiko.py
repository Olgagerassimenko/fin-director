# -*- coding: utf-8 -*-
"""
opiu_iiko.py — тянет выручку ОПиУ НАПРЯМУЮ из iiko по месяцам и пишет opiu_rev.js
для блока «Сверка с ОПиУ» на дашборде «Продажи». Только чтение, iiko не меняет.

Источник — доходные счета (Account.Type=INCOME) подразделения «Фуд завод»:
  Торговая выручка = крупнейший доходный счёт (расходные накладные),
  Итого выручка    = сумма всех доходных счетов (торговая + прочая).
Логин берётся из iiko_export.py (секреты не дублируются).
Запускается в пайплайне (GitHub Actions), где iiko доступен.
"""
import os, re, json, time, hashlib, calendar, warnings
from datetime import date, timedelta
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import almaty  # время завода — Алматы (UTC+5), не UTC раннера

warnings.filterwarnings("ignore")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"',   src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"',  src).group(1)
YEAR  = 2026
FZ_DEPT = "Фуд завод"

s = requests.Session()

def auth():
    r = s.get(f"{URL}/resto/api/auth",
              params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
              verify=False, timeout=60)
    r.raise_for_status()
    return r.text.strip().strip('"')

def olap(body, tries=4):
    last = None
    for i in range(tries):
        try:
            r = s.post(f"{URL}/resto/api/v2/reports/olap",
                       headers={"Cookie": f"key={TOK}", "Content-Type": "application/json"},
                       data=json.dumps(body), verify=False, timeout=300)
            if r.status_code == 200:
                return r.json().get("data", [])
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(3 * (i + 1))
    print(f"[!] OLAP не ответил: {last}")
    return None

def opiu_income(mi, last_full):
    d1 = date(YEAR, mi, 1)
    d2 = min(date(YEAR, mi, calendar.monthrange(YEAR, mi)[1]), last_full)
    body = {
        "reportType": "TRANSACTIONS", "buildSummary": "true",
        "groupByRowFields": ["Account.Name", "Account.Type"],
        "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
        "filters": {
            "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                   "from": d1.isoformat(),
                                   "to": (d2 + timedelta(days=1)).isoformat(),
                                   "includeLow": True, "includeHigh": True},
            "Department": {"filterType": "IncludeValues", "values": [FZ_DEPT]},
            "Account.Type": {"filterType": "IncludeValues", "values": ["INCOME"]},
        },
    }
    data = olap(body)
    if data is None:
        return None
    accs = {}
    for row in data:
        nm = (row.get("Account.Name") or "—").strip()
        val = -((row.get("Sum.Incoming") or 0) - (row.get("Sum.Outgoing") or 0))  # кредитовый оборот
        if abs(val) < 0.5:
            continue
        accs[nm] = accs.get(nm, 0.0) + val
    return accs

def main():
    global TOK
    TOK = auth()
    # date.today() на раннере — это UTC: с 00:00 до 05:00 по Алматы
    # «последний полный день» съезжал на сутки назад и терял день выручки.
    last_full = almaty.today() - timedelta(days=1)
    print(f"iiko ok, ОПиУ по {last_full:%d.%m.%Y}")
    out = {}
    for mi in range(1, 13):
        if date(YEAR, mi, 1) > last_full:
            break
        accs = opiu_income(mi, last_full)
        if not accs:
            continue
        itogo = round(sum(accs.values()))
        trade = round(max(accs.values()))
        d2 = min(date(YEAR, mi, calendar.monthrange(YEAR, mi)[1]), last_full)
        out[f"{YEAR}-{mi:02d}"] = {"trade": trade, "itogo": itogo, "through": d2.isoformat()}
        print(f"  {mi:02d}: торговая {trade:,}  итого {itogo:,}")
    out["_pulled"] = almaty.today().strftime("%d.%m.%Y")
    out["_through"] = last_full.isoformat()
    with open(os.path.join(HERE, "opiu_rev.js"), "w", encoding="utf-8") as f:
        f.write("window.OPIU_REV=" + json.dumps(out, ensure_ascii=False) + ";\n")
    print("записан opiu_rev.js")

if __name__ == "__main__":
    main()
