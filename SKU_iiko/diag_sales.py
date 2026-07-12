# -*- coding: utf-8 -*-
"""Диагностика: ищем правильный endpoint для продаж за месяц."""
import requests, hashlib, warnings, json
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"
MONTH = "2026-06"   # тестируем июнь 2026

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1}, verify=False, timeout=30)
token = r.text.strip().strip('"')
H = {"Cookie": f"key={token}", "Content-Type": "application/json"}
print(f"Auth OK: {token[:16]}...\n")

from_dt = f"{MONTH}-01"
to_dt   = f"{MONTH}-30"

def olap(rt, groups, aggs, filters=None):
    body = {
        "reportType": rt,
        "buildSummary": "false",
        "groupByRowFields": groups,
        "groupByColFields": [],
        "aggregateFields": aggs,
        "filters": filters or {}
    }
    r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                json=body, headers=H, verify=False, timeout=60)
    if not r2.ok:
        return None, r2.text[:200]
    d = r2.json()
    rows = d.get('data', d) if isinstance(d, dict) else d
    return rows if isinstance(rows, list) else [], ""

date_filter = {
    "OpenDate.Typed": {
        "filterType":"DateRange","periodType":"CUSTOM",
        "from": from_dt,"to": to_dt,
        "includeLow":"true","includeHigh":"true"
    }
}

print(f"=== Тестируем {MONTH} ===\n")

# 1. SALES — стандарт
rows, err = olap("SALES", ["DishCategory","DishName"], ["DishDiscountSumInt","DishAmountInt"], date_filter)
if rows is None:
    print(f"SALES: ОШИБКА — {err}")
else:
    print(f"SALES: {len(rows)} строк")
    if rows: print(f"  Пример: {json.dumps(rows[0], ensure_ascii=False)[:120]}")

# 2. DELIVERIES с датой
for groups in [
    ["DishName"],
    ["ProductName"],
    ["Nomenclature"],
    ["GoodName"],
    ["Product"],
]:
    rows2, err2 = olap("DELIVERIES", groups, ["DishDiscountSumInt"], date_filter)
    if rows2 is None:
        print(f"DELIVERIES groupBy={groups}: {err2[:80]}")
    else:
        print(f"DELIVERIES groupBy={groups}: {len(rows2)} строк")
        if rows2: print(f"  Пример: {json.dumps(rows2[0], ensure_ascii=False)[:120]}")
    if rows2 and len(rows2) > 0: break

# 3. DELIVERIES без фильтра даты
rows3, err3 = olap("DELIVERIES", ["Store"], ["Amount"], {})
print(f"\nDELIVERIES (без даты, groupBy=Store): {len(rows3) if rows3 is not None else 'ОШИБКА — '+err3[:80]}")

# 4. TRANSACTIONS без даты — сколько данных?
rows4, err4 = olap("TRANSACTIONS", ["Store","TransactionType"], ["Amount"], {})
if rows4 is None:
    print(f"TRANSACTIONS (без даты): ОШИБКА — {err4[:80]}")
else:
    print(f"TRANSACTIONS (без даты): {len(rows4)} строк")
    if rows4:
        for row in rows4[:5]:
            print(f"  {json.dumps(row, ensure_ascii=False)[:120]}")

# 5. Пробуем v1 API продаж
for endpoint in [
    "/resto/api/v2/documents/deliveryOrders",
    "/resto/api/v2/documents/invoice",
    "/resto/api/invoiceIn",
    "/resto/api/invoiceOut",
    "/resto/api/v2/documents/writeOff",
    "/resto/api/v2/reports/sales",
    "/resto/api/v2/reports/writeoffs",
]:
    try:
        r5 = s.get(f"{URL}{endpoint}", headers={"Cookie": f"key={token}"},
                   params={"dateFrom": from_dt, "dateTo": to_dt},
                   verify=False, timeout=20)
        snippet = r5.text[:100].replace('\n',' ')
        print(f"GET {endpoint}: HTTP {r5.status_code} | {snippet}")
    except Exception as e:
        print(f"GET {endpoint}: ОШИБКА {e}")

print("\nГотово. Скопируйте вывод и покажите Шарлотте.")
input("Enter...")
