# -*- coding: utf-8 -*-
"""Финальный поиск endpoint продаж по номенклатуре."""
import requests, hashlib, warnings, json, re, xml.etree.ElementTree as ET
warnings.filterwarnings("ignore")

URL="https://fudzavod.iiko.it"; LOGIN="GerassimenkoO"; PASS="1234"
s=requests.Session()
sha1=hashlib.sha1(PASS.encode()).hexdigest()
token=s.get(f"{URL}/resto/api/auth",params={"login":LOGIN,"pass":sha1},verify=False,timeout=30).text.strip().strip('"')
H_JSON={"Cookie":f"key={token}","Content-Type":"application/json"}
H_GET ={"Cookie":f"key={token}"}
print("Auth OK\n")

FROM="2026-05-01"; TO="2026-05-31"
DATE_F={"DateTime.Typed":{"filterType":"DateRange","periodType":"CUSTOM",
    "from":FROM,"to":TO,"includeLow":"true","includeHigh":"true"}}

# ── 1. DELIVERIES — пробуем блюда/продукты ──
print("=== DELIVERIES — ищем продуктовые поля ===")
dish_fields=["DishName","Dish","MenuItem","MenuItemName","ProductName","Product",
             "NomenclatureName","Nomenclature","GoodName","Good",
             "Ingredient","IngredientName","Element","ElementName",
             "InvoiceProduct","OutcomingProduct","RecipeElement"]
for f in dish_fields:
    body={"reportType":"DELIVERIES","buildSummary":"false",
          "groupByRowFields":[f],"groupByColFields":[],
          "aggregateFields":["WRONG_XYZ"],"filters":DATE_F}
    r2=s.post(f"{URL}/resto/api/v2/reports/olap",json=body,headers=H_JSON,verify=False,timeout=20)
    txt=r2.text
    if "WRONG_XYZ" in txt:
        print(f"  ✓ {f} — поле верное!")
    elif r2.ok:
        print(f"  ✓ {f} — OK, строк={len(r2.json().get('data',[]))}")

# ── 2. SALES по Department — все отделы ──
print("\n=== SALES — все департаменты (май 2026) ===")
body2={"reportType":"SALES","buildSummary":"false",
       "groupByRowFields":["Department","DishName"],"groupByColFields":[],
       "aggregateFields":["DishDiscountSumInt","DishAmountInt"],
       "filters":{"OpenDate.Typed":{"filterType":"DateRange","periodType":"CUSTOM",
           "from":FROM,"to":TO,"includeLow":"true","includeHigh":"true"}}}
r3=s.post(f"{URL}/resto/api/v2/reports/olap",json=body2,headers=H_JSON,verify=False,timeout=60)
if r3.ok:
    rows3=r3.json().get('data',[])
    total3=sum(abs(float(rr.get('DishDiscountSumInt',0) or 0)) for rr in rows3 if isinstance(rr,dict))
    print(f"  {len(rows3)} строк, сумма={total3/1e6:.1f}М")
    depts=set(rr.get('Department','') for rr in rows3 if isinstance(rr,dict))
    print(f"  Департаменты: {depts}")
else:
    print(f"  Ошибка: {r3.text[:150]}")

# ── 3. Веб-отчёты iiko (угадываем endpoint) ──
print("\n=== Веб-эндпоинты отчётов iiko ===")
web_endpoints=[
    f"/resto/api/v2/reports/GoodsSales?from={FROM}&to={TO}",
    f"/resto/api/v2/reports/salesbyproduct?from={FROM}&to={TO}",
    f"/resto/api/v2/reports/ProductMovement?from={FROM}&to={TO}",
    f"/resto/api/v2/reports/warehouseSales?dateFrom={FROM}&dateTo={TO}",
    f"/resto/api/v2/reports/invoice?dateFrom={FROM}&dateTo={TO}",
    f"/resto/api/v2/documents/outInvoice?dateFrom={FROM}&dateTo={TO}",
    f"/resto/api/v2/documents/export/outInvoice?dateFrom={FROM}&dateTo={TO}",
    f"/resto/api/v2/documents/movements?dateFrom={FROM}&dateTo={TO}",
    f"/resto/api/v2/accounting/invoice?from={FROM}&to={TO}",
    f"/resto/api/v2/reports/productSalesReportData?from={FROM}&to={TO}",
    f"/resto/api/v2/reports/olap?reportType=INVOICE_OUT",
]
for ep in web_endpoints:
    try:
        r4=s.get(f"{URL}{ep}",headers=H_GET,verify=False,timeout=15)
        snippet=r4.text[:80].replace('\n',' ')
        print(f"  {r4.status_code} | {ep.split('?')[0].split('/')[-1]}: {snippet}")
    except Exception as e:
        print(f"  ERR | {ep.split('?')[0].split('/')[-1]}: {e}")

# ── 4. Пробуем POST /resto/api/v2/reports/olap с INVOICE_OUT ──
print("\n=== Пробуем INVOICE_OUT, WRITEOFF_DOC как reportType ===")
for rt in ["INVOICE_OUT","WRITEOFF_DOC","WRITE_OFF","GOODS_RETURN","OUTGOING_INVOICE",
           "SALE","OUTCOME","STOCK_OUT","EXPENSE","OUTCOMING"]:
    body5={"reportType":rt,"buildSummary":"false",
           "groupByRowFields":["Store"],"groupByColFields":[],
           "aggregateFields":["Amount"],"filters":{}}
    r5=s.post(f"{URL}/resto/api/v2/reports/olap",json=body5,headers=H_JSON,verify=False,timeout=15)
    txt5=r5.text[:120].replace('\n',' ')
    print(f"  {rt}: HTTP {r5.status_code} | {txt5}")

print("\nГотово.")
input("Enter...")
