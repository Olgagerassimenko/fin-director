# -*- coding: utf-8 -*-
"""TRANSACTIONS с правильным фильтром DateTime.Typed — ищем продукты."""
import requests, hashlib, warnings, json, re
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1}, verify=False, timeout=30)
token = r.text.strip().strip('"')
H = {"Cookie": f"key={token}", "Content-Type": "application/json"}
print("Auth OK\n")

MONTH = "2026-05"
FROM  = f"{MONTH}-01"
TO    = f"{MONTH}-31"

def try_filter(filter_key, from_dt, to_dt):
    return {filter_key: {
        "filterType": "DateRange", "periodType": "CUSTOM",
        "from": from_dt, "to": to_dt,
        "includeLow": "true", "includeHigh": "true"
    }}

def olap(rt, groups, aggs, filters):
    body = {"reportType": rt, "buildSummary": "false",
            "groupByRowFields": groups, "groupByColFields": [],
            "aggregateFields": aggs, "filters": filters}
    r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
                json=body, headers=H, verify=False, timeout=60)
    if not r2.ok:
        err = r2.text[:200].replace('\n',' ')
        return None, err
    d = r2.json()
    rows = d.get('data', d) if isinstance(d,dict) else d
    return rows if isinstance(rows,list) else [], ""

# ── 1. TRANSACTIONS с DateTime.Typed ──
print("=== TRANSACTIONS + DateTime.Typed (май 2026) ===\n")
date_filters = ["DateTime.Typed", "AccountingPeriod.Typed", "DocumentDate.Typed",
                "ActualDate.Typed", "WriteoffDate.Typed"]

working_filter = None
for fk in date_filters:
    rows, err = olap("TRANSACTIONS", ["Store"], ["Amount"], try_filter(fk, FROM, TO))
    if rows is None:
        print(f"  {fk}: ОШИБКА — {err[:80]}")
    else:
        total = sum(abs(float(r.get('Amount',0) or 0)) for r in rows if isinstance(r,dict))
        print(f"  ✓ {fk}: {len(rows)} строк, сумма={total/1e6:.1f}М")
        if not working_filter and len(rows) > 0:
            working_filter = fk

# ── 2. Если нашли рабочий фильтр — ищем поля продуктов ──
if working_filter:
    print(f"\n=== Рабочий фильтр: {working_filter} — ищем продукты ===\n")
    product_fields = [
        "Product", "ProductName", "Nomenclature", "NomenclatureName",
        "Good", "GoodName", "Item", "ItemName", "Name",
        "Ingredient", "IngredientName", "CommodityName",
        "OutcomingProduct", "IncomingProduct",
        "ContragentName", "Reason", "ReasonName",
    ]
    valid = []
    filt = try_filter(working_filter, FROM, TO)
    for f in product_fields:
        rows2, err2 = olap("TRANSACTIONS", [f], ["WRONG_XYZ"], filt)
        if rows2 is None:
            txt = err2
            if "Unknown OLAP field 'WRONG_XYZ'" in txt:
                print(f"  ✓ {f} — поле верное!")
                valid.append(f)
            elif "Unknown OLAP field" in txt:
                pass  # поле неверное — молчим
            else:
                print(f"  ? {f}: {txt[:60]}")
        else:
            print(f"  ✓ {f} — OK, {len(rows2)} строк")
            valid.append(f)

    if valid:
        print(f"\n  Рабочие поля: {valid}")
        # Полный запрос
        rows3, err3 = olap("TRANSACTIONS", valid[:2], ["Amount"], filt)
        if rows3:
            total3 = sum(abs(float(r.get('Amount',0) or 0)) for r in rows3 if isinstance(r,dict))
            print(f"  Итого: {len(rows3)} строк, сумма={total3/1e6:.1f}М")
            print("\n  Первые 5 строк:")
            for row in rows3[:5]:
                print(f"    {json.dumps(row, ensure_ascii=False)[:120]}")
    else:
        print("  Поля продуктов не найдены для TRANSACTIONS\n")

# ── 3. DELIVERIES с DateTime.Typed ──
print("\n=== DELIVERIES + DateTime.Typed ===\n")
for fk in ["DateTime.Typed","AccountingPeriod.Typed"]:
    rows4, err4 = olap("DELIVERIES", ["Store"], ["Amount"], try_filter(fk, FROM, TO))
    if rows4 is None:
        print(f"  {fk}: ОШИБКА — {err4[:80]}")
    else:
        total4 = sum(abs(float(r.get('Amount',0) or 0)) for r in rows4 if isinstance(r,dict))
        print(f"  ✓ {fk}: {len(rows4)} строк, сумма={total4/1e6:.1f}М")

print("\nГотово.")
input("Enter...")
