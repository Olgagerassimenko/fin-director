# -*- coding: utf-8 -*-
"""
Проверка данных за май и июнь 2026 в iiko.
Ищем правильный endpoint для склада (расходные накладные).
"""
import requests, hashlib, warnings, json, re
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1}, verify=False, timeout=30)
token = r.text.strip().strip('"')
H = {"Cookie": f"key={token}", "Content-Type": "application/json"}
print(f"Auth OK\n")

def olap(rt, groups, aggs, date_from, date_to):
    body = {
        "reportType": rt,
        "buildSummary": "false",
        "groupByRowFields": groups,
        "groupByColFields": [],
        "aggregateFields": aggs,
        "filters": {
            "OpenDate.Typed": {
                "filterType": "DateRange", "periodType": "CUSTOM",
                "from": date_from, "to": date_to,
                "includeLow": "true", "includeHigh": "true"
            }
        }
    }
    r2 = s.post(f"{URL}/resto/api/v2/reports/olap", json=body, headers=H, verify=False, timeout=60)
    if not r2.ok:
        return None, r2.text[:200]
    d = r2.json()
    rows = d.get('data', d) if isinstance(d, dict) else d
    return (rows if isinstance(rows, list) else []), ""

# ── 1. Проверяем SALES за каждый месяц ──
print("=== SALES — сколько строк возвращает по месяцам? ===")
months = [
    ("Январь",  "2026-01-01", "2026-01-31"),
    ("Февраль", "2026-02-01", "2026-02-28"),
    ("Март",    "2026-03-01", "2026-03-31"),
    ("Апрель",  "2026-04-01", "2026-04-30"),
    ("Май",     "2026-05-01", "2026-05-31"),
    ("Июнь",    "2026-06-01", "2026-06-30"),
]
for lbl, frm, to in months:
    rows, err = olap("SALES", ["DishCategory","DishName"], ["DishDiscountSumInt","DishAmountInt"], frm, to)
    if rows is None:
        print(f"  {lbl}: ОШИБКА — {err[:60]}")
    else:
        total = sum(abs(float(r.get('DishDiscountSumInt',0) or 0)) for r in rows if isinstance(r,dict))
        print(f"  {lbl}: {len(rows)} строк, сумма={total/1e6:.1f}М")

# ── 2. TRANSACTIONS без даты — смотрим тип транзакций ──
print("\n=== TRANSACTIONS — виды транзакций (без фильтра даты) ===")
body2 = {
    "reportType": "TRANSACTIONS",
    "buildSummary": "false",
    "groupByRowFields": ["TransactionType"],
    "groupByColFields": [],
    "aggregateFields": ["Amount"],
    "filters": {}
}
r2 = s.post(f"{URL}/resto/api/v2/reports/olap", json=body2, headers=H, verify=False, timeout=60)
if r2.ok:
    d2 = r2.json()
    rows2 = d2.get('data',d2) if isinstance(d2,dict) else d2
    for row in (rows2 if isinstance(rows2,list) else []):
        if isinstance(row, dict):
            print(f"  {row}")
else:
    print(f"  Ошибка: {r2.text[:150]}")

# ── 3. Пробуем v1 расходные накладные ──
print("\n=== Расходные накладные v1 API (май 2026) ===")
endpoints = [
    f"/resto/api/v2/documents/export/invoice?dateFrom=2026-05-01&dateTo=2026-05-31",
    f"/resto/api/v2/documents/export/inventoryDocument?dateFrom=2026-05-01&dateTo=2026-05-31",
    f"/resto/api/v2/documents/movements?dateFrom=2026-05-01&dateTo=2026-05-31",
    f"/resto/api/v2/documents/outcomingInvoice?dateFrom=2026-05-01&dateTo=2026-05-31",
    f"/resto/api/v2/olap/sales?from=2026-05-01&to=2026-05-31",
]
for ep in endpoints:
    try:
        rr = s.get(f"{URL}{ep}", headers={"Cookie": f"key={token}"}, verify=False, timeout=20)
        snippet = rr.text[:100].replace('\n',' ')
        print(f"  {ep.split('?')[0].split('/')[-1]}: HTTP {rr.status_code} | {snippet}")
    except Exception as e:
        print(f"  {ep}: ERR {e}")

# ── 4. Magnum по месяцам через SALES ──
print("\n=== Magnum Chef — сумма через SALES по месяцам ===")
for lbl, frm, to in months:
    rows, err = olap("SALES", ["DishName"], ["DishDiscountSumInt"], frm, to)
    if rows is None:
        print(f"  {lbl}: ОШИБКА")
        continue
    mag_rows = [r for r in rows if isinstance(r,dict) and 'MAGNUM' in str(r.get('DishName','')).upper()]
    mag_total = sum(abs(float(r.get('DishDiscountSumInt',0) or 0)) for r in mag_rows)
    print(f"  {lbl}: {len(mag_rows)} Magnum позиций, сумма={mag_total/1e6:.2f}М")

print("\nГотово. Скопируйте вывод и покажите мне.")
input("Enter...")
