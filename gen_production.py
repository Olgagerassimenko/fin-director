# -*- coding: utf-8 -*-
"""
ПРОИЗВОДСТВО из iiko -> production_data.js

Четыре отчёта, которых на Пульсе не было.

1. ВЫПУСК (проводки PRODUCTION)
   Проводка производства — двойная запись: сырьё списывается (Sum.Outgoing),
   продукция приходуется (Sum.Incoming) по себестоимости этого сырья. Поэтому
   «оборот производства» сам по себе ничего не значит, а полуфабрикат считается
   дважды — когда его сделали и когда пустили в дело.
   Товарный выпуск = выпуск позиции минус её же внутреннее потребление.
   Именно он сопоставим с выручкой и себестоимостью продаж.

2. РАЗДЕЛКА (DISASSEMBLE)
   Туша или отруб разбирается на части. В деньгах сходится всегда (iiko
   разносит себестоимость), поэтому смотрим килограммы: сколько ушло
   в разделку и сколько получено.

3. ПЕРЕРАБОТКА И ПЕРЕСОРТ (TRANSFORMATION)
   Одна позиция превращается в другую. Здесь же видна усушка: например,
   дорогая мука уходит одним весом, а приходит дешёвая — меньшим.

4. СПИСАНИЯ (WRITEOFF)
   Что и с какого склада списано, в деньгах.

Плюс себестоимость единицы товарного выпуска по месяцам: видно, дорожает ли
производство само по себе, отдельно от объёма.

Запрос по номенклатуре за весь год iiko не отдаёт (обрывается по таймауту),
поэтому выпуск тянем помесячно. Только чтение.
Пишет production_data.js и production_LOG.txt.
"""
import sys, os, re, json, hashlib, warnings, datetime, calendar
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL = re.search(r'URL\s*=\s*"([^"]+)"', src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS = re.search(r'PASS\s*=\s*"([^"]+)"', src).group(1)

YEAR = 2026
TOP = 40
UNIT_TOP = 12
OUT = os.path.join(HERE, "production_data.js")
RUM = {1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
       7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек"}

LOG = open(os.path.join(HERE, "production_LOG.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a)
    print(t); LOG.write(t + "\n"); LOG.flush()


s = requests.Session()
tok = s.get(f"{URL}/resto/api/auth",
            params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
            verify=False, timeout=60).text.strip().strip('"')
log("iiko auth ok", datetime.datetime.now().strftime("%H:%M:%S"))


def olap(types, groups, d1, d2, aggs):
    """Верхняя дата у iiko исключающая — d2 передаём следующим днём."""
    body = {
        "reportType": "TRANSACTIONS", "buildSummary": "true",
        "groupByRowFields": list(groups), "aggregateFields": list(aggs),
        "filters": {
            "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                   "from": d1.isoformat(), "to": d2.isoformat(),
                                   "includeLow": True, "includeHigh": True},
            "TransactionType": {"filterType": "IncludeValues", "values": list(types)},
        },
    }
    r = s.post(f"{URL}/resto/api/v2/reports/olap",
               headers={"Cookie": f"key={tok}", "Content-Type": "application/json"},
               data=json.dumps(body), verify=False, timeout=600)
    if r.status_code != 200:
        log("  OLAP ERR", r.status_code, r.text[:200]); return []
    return r.json().get("data", [])


today = datetime.date.today()
last_full = today - datetime.timedelta(days=1)
YSTART = datetime.date(YEAR, 1, 1)
YEND = last_full + datetime.timedelta(days=1)
months = [m for m in range(1, 13) if datetime.date(YEAR, m, 1) <= last_full]

MONEY = ["Sum.Incoming", "Sum.Outgoing"]
FULL = ["Sum.Incoming", "Sum.Outgoing", "Amount.In", "Amount.Out"]

# ═════════════════════ 1. ВЫПУСК ═════════════════════
mo_keys = []
mo_gross, mo_netto = {}, {}
out_tot, inp_tot, fin_tot = {}, {}, {}
fin_by_mo, inp_by_mo, fin_qty_mo = {}, {}, {}
units = {}

log("\n-- выпуск --")
for m in months:
    d1 = datetime.date(YEAR, m, 1)
    d2 = min(datetime.date(YEAR, m, calendar.monthrange(YEAR, m)[1]), last_full)
    if d2 < d1:
        continue
    key = f"{YEAR}-{m:02d}"
    rows = olap(["PRODUCTION"], ["Product.Name", "Product.MeasureUnit"],
                d1, d2 + datetime.timedelta(days=1), FULL)
    if not rows:
        log(f"  {RUM[m]}: пусто"); continue

    per = {}
    for x in rows:
        name = (x.get("Product.Name") or "").strip()
        if not name:
            continue
        units.setdefault(name, (x.get("Product.MeasureUnit") or "").strip())
        r = per.setdefault(name, {"i": 0.0, "o": 0.0, "ai": 0.0, "ao": 0.0})
        r["i"] += x.get("Sum.Incoming") or 0
        r["o"] += x.get("Sum.Outgoing") or 0
        r["ai"] += x.get("Amount.In") or 0
        r["ao"] += x.get("Amount.Out") or 0

    gross = netto = 0.0
    for name, r in per.items():
        if r["i"] > 0:
            out_tot[name] = out_tot.get(name, 0) + r["i"]
            gross += r["i"]
        if r["o"] > 0:
            inp_tot[name] = inp_tot.get(name, 0) + r["o"]
            inp_by_mo.setdefault(name, {})[key] = r["o"]
        nt = r["i"] - r["o"]
        if nt > 0:
            fin_tot[name] = fin_tot.get(name, 0) + nt
            fin_by_mo.setdefault(name, {})[key] = nt
            if r["i"] > 0 and r["ai"] > 0:
                fin_qty_mo.setdefault(name, {})[key] = r["ai"] * nt / r["i"]
            netto += nt

    mo_keys.append(key)
    mo_gross[key] = gross
    mo_netto[key] = netto
    log(f"  {RUM[m]}: оборот {gross/1e6:7.1f} млн · товарный выпуск {netto/1e6:7.1f} млн · позиций {len(per)}")

if not mo_keys:
    log("ОСТАНОВЛЕНО: iiko не отдал ни одного месяца — файл не трогаю.")
    sys.exit(1)

own = {n for n in inp_tot if n in out_tot}

stores = {}
for x in olap(["PRODUCTION"], ["Store"], YSTART, YEND, MONEY):
    nm = (x.get("Store") or "—").strip() or "—"
    v = x.get("Sum.Incoming") or 0
    if v > 0:
        stores[nm] = stores.get(nm, 0) + v
log(f"  складов выпуска: {len(stores)}")


def top(d_tot, d_mo, mark_own=False):
    res = []
    for name, total in sorted(d_tot.items(), key=lambda kv: -kv[1])[:TOP]:
        row = {"n": name, "s": round(total),
               "m": [round(d_mo.get(name, {}).get(k, 0)) for k in mo_keys]}
        if mark_own and name in own:
            row["own"] = 1
        res.append(row)
    return res


unitcost = []
for name, total in sorted(fin_tot.items(), key=lambda kv: -kv[1])[:UNIT_TOP]:
    qty = fin_qty_mo.get(name, {})
    sums = fin_by_mo.get(name, {})
    series = []
    for k in mo_keys:
        q = qty.get(k, 0)
        series.append(round(sums.get(k, 0) / q, 1) if q > 0.001 else None)
    have = [v for v in series if v]
    if len(have) >= 3:
        unitcost.append({"n": name, "u": units.get(name, ""), "c": series,
                         "q": [round(qty.get(k, 0), 1) for k in mo_keys],
                         "d": round((have[-1] / have[0] - 1) * 100, 1) if have[0] else 0})
log(f"  позиций с себестоимостью единицы: {len(unitcost)}")


# ═════════════ 2 и 3. РАЗДЕЛКА и ПЕРЕРАБОТКА ═════════════
def split_report(types, title):
    rows = olap(types, ["Product.Name", "Product.MeasureUnit"], YSTART, YEND, FULL)
    per = {}
    for x in rows:
        name = (x.get("Product.Name") or "").strip()
        if not name:
            continue
        r = per.setdefault(name, {"u": (x.get("Product.MeasureUnit") or "").strip(),
                                  "si": 0.0, "so": 0.0, "ai": 0.0, "ao": 0.0})
        r["si"] += x.get("Sum.Incoming") or 0
        r["so"] += x.get("Sum.Outgoing") or 0
        r["ai"] += x.get("Amount.In") or 0
        r["ao"] += x.get("Amount.Out") or 0
    ins = [{"n": n, "u": r["u"], "kg": round(r["ao"], 1), "s": round(r["so"])}
           for n, r in per.items() if r["so"] > 0]
    outs = [{"n": n, "u": r["u"], "kg": round(r["ai"], 1), "s": round(r["si"])}
            for n, r in per.items() if r["si"] > 0]
    ins.sort(key=lambda x: -x["s"]); outs.sort(key=lambda x: -x["s"])
    res = {"in": ins[:TOP], "out": outs[:TOP],
           "sum": round(sum(x["s"] for x in ins)),
           "kg_in": round(sum(x["kg"] for x in ins), 1),
           "kg_out": round(sum(x["kg"] for x in outs), 1),
           "n_in": len(ins), "n_out": len(outs)}
    log(f"  {title}: {res['sum']/1e6:.1f} млн, вход {res['kg_in']:.0f}, выход {res['kg_out']:.0f}")
    return res


log("\n-- разделка и переработка --")
disasm = split_report(["DISASSEMBLE"], "разделка")
transf = split_report(["TRANSFORMATION"], "переработка")


# ═════════════════════ 4. СПИСАНИЯ ═════════════════════
log("\n-- списания --")
wo_prod, wo_store, wo_mo = {}, {}, {}
for x in olap(["WRITEOFF"], ["Product.Name", "Store", "DateTime.DateTyped"],
              YSTART, YEND, ["Sum.Outgoing"]):
    v = x.get("Sum.Outgoing") or 0
    if v <= 0:
        continue
    n = (x.get("Product.Name") or "—").strip() or "—"
    st = (x.get("Store") or "—").strip() or "—"
    k = str(x.get("DateTime.DateTyped") or "")[:7].replace(".", "-")
    wo_prod[n] = wo_prod.get(n, 0) + v
    wo_store[st] = wo_store.get(st, 0) + v
    if k:
        wo_mo[k] = wo_mo.get(k, 0) + v
writeoff = {
    "sum": round(sum(wo_prod.values())),
    "n": len(wo_prod),
    "by_product": sorted([{"n": k, "s": round(v)} for k, v in wo_prod.items()],
                         key=lambda x: -x["s"])[:TOP],
    "by_store": sorted([{"n": k, "s": round(v)} for k, v in wo_store.items()],
                       key=lambda x: -x["s"])[:20],
    "mo": [round(wo_mo.get(k, 0)) for k in mo_keys],
}
log(f"  списано: {writeoff['sum']/1e6:.1f} млн, позиций {writeoff['n']}")


data = {
    "updated": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
    "through": last_full.strftime("%d.%m.%Y"),
    "mo_keys": mo_keys,
    "mo_labels": [RUM[int(k[5:7])] for k in mo_keys],
    "mo_gross": [round(mo_gross[k]) for k in mo_keys],
    "mo_netto": [round(mo_netto[k]) for k in mo_keys],
    "out_count": len(out_tot), "inp_count": len(inp_tot),
    "fin_count": len(fin_tot), "own_count": len(own),
    "finished": top(fin_tot, fin_by_mo),
    "inputs": top(inp_tot, inp_by_mo, mark_own=True),
    "stores": sorted([{"n": k, "s": round(v)} for k, v in stores.items()],
                     key=lambda x: -x["s"]),
    "unitcost": unitcost,
    "disasm": disasm,
    "transf": transf,
    "writeoff": writeoff,
}


def prev():
    if not os.path.exists(OUT):
        return None
    try:
        t = open(OUT, encoding="utf-8").read()
        return json.loads(t[t.find("{"):t.rfind("}") + 1])
    except Exception as e:
        log(f"  прежний файл не прочитался ({e}) — проверку пропускаю"); return None


p = prev()
if p and p.get("mo_keys"):
    if len(mo_keys) < len(p["mo_keys"]) or len(fin_tot) < p.get("fin_count", 0) * 0.7:
        log("")
        log("  " + "=" * 52)
        log("  ОСТАНОВЛЕНО: новая сборка беднее прежней.")
        log(f"    было:  {len(p['mo_keys'])} мес., {p.get('fin_count', 0)} товарных позиций")
        log(f"    стало: {len(mo_keys)} мес., {len(fin_tot)} товарных позиций")
        log("  production_data.js не тронут.")
        log("  " + "=" * 52)
        sys.exit(1)

open(OUT, "w", encoding="utf-8").write(
    "window.PROD_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")

log("")
log(f"  месяцев:         {len(mo_keys)}  ({data['mo_labels'][0]} - {data['mo_labels'][-1]})")
log(f"  оборот за год:   {sum(mo_gross.values())/1e6:.0f} млн")
log(f"  товарный выпуск: {sum(mo_netto.values())/1e6:.0f} млн")
log(f"  позиций: выпуск {len(out_tot)}, товарных {len(fin_tot)}, "
    f"сырья {len(inp_tot)}, полуфабрикатов {len(own)}")
log(f"  -> production_data.js ({os.path.getsize(OUT)//1024} KB)")
