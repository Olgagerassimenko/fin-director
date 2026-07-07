# -*- coding: utf-8 -*-
"""
Шаг 6: исследуем /resto/api/v2/reports/sales и другие эндпоинты.
"""
import requests, hashlib, warnings, json
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

STORE_GP_FZ = "39846ac3-3697-417b-b33f-228123ab15a3"
STORE_GP_25 = "e64f0a92-a07e-4207-866e-dac07950ae19"

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1},
          verify=False, timeout=30)
token = r.text.strip().strip('"')
H_json = {"Cookie": f"key={token}", "Content-Type": "application/json"}
H_xml  = {"Cookie": f"key={token}", "Content-Type": "application/xml"}
H      = {"Cookie": f"key={token}"}
print("Token OK\n")

# ── 1. Все варианты POST /resto/api/v2/reports/sales ──────────────────────
print("=== 1. POST /resto/api/v2/reports/sales ===\n")

payloads = [
    # JSON варианты
    (H_json, {"dateFrom": "2026-06-01", "dateTo": "2026-06-30"}),
    (H_json, {"from": "2026-06-01", "to": "2026-06-30", "storeIds": [STORE_GP_FZ, STORE_GP_25]}),
    (H_json, {"dateFrom": "2026-06-01T00:00:00", "dateTo": "2026-06-30T23:59:59"}),
    (H_json, {"period": {"dateFrom": "2026-06-01", "dateTo": "2026-06-30"}}),
]

for h, payload in payloads:
    r2 = s.post(f"{URL}/resto/api/v2/reports/sales",
                json=payload, headers=h, verify=False, timeout=30)
    snippet = r2.text[:120].replace('\n', ' ')
    print(f"  HTTP {r2.status_code} | {snippet}")

# ── 2. GET с параметрами ──────────────────────────────────────────────────
print("\n=== 2. GET /resto/api/v2/reports/sales с параметрами ===\n")
params_list = [
    {"dateFrom": "2026-06-01", "dateTo": "2026-06-30"},
    {"from": "2026-06-01", "to": "2026-06-30"},
    {"dateFrom": "2026-06-01", "dateTo": "2026-06-30", "storeId": STORE_GP_FZ},
]
for params in params_list:
    r2 = s.get(f"{URL}/resto/api/v2/reports/sales",
               params=params, headers=H, verify=False, timeout=30)
    snippet = r2.text[:100].replace('\n', ' ')
    print(f"  HTTP {r2.status_code} | {snippet}")

# ── 3. Складские движения через documents ─────────────────────────────────
print("\n=== 3. Документы движения товара ===\n")
doc_endpoints = [
    f"/resto/api/v2/documents/movements?dateFrom=2026-06-01&dateTo=2026-06-30",
    f"/resto/api/v2/documents/transfers?dateFrom=2026-06-01&dateTo=2026-06-30",
    f"/resto/api/v2/documents/writeoffs?dateFrom=2026-06-01&dateTo=2026-06-30",
    f"/resto/api/v2/documents/incomingInvoices?dateFrom=2026-06-01&dateTo=2026-06-30",
    f"/resto/api/v2/documents/purchaseInvoices?dateFrom=2026-06-01&dateTo=2026-06-30",
    f"/resto/api/v2/documents/returns?dateFrom=2026-06-01&dateTo=2026-06-30",
    f"/resto/api/v2/storageMethod",
    f"/resto/api/v2/reports",
    f"/resto/api/v2/store/balance",
]
for ep in doc_endpoints:
    r2 = s.get(f"{URL}{ep}", headers=H, verify=False, timeout=15)
    snippet = r2.text[:80].replace('\n',' ')
    print(f"  {ep.split('?')[0]:<48} HTTP {r2.status_code} | {snippet}")

# ── 4. Пробуем ещё OLAP типы (найти валидные) ────────────────────────────
print("\n=== 4. Поиск валидных reportType для OLAP ===\n")
candidates = [
    "SALES_BY_DAY", "SALES_BY_HOUR", "PRODUCT_SALES",
    "STORE_MOVEMENTS", "STORE_SALES", "PRODUCT_MOVEMENT",
    "REVENUE", "PRODUCT", "STORE", "ORDER",
    "COMBO_SALES", "ALCOHOL_SALES",
]
for rt in candidates:
    body = {
        "reportType": rt,
        "buildSummary": "false",
        "groupByRowFields": ["DishName"],
        "groupByColFields": [],
        "aggregateFields": ["DishDiscountSumInt"],
        "filters": {}
    }
    r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                json=body, headers=H_json, verify=False, timeout=15)
    if "value not one" in r2.text:
        status = "не поддерживается"
    elif r2.ok:
        data = r2.json()
        rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
        status = f"OK! строк={len(rows)}"
    else:
        status = r2.text[:60].replace('\n',' ')
    print(f"  {rt:<22} HTTP {r2.status_code} | {status}")

print("\nГотово.")
