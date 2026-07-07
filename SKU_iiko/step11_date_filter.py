# -*- coding: utf-8 -*-
"""
Шаг 11: ищем правильный ключ фильтра даты для TRANSACTIONS и STOCK.
Плюс ищем поля с названием номенклатуры.
"""
import requests, hashlib, warnings, json, re, os
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

def post_olap(rt, group_fields, agg_fields, filters):
    body = {
        "reportType": rt,
        "buildSummary": "false",
        "groupByRowFields": group_fields,
        "groupByColFields": [],
        "aggregateFields": agg_fields,
        "filters": filters
    }
    r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                json=body, headers=H, verify=False, timeout=60)
    return r2

def make_date_filter(key):
    return {key: {
        "filterType": "DateRange", "periodType": "CUSTOM",
        "from": "2026-06-01", "to": "2026-06-30",
        "includeLow": "true", "includeHigh": "true"
    }}

# ── 1. Ищем правильный ключ даты для TRANSACTIONS ─────────────────────────
print("=== 1. Ключи даты для TRANSACTIONS (groupBy=Store, agg=Amount) ===\n")

date_keys = [
    "OpenDate.Typed", "TransactionDate.Typed", "Date.Typed",
    "DocumentDate.Typed", "InventDate.Typed", "PeriodDate.Typed",
    "CreateDate.Typed", "EventDate.Typed", "CloseDate.Typed",
    "WriteoffDate.Typed", "InvoiceDate.Typed", "ActualDate.Typed",
]

valid_date_key = None
for dk in date_keys:
    r2 = post_olap("TRANSACTIONS", ["Store"], ["Amount"], make_date_filter(dk))
    if r2.ok:
        data = r2.json()
        rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
        print(f"  ✓ {dk:<30} HTTP 200 | строк={len(rows)}")
        if not valid_date_key:
            valid_date_key = dk
    else:
        txt = r2.text
        m = re.search(r"Unknown OLAP field '([^']+)'", txt)
        bad = m.group(1) if m else txt[:60].replace('\n',' ')
        if bad == dk:
            status = "дата-ключ неверный"
        elif bad == "Amount":
            status = f"ДА-КЛЮЧ ОК! Но agg='Amount' неверен"
            if not valid_date_key:
                valid_date_key = dk
        else:
            status = f"bad={bad}"
        print(f"  {dk:<30} {status}")

print()

# ── 2. Если нашли дату — ищем поля с продуктами ───────────────────────────
if valid_date_key:
    print(f"=== 2. Дата-ключ найден: {valid_date_key} ===")
    print("Ищем groupBy поля с названиями продуктов...\n")

    product_candidates = [
        "Product", "ProductName", "Nomenclature", "NomenclatureName",
        "Good", "GoodName", "Ingredient", "IngredientName",
        "Item", "ItemName", "CommodityName", "CommodityGroup",
        "ProductGroup", "CategoryName", "ProductCategory",
        "StoreName", "StoreFromName", "StoreToName",
        "Reason", "ReasonName", "OperationType",
        "ContragentName", "Employee", "EmployeeName",
    ]
    valid_prod_fields = []
    for f in product_candidates:
        r2 = post_olap("TRANSACTIONS", [f], ["WRONG_AGG_XYZ"], make_date_filter(valid_date_key))
        if r2.ok:
            data = r2.json()
            rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
            print(f"  ✓ {f:<25} OK! rows={len(rows)}")
            valid_prod_fields.append(f)
        else:
            txt = r2.text
            m = re.search(r"Unknown OLAP field '([^']+)'", txt)
            bad = m.group(1) if m else "?"
            if bad == "WRONG_AGG_XYZ":
                print(f"  ✓ {f:<25} GROUP_OK!")
                valid_prod_fields.append(f)
            # else: поле группировки неверное — молчим

    # ── 3. Ищем правильные агрегаты ─────────────────────────────────────
    if valid_prod_fields:
        best_gf = valid_prod_fields[0]
        print(f"\n=== 3. Агрегаты (groupBy={best_gf}) ===\n")
        agg_candidates = [
            "Amount", "Sum", "Quantity", "Count", "Balance",
            "SumIn", "SumOut", "AmountIn", "AmountOut",
            "PriceIn", "PriceOut", "Cost", "CostSum",
            "TotalSum", "NetSum", "GrossSum", "ProductSum",
            "ContainerAmount", "ContainerSum",
            "InvoiceSum", "ReceiptSum", "WriteoffSum",
        ]
        valid_aggs = []
        for af in agg_candidates:
            r2 = post_olap("TRANSACTIONS", [best_gf], [af], make_date_filter(valid_date_key))
            if r2.ok:
                data = r2.json()
                rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
                print(f"  ✓ {af:<20} OK! rows={len(rows)}")
                valid_aggs.append(af)
            else:
                txt = r2.text
                m = re.search(r"Unknown OLAP field '([^']+)'", txt)
                bad = m.group(1) if m else "?"
                if bad != af:
                    print(f"  ? {af:<20} bad={bad}")

        if valid_aggs:
            # Итоговый запрос!
            print(f"\n=== ИТОГО: полный запрос ===")
            print(f"  reportType=TRANSACTIONS")
            print(f"  groupBy={valid_prod_fields[:3]}")
            print(f"  agg={valid_aggs[:3]}")
            print(f"  dateKey={valid_date_key}")

else:
    print("Дата-ключ для TRANSACTIONS не найден.")
    print("\n=== Пробуем STOCK с теми же ключами ===\n")
    for dk in date_keys:
        r2 = post_olap("STOCK", ["Store"], ["Amount"], make_date_filter(dk))
        txt = r2.text
        m = re.search(r"Unknown OLAP field '([^']+)'", txt)
        bad = m.group(1) if m else txt[:50].replace('\n',' ')
        if r2.ok or bad == "Amount":
            print(f"  ✓ STOCK date={dk}")

print("\nГотово.")
