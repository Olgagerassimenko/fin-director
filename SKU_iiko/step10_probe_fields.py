# -*- coding: utf-8 -*-
"""
Шаг 10: угадываем поля TRANSACTIONS и STOCK через сообщения об ошибках.
Также пробуем пустые массивы — вдруг вернёт дефолтные данные.
"""
import requests, hashlib, warnings, json, os
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1},
          verify=False, timeout=30)
token = r.text.strip().strip('"')
H = {"Cookie": f"key={token}", "Content-Type": "application/json"}
print("Token OK\n")

date_f = {"OpenDate.Typed": {
    "filterType": "DateRange", "periodType": "CUSTOM",
    "from": "2026-06-01", "to": "2026-06-30",
    "includeLow": "true", "includeHigh": "true"
}}

def probe(rt, group_field, agg_field="UnknownAgg"):
    body = {
        "reportType": rt,
        "buildSummary": "false",
        "groupByRowFields": [group_field] if group_field else [],
        "groupByColFields": [],
        "aggregateFields": [agg_field] if agg_field else [],
        "filters": date_f
    }
    r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                json=body, headers=H, verify=False, timeout=30)
    if r2.ok:
        data = r2.json()
        rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
        skus = {str(row.get(group_field,"")) for row in rows if isinstance(row,dict)}
        skus.discard("")
        return "OK", len(rows), len(skus)
    else:
        # Вытащить имя поля из ошибки
        txt = r2.text
        if "Unknown OLAP field" in txt:
            # "Unknown OLAP field 'XYZ'" — узнаём что именно неизвестно
            import re
            m = re.search(r"Unknown OLAP field '([^']+)'", txt)
            bad = m.group(1) if m else "?"
            # Если bad == agg_field, то group_field ВАЛИДЕН!
            if bad == agg_field:
                return "GROUP_OK!", 0, 0
            elif bad == group_field:
                return "group_bad", 0, 0
            else:
                return f"unknown:{bad}", 0, 0
        elif "value not one" in txt:
            return "wrong_type", 0, 0
        else:
            return f"err:{r2.status_code}", 0, 0

# Зондируем с заведомо неверным агрегатом — если group_field верный, ошибка будет на агрегате
print("=== TRANSACTIONS: зондируем groupByRowFields ===")
print("(если статус GROUP_OK! — поле группировки верное)\n")

candidates_group = [
    # Номенклатура/продукты
    "Product", "ProductName", "Nomenclature", "NomenclatureName",
    "Ingredient", "IngredientName", "GoodName", "Good",
    "ItemName", "Item", "Name",
    # Склад
    "Store", "StoreName", "StoreFrom", "StoreTo",
    "Warehouse", "WarehouseName",
    # Документы
    "DocumentType", "TransactionType", "Reason", "ReasonName",
    "Account", "AccountName",
    # Партнёры
    "Contragent", "ContragentName", "Supplier", "SupplierName",
    # Прочее
    "Category", "Group", "Department", "DepartmentName",
    "CostCenter", "OrderType", "PaymentType",
]

valid_group = []
for f in candidates_group:
    status, rows, skus = probe("TRANSACTIONS", f, "DEFINITELY_WRONG_AGG_XYZ123")
    if "GROUP_OK" in status or status == "OK":
        print(f"  ✓ {f:<30} {status} rows={rows}")
        valid_group.append(f)
    # else: молчим, не загромождаем вывод

if not valid_group:
    print("  Ни одно поле группировки не подошло для TRANSACTIONS\n")
    # Пробуем STOCK
    print("\n=== STOCK: зондируем groupByRowFields ===\n")
    for f in candidates_group:
        status, rows, skus = probe("STOCK", f, "DEFINITELY_WRONG_AGG_XYZ123")
        if "GROUP_OK" in status or status == "OK":
            print(f"  ✓ {f:<30} {status} rows={rows}")
            valid_group.append(f)

# Если нашли валидные поля группировки — ищем агрегаты
if valid_group:
    print(f"\n=== Найдены groupBy поля: {valid_group} ===")
    print("Зондируем aggregateFields...\n")
    agg_candidates = [
        "Sum", "Amount", "Quantity", "Count",
        "PriceIn", "PriceOut", "SumIn", "SumOut",
        "AmountIn", "AmountOut", "Balance",
        "Cost", "CostSum", "ProductSum",
        "InvoiceSum", "ContainerSum",
        "TotalSum", "NetSum", "GrossSum",
    ]
    for gf in valid_group[:2]:
        print(f"  groupBy={gf}:")
        for af in agg_candidates:
            body = {
                "reportType": "TRANSACTIONS",
                "buildSummary": "false",
                "groupByRowFields": [gf],
                "groupByColFields": [],
                "aggregateFields": [af],
                "filters": date_f
            }
            r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                        json=body, headers=H, verify=False, timeout=20)
            if r2.ok:
                data = r2.json()
                rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
                print(f"    ✓ agg={af:<20} OK! rows={len(rows)}")
            elif "Unknown OLAP field" in r2.text:
                import re
                m = re.search(r"Unknown OLAP field '([^']+)'", r2.text)
                bad = m.group(1) if m else "?"
                if bad == af:
                    pass  # агрегат неверный — молчим
                else:
                    print(f"    ? agg={af:<20} bad_field={bad}")

# Пробуем полностью пустые массивы
print("\n=== Пустые groupBy и agg (дефолтный результат?) ===\n")
for rt in ["TRANSACTIONS", "STOCK", "DELIVERIES"]:
    body = {
        "reportType": rt,
        "buildSummary": "false",
        "groupByRowFields": [],
        "groupByColFields": [],
        "aggregateFields": [],
        "filters": date_f
    }
    r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                json=body, headers=H, verify=False, timeout=30)
    snippet = r2.text[:150].replace('\n',' ')
    print(f"  {rt:<15} HTTP {r2.status_code} | {snippet}")

print("\nГотово.")
