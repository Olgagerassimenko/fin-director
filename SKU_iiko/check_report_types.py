# -*- coding: utf-8 -*-
"""
Ищем правильный тип OLAP-отчёта, соответствующий
"Отчёт о продажах за период" в iiko.
"""
import requests, hashlib, warnings
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1},
          verify=False, timeout=30)
token = r.text.strip().strip('"')
print(f"Авторизация OK\n")
headers = {"Cookie": f"key={token}", "Content-Type": "application/json"}

date_filter = {
    "OpenDate.Typed": {
        "filterType": "DateRange", "periodType": "CUSTOM",
        "from": "2026-01-01", "to": "2026-05-31",
        "includeLow": "true", "includeHigh": "true"
    }
}

# Все известные типы отчётов iiko
report_types = [
    "SALES",
    "GOODS_MOTION",
    "DELIVERIES",
    "PRODUCTION",
    "PURCHASES",
    "INVENTORY",
    "WRITEOFF",
    "TRANSFER",
    "SALES_BY_HOUR",
]

print("=" * 60)
print("  Тип отчёта            Строк    Уникальных SKU")
print("=" * 60)

best = None
for rt in report_types:
    try:
        body = {
            "reportType": rt,
            "buildSummary": "false",
            "groupByRowFields": ["DishName"],
            "groupByColFields": [],
            "aggregateFields": ["DishDiscountSumInt", "DishAmountInt"],
            "filters": date_filter
        }
        r = s.post(f"{URL}/resto/api/v2/reports/olap",
                   json=body, headers=headers, verify=False, timeout=60)
        if r.ok:
            data = r.json()
            rows = data.get('data', []) if isinstance(data, dict) else (data or [])
            skus = set(row.get('DishName','') for row in rows if isinstance(row, dict) and row.get('DishName'))
            n = len(rows)
            s_count = len(skus)
            marker = " <<<" if s_count > 100 else ""
            print(f"  {rt:<22} {n:<8} {s_count}{marker}")
            if s_count > (best[2] if best else 0):
                best = (rt, rows, s_count)
        else:
            err = r.text[:60].replace('\n',' ')
            print(f"  {rt:<22} ОШИБКА: {err}")
    except Exception as e:
        print(f"  {rt:<22} Исключение: {str(e)[:50]}")

print("=" * 60)
if best:
    print(f"\n  Лучший вариант: {best[0]} ({best[2]} SKU)")
    print(f"\n  Первые 10 SKU из {best[0]}:")
    seen = set()
    for row in best[1]:
        name = row.get('DishName','')
        if name and name not in seen:
            seen.add(name)
            rev = row.get('DishDiscountSumInt', 0)
            print(f"    {name}  —  {rev:,.0f}")
            if len(seen) >= 10:
                break
