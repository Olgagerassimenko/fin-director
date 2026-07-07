# -*- coding: utf-8 -*-
"""
Подбираем правильные имена полей для GOODS_MOTION.
"""
import requests, hashlib, warnings
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

date_f = {
    "OpenDate.Typed": {
        "filterType": "DateRange", "periodType": "CUSTOM",
        "from": "2026-06-01", "to": "2026-06-30",
        "includeLow": "true", "includeHigh": "true"
    }
}

def try_query(rt, group_fields, agg_fields, extra_filters=None):
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
        rows = data.get("data", []) if isinstance(data, dict) else (data or [])
        skus = {row.get(group_fields[0],"") for row in rows if isinstance(row, dict)}
        skus.discard("")
        return r2.status_code, len(rows), len(skus), None
    else:
        return r2.status_code, 0, 0, r2.text[:80].replace('\n',' ')

print("=== GOODS_MOTION — пробуем разные имена полей ===\n")
print(f"{'Поля группировки':<38} {'HTTP':<6} {'Строк':<8} {'Уник.'}")
print("-" * 65)

field_combos = [
    # Пары: [группировка], [агрегаты]
    (["DishName"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["MenuItem"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["MenuItem.Name"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["Product"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["ProductName"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["DishName"], ["Sum", "Amount"]),
    (["MenuItem"], ["Sum", "Amount"]),
    (["MenuItem"], ["SumOut", "AmountOut"]),
    (["MenuItem"], ["PriceOut", "AmountOut"]),
    (["DishName"], ["ContainerAmountOut", "ContainerSumOut"]),
    (["DishName", "DishCategory"], ["DishDiscountSumInt", "DishAmountInt"]),
    (["MenuItem", "MenuItemCategory"], ["Sum", "Amount"]),
]

for gf, af in field_combos:
    code, rows, uniq, err = try_query("GOODS_MOTION", gf, af)
    label = f"{gf[0]}" + (f"+{gf[1]}" if len(gf)>1 else "")
    agg_label = af[0]
    col = f"{label} / {agg_label}"
    if err:
        short_err = err[:35]
        print(f"  {col:<38} {code:<6} {short_err}")
    else:
        marker = " <--" if uniq > 50 else ""
        print(f"  {col:<38} {code:<6} {rows:<8} {uniq}{marker}")

print("\n=== Также пробуем SALES с правильной датой ===\n")
# SALES мог вернуть 0 из-за неверного фильтра дат — попробуем без OpenDate.Typed
for df_key in ["OpenDate.Typed", "OpenDate"]:
    body = {
        "reportType": "SALES",
        "buildSummary": "false",
        "groupByRowFields": ["DishName"],
        "groupByColFields": [],
        "aggregateFields": ["DishDiscountSumInt", "DishAmountInt"],
        "filters": {
            df_key: {
                "filterType": "DateRange", "periodType": "CUSTOM",
                "from": "2026-06-01", "to": "2026-06-30",
                "includeLow": "true", "includeHigh": "true"
            }
        }
    }
    r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                json=body, headers=H, verify=False, timeout=60)
    if r2.ok:
        data = r2.json()
        rows = data.get("data",[]) if isinstance(data,dict) else (data or [])
        skus = {row.get("DishName","") for row in rows if isinstance(row,dict)}
        skus.discard("")
        print(f"  SALES / filter={df_key}: HTTP {r2.status_code} | строк={len(rows)} | SKU={len(skus)}")
    else:
        print(f"  SALES / filter={df_key}: HTTP {r2.status_code} | {r2.text[:60]}")

print("\nГотово.")
