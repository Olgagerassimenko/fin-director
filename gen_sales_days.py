# -*- coding: utf-8 -*-
"""
gen_sales_days.py — выручка по дням из айко, для ежедневного план-факта.

Зачем отдельный файл. contractor_items.js даёт помесячные итоги: по ним
видно, выполнен ли план за месяц, но не видно, в какой день мы от него
отстали. Здесь тот же показатель, что и везде на «Продажах», — выручка
расходных накладных за вычетом возвратов, — но с разбивкой по дням.

Формат: window.SALES_DAYS = {"2026-09-01": 9123456, ...}. Только дни с
движением; страница сама раскладывает их по календарю месяца.
"""
import sys, os, re, json, hashlib, warnings
from datetime import date, timedelta
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import almaty

src = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL     = re.search(r'URL\s*=\s*"([^"]+)"', src).group(1)
LOGIN   = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS    = re.search(r'PASS\s*=\s*"([^"]+)"', src).group(1)
REVENUE = re.search(r'REVENUE_TYPE_CODE\s*=\s*"([^"]+)"', src).group(1)
RETURN  = re.search(r'RETURN_TYPE_CODE\s*=\s*"([^"]+)"', src).group(1)

YEAR   = 2026
OUTPUT = "sales_days.js"


def auth():
    s = requests.Session()
    tok = s.get(f"{URL}/resto/api/auth",
                params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
                verify=False, timeout=60).text.strip().strip('"')
    return s, {"Cookie": f"key={tok}", "Content-Type": "application/json"}


def by_day(s, H, types, d_from, d_to_excl):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": ["DateTime.DateTyped"],
            "aggregateFields": ["Sum.Incoming"],
            "filters": {
                "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                       "from": d_from.isoformat(), "to": d_to_excl.isoformat(),
                                       "includeLow": True, "includeHigh": False},
                "TransactionType": {"filterType": "IncludeValues", "values": types}}}
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers=H, data=json.dumps(body),
               verify=False, timeout=900)
    if r.status_code != 200:
        raise RuntimeError(f"OLAP {r.status_code}: {r.text[:300]}")
    out = {}
    for x in r.json().get("data", []):
        d = str(x.get("DateTime.DateTyped") or "")[:10]
        if d:
            out[d] = out.get(d, 0.0) + (x.get("Sum.Incoming") or 0.0)
    return out


def main():
    today = almaty.now().date()
    d1 = date(YEAR, 1, 1)
    d2 = today + timedelta(days=1)          # верхняя граница в айко исключающая

    s, H = auth()
    rev = by_day(s, H, [REVENUE], d1, d2)
    ret = by_day(s, H, [RETURN], d1, d2)

    days = {}
    for d in set(list(rev.keys()) + list(ret.keys())):
        v = round(rev.get(d, 0.0) - ret.get(d, 0.0))
        if v:
            days[d] = v

    data = {k: days[k] for k in sorted(days)}
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("window.SALES_DAYS = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")

    tot = sum(data.values())
    last = sorted(data)[-5:] if data else []
    print(f"дней с выручкой: {len(data)}, итого {tot:,.0f} ₸".replace(",", " "))
    for d in last:
        print(f"   {d}  {data[d]:,.0f}".replace(",", " "))
    print(f"{OUTPUT}: {os.path.getsize(OUTPUT):,} байт".replace(",", " "))


if __name__ == "__main__":
    main()
