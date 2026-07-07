# -*- coding: utf-8 -*-
import requests, hashlib, warnings
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

STORE_GP_FZ   = "39846ac3-3697-417b-b33f-228123ab15a3"   # Склад ГП ФЗ
STORE_GP_25   = "e64f0a92-a07e-4207-866e-dac07950ae19"   # Склад ГП -25 С° ФЗ

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1},
          verify=False, timeout=30)
token = r.text.strip().strip('"')
headers = {"Cookie": f"key={token}", "Content-Type": "application/json"}
print(f"Token OK\n")

date_filter = {
    "OpenDate.Typed": {
        "filterType": "DateRange", "periodType": "CUSTOM",
        "from": "2026-06-01", "to": "2026-06-30",
        "includeLow": "true", "includeHigh": "true"
    }
}
store_filter = {
    "Store": {
        "filterType": "IncludeValues",
        "values": [STORE_GP_FZ, STORE_GP_25]
    }
}

print(f"{'Тип отчёта':<22} {'Склад?':<8} {'HTTP':<6} {'Строк':<8} {'SKU'}")
print("=" * 60)

best = None

for rt in ["GOODS_MOTION", "SALES", "WRITEOFF", "TRANSFER",
           "PRODUCTION", "PURCHASES", "DELIVERIES", "INVENTORY"]:
    for use_store, label in [(True, "да"), (False, "нет")]:
        filters = dict(date_filter)
        if use_store:
            filters.update(store_filter)

        body = {
            "reportType": rt,
            "buildSummary": "false",
            "groupByRowFields": ["DishCategory", "DishName"],
            "groupByColFields": [],
            "aggregateFields": ["DishDiscountSumInt", "DishAmountInt"],
            "filters": filters
        }
        try:
            r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                        json=body, headers=headers, verify=False, timeout=60)
            if r2.ok:
                data = r2.json()
                rows = data.get("data", []) if isinstance(data, dict) else (data or [])
                skus = {row.get("DishName","") for row in rows
                        if isinstance(row, dict) and row.get("DishName")}
                skus.discard("")
                marker = " <-- ЛУЧШИЙ" if len(skus) > 100 else ""
                print(f"{rt:<22} {label:<8} {r2.status_code:<6} {len(rows):<8} {len(skus)}{marker}")
                if len(skus) > (best[3] if best else 0):
                    best = (rt, use_store, len(rows), len(skus))
            else:
                err = r2.text[:50].replace('\n',' ')
                print(f"{rt:<22} {label:<8} {r2.status_code:<6} {err}")
        except Exception as e:
            print(f"{rt:<22} {label:<8} ERR  {str(e)[:50]}")

    print()  # пустая строка между типами

print("=" * 60)
if best:
    rt, use_store, rows, skus = best
    print(f"\nЛучший: {rt} (склад фильтр: {'да' if use_store else 'нет'})")
    print(f"  Строк: {rows}, SKU: {skus}")
