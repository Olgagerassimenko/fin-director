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

5. ИНВЕНТАРИЗАЦИИ (INVENTORY_CORRECTION)
   Недостачи и излишки по итогам пересчётов. Проводка двойная, направление
   определяется по количеству, а не по деньгам.

6. СТРУКТУРА ПО ГРУППАМ НОМЕНКЛАТУРЫ
   Из чего складывается себестоимость выпуска: мясо, молочка, овощи,
   упаковка. Отдельно — покупное сырьё и внутренний передел.

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
TOP = 40          # столько позиций отдаём с помесячной раскладкой
ALL_TOP = 3000    # столько строк отдаём всего — чтобы сортировать по всей базе
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

# Месяц считается закрытым, только если его последний день уже прошёл.
# Все сравнения на странице должны идти по закрытым месяцам: текущий
# неполный месяц занижает и выпуск, и себестоимость единицы.
closed_n = sum(1 for k in mo_keys
               if datetime.date(YEAR, int(k[5:7]),
                                calendar.monthrange(YEAR, int(k[5:7]))[1]) <= last_full)
log(f"  закрытых месяцев: {closed_n} из {len(mo_keys)}")

own = {n for n in inp_tot if n in out_tot}

stores = {}
for x in olap(["PRODUCTION"], ["Store"], YSTART, YEND, MONEY):
    nm = (x.get("Store") or "—").strip() or "—"
    v = x.get("Sum.Incoming") or 0
    if v > 0:
        stores[nm] = stores.get(nm, 0) + v
log(f"  складов выпуска: {len(stores)}")


def top(d_tot, d_mo, mark_own=False):
    """Отдаём всю базу, чтобы на странице можно было сортировать по любому
    столбцу, а не только по сорока крупнейшим. Помесячную раскладку держим
    только для первых TOP позиций — иначе файл раздувается в разы, а нужна
    она только там, где её реально смотрят."""
    res = []
    for i, (name, total) in enumerate(sorted(d_tot.items(), key=lambda kv: -kv[1])[:ALL_TOP]):
        row = {"n": name, "s": round(total)}
        if i < TOP:
            row["m"] = [round(d_mo.get(name, {}).get(k, 0)) for k in mo_keys]
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
    # Изменение считаем только по закрытым месяцам — в незакрытом выпуск
    # неполный, и себестоимость единицы по нему обманчива.
    have = [v for v in series[:closed_n] if v]
    if len(have) >= 3:
        unitcost.append({"n": name, "u": units.get(name, ""), "c": series,
                         "q": [round(qty.get(k, 0), 1) for k in mo_keys],
                         "d": round((have[-1] / have[0] - 1) * 100, 1) if have[0] else 0})
log(f"  позиций с себестоимостью единицы: {len(unitcost)}")


# ═════════════ 2 и 3. РАЗДЕЛКА и ПЕРЕРАБОТКА ═════════════
def split_report(types, title):
    """Килограммы, литры и штуки в одну сумму складывать нельзя, поэтому
    вход и выход считаем ОТДЕЛЬНО ПО КАЖДОЙ ЕДИНИЦЕ ИЗМЕРЕНИЯ. Иначе
    «потеря веса» получается бессмысленной: 678 тысяч чего именно."""
    rows = olap(types, ["Product.Name", "Product.MeasureUnit"], YSTART, YEND, FULL)
    per = {}
    for x in rows:
        name = (x.get("Product.Name") or "").strip()
        if not name:
            continue
        r = per.setdefault(name, {"u": (x.get("Product.MeasureUnit") or "").strip() or "—",
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

    by_unit = {}
    for r in ins:
        b = by_unit.setdefault(r["u"], {"in": 0.0, "out": 0.0, "n_in": 0, "n_out": 0})
        b["in"] += r["kg"]; b["n_in"] += 1
    for r in outs:
        b = by_unit.setdefault(r["u"], {"in": 0.0, "out": 0.0, "n_in": 0, "n_out": 0})
        b["out"] += r["kg"]; b["n_out"] += 1
    units = sorted(({"u": u, "in": round(v["in"], 1), "out": round(v["out"], 1),
                     "n_in": v["n_in"], "n_out": v["n_out"]} for u, v in by_unit.items()),
                   key=lambda x: -(x["in"] + x["out"]))

    res = {"in": ins[:ALL_TOP], "out": outs[:ALL_TOP],
           "sum": round(sum(x["s"] for x in ins)),
           "units": units, "n_in": len(ins), "n_out": len(outs)}
    log(f"  {title}: {res['sum']/1e6:.1f} млн, позиций {len(ins)}/{len(outs)}")
    for u in units:
        d = u["in"] - u["out"]
        log(f"      {u['u']:5} вход {u['in']:12.1f}  выход {u['out']:12.1f}  разница {-d:+.1f}")
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
                         key=lambda x: -x["s"])[:ALL_TOP],
    "by_store": sorted([{"n": k, "s": round(v)} for k, v in wo_store.items()],
                       key=lambda x: -x["s"]),
    "mo": [round(wo_mo.get(k, 0)) for k in mo_keys],
}
log(f"  списано: {writeoff['sum']/1e6:.1f} млн, позиций {writeoff['n']}")


# ═════════════════ 5. ИНВЕНТАРИЗАЦИИ ═════════════════
# Проводка инвентаризации в iiko двойная: Sum.Incoming == Sum.Outgoing на каждой
# строке, поэтому по деньгам направление не определить. Направление читается по
# количеству: Amount.In > 0 — излишек, Amount.Out > 0 — недостача. Строки, где
# количество нулевое (пересчёт без расхождения), в отчёт не идут.
log("\n-- инвентаризации --")
inv_store, inv_prod = {}, {}
inv_mo_in, inv_mo_out = {}, {}
inv_zero = 0
for x in olap(["INVENTORY_CORRECTION"],
              ["Product.Name", "Product.MeasureUnit", "Store", "DateTime.DateTyped"],
              YSTART, YEND, FULL):
    ai = x.get("Amount.In") or 0
    ao = x.get("Amount.Out") or 0
    v = x.get("Sum.Incoming") or 0
    if ai <= 0 and ao <= 0:
        inv_zero += 1
        continue
    n = (x.get("Product.Name") or "—").strip() or "—"
    st = (x.get("Store") or "—").strip() or "—"
    k = str(x.get("DateTime.DateTyped") or "")[:7].replace(".", "-")
    pr = inv_prod.setdefault(n, {"u": (x.get("Product.MeasureUnit") or "").strip(),
                                 "si": 0.0, "so": 0.0, "qi": 0.0, "qo": 0.0})
    b = inv_store.setdefault(st, {"i": 0.0, "o": 0.0})
    if ai > 0:
        pr["si"] += v; pr["qi"] += ai; b["i"] += v
        inv_mo_in[k] = inv_mo_in.get(k, 0) + v
    else:
        pr["so"] += v; pr["qo"] += ao; b["o"] += v
        inv_mo_out[k] = inv_mo_out.get(k, 0) + v


def _inv_rows(sign):
    """sign=-1 — чистые недостачи, sign=+1 — чистые излишки (по каждой позиции
    излишек и недостача сворачиваются: одна и та же позиция может и теряться,
    и находиться в разные месяцы)."""
    res = []
    for n, pr in inv_prod.items():
        net = (pr["si"] - pr["so"]) if sign > 0 else (pr["so"] - pr["si"])
        if net <= 0:
            continue
        q = (pr["qi"] - pr["qo"]) if sign > 0 else (pr["qo"] - pr["qi"])
        res.append({"n": n, "u": pr["u"], "s": round(net), "kg": round(q, 1)})
    res.sort(key=lambda r: -r["s"])
    return res[:ALL_TOP]


inv_in = sum(v["i"] for v in inv_store.values())
inv_out = sum(v["o"] for v in inv_store.values())
invent = {
    "sum_in": round(inv_in), "sum_out": round(inv_out), "net": round(inv_out - inv_in),
    "n": len(inv_prod), "zero": inv_zero,
    "mo_in": [round(inv_mo_in.get(k, 0)) for k in mo_keys],
    "mo_out": [round(inv_mo_out.get(k, 0)) for k in mo_keys],
    "by_store": sorted([{"n": k, "i": round(v["i"]), "o": round(v["o"]),
                         "s": round(v["o"] - v["i"])} for k, v in inv_store.items()
                        if v["i"] > 0 or v["o"] > 0],
                       key=lambda r: -r["s"]),
    "short": _inv_rows(-1),
    "over": _inv_rows(1),
}
log(f"  излишки {inv_in/1e6:.1f} млн · недостачи {inv_out/1e6:.1f} млн · "
    f"чистая недостача {(inv_out-inv_in)/1e6:.1f} млн · позиций {len(inv_prod)}")
for r in invent["by_store"][:6]:
    log(f"      {r['n'][:34]:36} сальдо {-r['s']/1e6:+8.2f} млн")



# ═════════ 6. СТРУКТУРА ВЫПУСКА И СЫРЬЯ ПО ГРУППАМ НОМЕНКЛАТУРЫ ═════════
# Позиций тысячи, и по списку из сорока строк не видно, из чего вообще
# складывается себестоимость. Группы номенклатуры (Product.SecondParent)
# дают ту же картину в двадцати строках: мясо, молочка, овощи, упаковка.
# Группу считаем «своей», если завод её не только тратит, но и сам выпускает
# хотя бы на пятую часть от того, что списывает, — это внутренний передел,
# и в покупное сырьё его включать нельзя, иначе затраты задвоятся.
log("\n-- структура по группам --")
g_out, g_inp = {}, {}
g_out_mo, g_inp_mo = {}, {}
for m in months:
    d1 = datetime.date(YEAR, m, 1)
    d2 = min(datetime.date(YEAR, m, calendar.monthrange(YEAR, m)[1]), last_full)
    if d2 < d1:
        continue
    key = f"{YEAR}-{m:02d}"
    for x in olap(["PRODUCTION"], ["Product.TopParent", "Product.SecondParent"],
                  d1, d2 + datetime.timedelta(days=1), MONEY):
        nm = ((x.get("Product.SecondParent") or "").strip()
              or (x.get("Product.TopParent") or "").strip() or "—")
        i = x.get("Sum.Incoming") or 0
        o = x.get("Sum.Outgoing") or 0
        if i > 0:
            g_out[nm] = g_out.get(nm, 0) + i
            d = g_out_mo.setdefault(nm, {}); d[key] = d.get(key, 0) + i
        if o > 0:
            g_inp[nm] = g_inp.get(nm, 0) + o
            d = g_inp_mo.setdefault(nm, {}); d[key] = d.get(key, 0) + o


def _own_group(nm, spent):
    return g_out.get(nm, 0) >= 0.2 * spent


def _grp(d_tot, d_mo, mark=False):
    res = []
    for nm, t in sorted(d_tot.items(), key=lambda kv: -kv[1])[:TOP]:
        row = {"n": nm, "s": round(t),
               "m": [round(d_mo.get(nm, {}).get(k, 0)) for k in mo_keys]}
        if mark and _own_group(nm, t):
            row["own"] = 1
        res.append(row)
    return res


buy_mo = {}
buy_tot = own_tot = 0.0
for nm, t in g_inp.items():
    if _own_group(nm, t):
        own_tot += t
    else:
        buy_tot += t
        for k, v in g_inp_mo.get(nm, {}).items():
            buy_mo[k] = buy_mo.get(k, 0) + v

groups = {
    "out": _grp(g_out, g_out_mo),
    "inp": _grp(g_inp, g_inp_mo, True),
    "buy": round(buy_tot), "own": round(own_tot),
    "mo_buy": [round(buy_mo.get(k, 0)) for k in mo_keys],
    "n_out": len(g_out), "n_inp": len(g_inp),
}
log(f"  групп: выпуск {len(g_out)}, списание {len(g_inp)}")
log(f"  покупное сырьё {buy_tot/1e6:.1f} млн · внутренний передел {own_tot/1e6:.1f} млн")
for r in groups["inp"][:8]:
    log(f"      {r['n'][:34]:36} {r['s']/1e6:8.1f} млн{'  (своё)' if r.get('own') else ''}")



data = {
    "updated": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
    "through": last_full.strftime("%d.%m.%Y"),
    "mo_keys": mo_keys,
    "closed": closed_n,
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
    "invent": invent,
    "groups": groups,
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
