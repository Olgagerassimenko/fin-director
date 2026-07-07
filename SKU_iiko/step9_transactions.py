# -*- coding: utf-8 -*-
"""
Шаг 9: тестируем TRANSACTIONS и STOCK — правильные типы для склада.
"""
import requests, hashlib, warnings, json, os
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
H = {"Cookie": f"key={token}", "Content-Type": "application/json"}
print("Token OK\n")

HERE = os.path.dirname(os.path.abspath(__file__))

date_f = {
    "OpenDate.Typed": {
        "filterType": "DateRange", "periodType": "CUSTOM",
        "from": "2026-06-01", "to": "2026-06-30",
        "includeLow": "true", "includeHigh": "true"
    }
}

def test(rt, group_fields, agg_fields, extra_filters=None):
    filters = dict(date_f)
    if extra_filters:
        filters.update(extra_filters)
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
    if r2.ok:
        data = r2.json()
        rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
        skus = {str(row.get(group_fields[0],"")) for row in rows if isinstance(row,dict)}
        skus.discard("")
        return r2.status_code, len(rows), len(skus), rows[:2]
    else:
        return r2.status_code, 0, 0, r2.text[:100]

print("=" * 70)
print("TRANSACTIONS — перебор полей группировки и агрегатов")
print("=" * 70)

combos = [
    (["DishName"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["DishName"], ["DishAmountInt"]),
    (["DishName", "DishCategory"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["Product"], ["Sum", "Amount"]),
    (["ProductName"], ["Sum", "Amount"]),
    (["MenuItem"], ["Sum", "Amount"]),
    (["GoodName"], ["Sum", "Amount"]),
    (["Item"], ["Sum", "Amount"]),
    (["StoreName", "DishName"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["Store", "DishName"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["DishName"], ["DishSumInt", "DishAmountInt"]),
    (["DishName"], ["ContainerAmountOut", "ContainerSumOut"]),
    (["DishName"], ["GrossProfit", "DishDiscountSumInt"]),
]

best_rows = 0
best_combo = None
best_data = None

for gf, af in combos:
    code, rows, skus, extra = test("TRANSACTIONS", gf, af)
    label = f"{gf[0]}/{af[0]}"
    if code == 200:
        marker = " <-- ДАННЫЕ!" if skus > 50 else (" <- есть" if rows > 0 else "")
        print(f"  {label:<40} HTTP {code} | строк={rows} | SKU={skus}{marker}")
        if rows > best_rows:
            best_rows = rows
            best_combo = (gf, af)
            best_data = extra
    else:
        err = str(extra)[:60] if isinstance(extra, str) else ""
        print(f"  {label:<40} HTTP {code} | {err}")

print("\n" + "=" * 70)
print("STOCK")
print("=" * 70)

for gf, af in [
    (["DishName"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["DishName"], ["Balance"]),
    (["DishName"], ["Amount"]),
    (["Product"], ["Balance"]),
]:
    code, rows, skus, extra = test("STOCK", gf, af)
    label = f"{gf[0]}/{af[0]}"
    if code == 200:
        print(f"  {label:<40} HTTP {code} | строк={rows} | SKU={skus}")
    else:
        err = str(extra)[:60] if isinstance(extra, str) else ""
        print(f"  {label:<40} HTTP {code} | {err}")

if best_combo:
    print(f"\n[Лучший результат TRANSACTIONS: {best_rows} строк]")
    print(f"Поля: groupBy={best_combo[0]}, agg={best_combo[1]}")
    if isinstance(best_data, list) and best_data:
        print(f"Первая строка: {json.dumps(best_data[0], ensure_ascii=False)}")

    # Если нашли данные — сохраним полный результат
    if best_rows > 0:
        gf, af = best_combo
        store_filter = {
            "Store": {
                "filterType": "IncludeValues",
                "values": [STORE_GP_FZ, STORE_GP_25]
            }
        }
        code, rows, skus, extra = test("TRANSACTIONS", gf, af, store_filter)
        print(f"\nС фильтром складов ГП: HTTP {code} | строк={rows} | SKU={skus}")

        # Без фильтра склада — все данные
        filters = dict(date_f)
        body = {
            "reportType": "TRANSACTIONS",
            "buildSummary": "false",
            "groupByRowFields": gf,
            "groupByColFields": [],
            "aggregateFields": af,
            "filters": filters
        }
        r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                    json=body, headers=H, verify=False, timeout=120)
        if r2.ok:
            data = r2.json()
            all_rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
            out_file = os.path.join(HERE, "transactions_data.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(all_rows, f, ensure_ascii=False, indent=2)
            print(f"Полные данные ({len(all_rows)} строк) → transactions_data.json")

print("\nГотово.")
