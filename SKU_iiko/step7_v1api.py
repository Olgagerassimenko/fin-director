# -*- coding: utf-8 -*-
"""
Шаг 7: старый v1 API iiko + полный текст ошибки OLAP (список валидных типов).
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
H_xml  = {"Cookie": f"key={token}", "Content-Type": "application/xml; charset=utf-8"}
H      = {"Cookie": f"key={token}"}
print("Token OK\n")

# ── 1. ПОЛНЫЙ текст ошибки GOODS_MOTION — узнаём список валидных типов ────
print("=== 1. Полный список валидных reportType (из текста ошибки) ===\n")
body = {"reportType": "GOODS_MOTION", "buildSummary": "false",
        "groupByRowFields": ["DishName"], "groupByColFields": [],
        "aggregateFields": ["DishDiscountSumInt"], "filters": {}}
r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
            json=body, headers=H_json, verify=False, timeout=15)
print(r2.text)  # полный текст — там будет enum

# ── 2. Старый v1 OLAP эндпоинт ────────────────────────────────────────────
print("\n\n=== 2. Старый API /resto/api/reports/olap (v1) ===\n")
for rt in ["GOODS_MOTION", "SALES", "STORE_MOVEMENTS"]:
    body = {
        "reportType": rt,
        "buildSummary": "false",
        "groupByRowFields": ["DishName"],
        "groupByColFields": [],
        "aggregateFields": ["DishDiscountSumInt"],
        "filters": {
            "OpenDate.Typed": {
                "filterType": "DateRange", "periodType": "CUSTOM",
                "from": "2026-06-01", "to": "2026-06-30",
                "includeLow": "true", "includeHigh": "true"
            }
        }
    }
    r2 = s.post(f"{URL}/resto/api/reports/olap",
                json=body, headers=H_json, verify=False, timeout=30)
    snippet = r2.text[:150].replace('\n',' ')
    print(f"  {rt:<20} HTTP {r2.status_code} | {snippet}")

# ── 3. Старые v1 XML-эндпоинты ────────────────────────────────────────────
print("\n\n=== 3. Старые API эндпоинты (v1) ===\n")
old_endpoints = [
    "/resto/api/reports/store_movements",
    "/resto/api/reports/goods_motion",
    "/resto/api/reports/product_sales",
    "/resto/api/chain/stores",
    "/resto/api/chain/departments",
    "/resto/api/products",
    "/resto/api/v2/nomenclature",
    "/resto/api/v2/nomenclature?id=00000000-0000-0000-0000-000000000000",
]
for ep in old_endpoints:
    r2 = s.get(f"{URL}{ep}", headers=H, verify=False, timeout=10)
    snippet = r2.text[:80].replace('\n',' ')
    print(f"  {ep:<50} HTTP {r2.status_code}")

# ── 4. XML-запрос на v1 OLAP ──────────────────────────────────────────────
print("\n\n=== 4. XML-формат запроса для v1 OLAP ===\n")
xml_body = """<?xml version="1.0" encoding="UTF-8"?>
<olap_report>
  <reportType>GOODS_MOTION</reportType>
  <buildSummary>false</buildSummary>
  <groupByRowFields>
    <field>DishName</field>
  </groupByRowFields>
  <groupByColFields/>
  <aggregateFields>
    <field>DishDiscountSumInt</field>
  </aggregateFields>
  <filters>
    <OpenDate.Typed>
      <filterType>DateRange</filterType>
      <periodType>CUSTOM</periodType>
      <from>2026-06-01</from>
      <to>2026-06-30</to>
      <includeLow>true</includeLow>
      <includeHigh>true</includeHigh>
    </OpenDate.Typed>
  </filters>
</olap_report>"""
r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
            data=xml_body.encode('utf-8'), headers=H_xml, verify=False, timeout=15)
snippet = r2.text[:200].replace('\n',' ')
print(f"  XML POST v2: HTTP {r2.status_code} | {snippet}")

r2 = s.post(f"{URL}/resto/api/reports/olap",
            data=xml_body.encode('utf-8'), headers=H_xml, verify=False, timeout=15)
snippet = r2.text[:200].replace('\n',' ')
print(f"  XML POST v1: HTTP {r2.status_code} | {snippet}")

print("\nГотово.")
