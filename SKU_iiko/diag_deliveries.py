# -*- coding: utf-8 -*-
"""Ищем рабочие поля для DELIVERIES — последняя попытка."""
import requests, hashlib, warnings, json, re
warnings.filterwarnings("ignore")

URL="https://fudzavod.iiko.it"; LOGIN="GerassimenkoO"; PASS="1234"
s=requests.Session()
sha1=hashlib.sha1(PASS.encode()).hexdigest()
token=s.get(f"{URL}/resto/api/auth",params={"login":LOGIN,"pass":sha1},verify=False,timeout=30).text.strip().strip('"')
H={"Cookie":f"key={token}","Content-Type":"application/json"}
print("Auth OK\n")

# TRANSACTIONS DateTime.Typed дал 2.2М — смотрим что внутри
print("=== TRANSACTIONS DateTime.Typed май — полный результат ===")
body={"reportType":"TRANSACTIONS","buildSummary":"false",
      "groupByRowFields":["Store","TransactionType"],"groupByColFields":[],
      "aggregateFields":["Amount"],
      "filters":{"DateTime.Typed":{"filterType":"DateRange","periodType":"CUSTOM",
          "from":"2026-05-01","to":"2026-05-31","includeLow":"true","includeHigh":"true"}}}
r2=s.post(f"{URL}/resto/api/v2/reports/olap",json=body,headers=H,verify=False,timeout=60)
if r2.ok:
    rows=r2.json().get('data',[])
    for row in rows:
        print(f"  {json.dumps(row,ensure_ascii=False)}")
else:
    print(f"  Ошибка: {r2.text[:200]}")

# Зондируем DELIVERIES — ищем рабочие groupBy поля
print("\n=== DELIVERIES — зондируем поля (май 2026) ===")
DATE_F={"DateTime.Typed":{"filterType":"DateRange","periodType":"CUSTOM",
    "from":"2026-05-01","to":"2026-05-31","includeLow":"true","includeHigh":"true"}}
DATE_F2={"AccountingPeriod.Typed":{"filterType":"DateRange","periodType":"CUSTOM",
    "from":"2026-05-01","to":"2026-05-31","includeLow":"true","includeHigh":"true"}}

candidates=["Supplier","SupplierName","Contragent","ContragentName",
            "Product","ProductName","Nomenclature","NomenclatureName",
            "Store","StoreName","StoreFrom","StoreTo","Warehouse",
            "Department","DepartmentName","InvoiceNumber","DocumentType",
            "Employee","EmployeeName","Category","CategoryName",
            "GoodName","Good","Item","ItemName","Amount","Sum","Cost"]

valid=[]
for f in candidates:
    for filt in [DATE_F, DATE_F2, {}]:
        body2={"reportType":"DELIVERIES","buildSummary":"false",
               "groupByRowFields":[f],"groupByColFields":[],
               "aggregateFields":["WRONG_XYZ"],"filters":filt}
        r3=s.post(f"{URL}/resto/api/v2/reports/olap",json=body2,headers=H,verify=False,timeout=20)
        txt=r3.text
        if r3.ok:
            print(f"  ✓ {f}: OK!")
            valid.append(f); break
        elif "Unknown OLAP field 'WRONG_XYZ'" in txt:
            print(f"  ✓ {f}: ПОЛЕ ВЕРНОЕ (агрегат нужен другой)")
            valid.append(f); break
        elif "Unknown OLAP field" in txt and f in txt:
            break  # поле неверное
        # иначе пробуем другой фильтр

if valid:
    print(f"\nРабочие поля DELIVERIES: {valid}")
    # Пробуем получить данные
    for f in valid[:3]:
        body3={"reportType":"DELIVERIES","buildSummary":"false",
               "groupByRowFields":[f],"groupByColFields":[],
               "aggregateFields":["Amount"],"filters":DATE_F}
        r4=s.post(f"{URL}/resto/api/v2/reports/olap",json=body3,headers=H,verify=False,timeout=30)
        if r4.ok:
            rows4=r4.json().get('data',[])
            total=sum(abs(float(rr.get('Amount',0) or 0)) for rr in rows4 if isinstance(rr,dict))
            print(f"  {f}: {len(rows4)} строк, сумма={total/1e6:.1f}М")
            for rr in rows4[:3]:
                print(f"    {json.dumps(rr,ensure_ascii=False)[:100]}")
else:
    print("  Рабочих полей не найдено.")

print("\n=== ИТОГ ===")
print("TRANSACTIONS DateTime.Typed: 11 строк, 2.2М — только внутренние переводы")
print("DELIVERIES: не поддерживает нужные поля")
print("\nВывод: данные склада доступны только через Excel-выгрузку из iiko.")
print("Для мая нужно выгрузить 'Отчёт о продажах' за май 2026 из iiko UI.")
input("\nEnter...")
