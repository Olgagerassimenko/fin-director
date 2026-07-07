# -*- coding: utf-8 -*-
"""
Шаг 5: пробуем другие ключи дат для GOODS_MOTION
и другие API-эндпоинты iiko.
"""
import requests, hashlib, warnings, json
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

DEPT  = "2aafb9a8-7c62-499f-80b7-c3935348b891"  # department из прошлых сессий

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1},
          verify=False, timeout=30)
token = r.text.strip().strip('"')
H_json = {"Cookie": f"key={token}", "Content-Type": "application/json"}
H      = {"Cookie": f"key={token}"}
print("Token OK\n")

# ── 1. GOODS_MOTION с разными ключами даты ────────────────────────────────
print("=== 1. GOODS_MOTION — разные ключи фильтра даты ===\n")

date_keys = [
    "OpenDate.Typed",
    "InventDate.Typed",
    "DocumentDate.Typed",
    "StorageDate.Typed",
    "Date.Typed",
    "CloseDate.Typed",
]

for dk in date_keys:
    body = {
        "reportType": "GOODS_MOTION",
        "buildSummary": "false",
        "groupByRowFields": ["DishName"],
        "groupByColFields": [],
        "aggregateFields": ["DishDiscountSumInt"],
        "filters": {
            dk: {
                "filterType": "DateRange", "periodType": "CUSTOM",
                "from": "2026-06-01", "to": "2026-06-30",
                "includeLow": "true", "includeHigh": "true"
            }
        }
    }
    r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                json=body, headers=H_json, verify=False, timeout=30)
    if r2.ok:
        data = r2.json()
        rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
        print(f"  {dk:<28} HTTP {r2.status_code} | строк={len(rows)}")
    else:
        err = r2.text[:70].replace('\n',' ')
        print(f"  {dk:<28} HTTP {r2.status_code} | {err}")

# ── 2. GOODS_MOTION совсем без фильтров ──────────────────────────────────
print("\n=== 2. GOODS_MOTION без фильтров (минимальный запрос) ===\n")
body = {
    "reportType": "GOODS_MOTION",
    "buildSummary": "false",
    "groupByRowFields": ["DishName"],
    "groupByColFields": [],
    "aggregateFields": ["DishDiscountSumInt"],
    "filters": {}
}
r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
            json=body, headers=H_json, verify=False, timeout=30)
print(f"  HTTP {r2.status_code} | {r2.text[:120].replace(chr(10),' ')}")

# ── 3. SALES за июнь 2026 с Department ────────────────────────────────────
print("\n=== 3. SALES июнь 2026 + Department фильтр ===\n")
body = {
    "reportType": "SALES",
    "buildSummary": "false",
    "groupByRowFields": ["DishName", "DishCategory"],
    "groupByColFields": [],
    "aggregateFields": ["DishDiscountSumInt", "DishAmountInt"],
    "filters": {
        "OpenDate.Typed": {
            "filterType": "DateRange", "periodType": "CUSTOM",
            "from": "2026-06-01", "to": "2026-06-30",
            "includeLow": "true", "includeHigh": "true"
        },
        "Department": {
            "filterType": "IncludeValues",
            "values": [DEPT]
        }
    }
}
r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
            json=body, headers=H_json, verify=False, timeout=60)
if r2.ok:
    data = r2.json()
    rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
    skus = {row.get("DishName","") for row in rows if isinstance(row,dict)}
    skus.discard("")
    print(f"  HTTP {r2.status_code} | строк={len(rows)} | SKU={len(skus)}")
else:
    print(f"  HTTP {r2.status_code} | {r2.text[:120].replace(chr(10),' ')}")

# ── 4. Другие REST-эндпоинты ──────────────────────────────────────────────
print("\n=== 4. Альтернативные эндпоинты ===\n")
alt_endpoints = [
    f"/resto/api/v2/reports/olap",                          # уже знаем
    f"/resto/api/reports/salereport.json",
    f"/resto/api/v2/documents/export/sales",
    f"/resto/api/export/products/sales",
    f"/resto/api/v2/reports/sales",
    f"/resto/api/v2/olap",
    f"/resto/api/v2/olap/report",
]
for ep in alt_endpoints:
    try:
        r2 = s.get(f"{URL}{ep}", headers=H, verify=False, timeout=10)
        print(f"  GET {ep:<45} HTTP {r2.status_code}")
    except Exception as e:
        print(f"  GET {ep:<45} ERR {str(e)[:40]}")

print("\nГотово.")
