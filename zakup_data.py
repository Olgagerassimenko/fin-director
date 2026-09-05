# -*- coding: utf-8 -*-
"""
ЗАКУП из iiko -> zakup.json
Вкладки дашборда «Закуп»:
  1) Приход и оплата товара по накладным (по поставщикам): неделя / месяц / год
     тип INVOICE = приход, INVOICE_PAYMENT(+AUTO) = оплата, значение Sum.Incoming
  2) Закупочные цены по позициям (тип INVOICE): цена = сумма/кол-во, отклонения
  3) Остатки по складам (balance/stores) + тренд по месяцам/неделям
  4) КЗ / план оплат: остаток долга из счёта «Задолженность перед поставщиками»,
     список поставщиков ограничен листом «КЗ» Google-файла ДЗ КЗ
Только чтение. Пишет zakup.json + zakup_LOG.txt.
"""
import sys, os, re, json, hashlib, warnings, datetime, csv, io
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import almaty  # время завода — Алматы (UTC+5), не UTC раннера

warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import requests
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL = re.search(r'URL\s*=\s*"([^"]+)"', src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS = re.search(r'PASS\s*=\s*"([^"]+)"', src).group(1)
FZ = "2aafb9a8-7c62-499f-80b7-c3935348b891"
DEP = "Фуд завод"
YEAR = 2026
T_PRIHOD = ["INVOICE"]
T_OPLATA = ["INVOICE_PAYMENT", "INVOICE_PAYMENT_AUTO"]
PAY_ACC = "Задолженность перед поставщиками"
SHEET_ID = "13iFd16Hah1Yi5y2QptmyUrw51rSFfAmtnzhf0U2g_wc"
KZ_GID = "2005257911"
RUM = {1:"январь",2:"февраль",3:"март",4:"апрель",5:"май",6:"июнь",7:"июль",8:"август",9:"сентябрь",10:"октябрь",11:"ноябрь",12:"декабрь"}

LOG = open(os.path.join(HERE, "zakup_LOG.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

s = requests.Session()
tok = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()}, verify=False, timeout=60).text.strip().strip('"')
log("iiko auth ok", almaty.now().strftime("%H:%M:%S"))

def olap(body):
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers={"Cookie": f"key={tok}", "Content-Type": "application/json"}, data=json.dumps(body), verify=False, timeout=300)
    if r.status_code != 200:
        log("  OLAP ERR", r.status_code, r.text[:150]); return []
    return r.json().get("data", [])

# время завода, а не раннера: иначе ночью дашборд считает вчерашним днём позавчера
today = almaty.today()
last_full = today - datetime.timedelta(days=1)
lastm = last_full.month

def d_iso(d): return d.isoformat()
def daterange_filter(d1, d2):
    return {"filterType": "DateRange", "periodType": "CUSTOM", "from": d_iso(d1), "to": d_iso(d2), "includeLow": True, "includeHigh": False}

# ---------- периоды ----------
def bom(mi): return datetime.date(YEAR, mi, 1)
def eom(mi): return datetime.date(YEAR, mi + 1, 1) if mi < 12 else datetime.date(YEAR + 1, 1, 1)
months = [(f"{YEAR}-{mi:02d}", bom(mi), min(eom(mi), last_full + datetime.timedelta(days=1))) for mi in range(1, lastm + 1)]

def week_start(d): return d - datetime.timedelta(days=d.weekday())
cur_ws = week_start(last_full)
weeks = []
for k in range(12, -1, -1):  # последние 13 недель, включая текущую
    ws = cur_ws - datetime.timedelta(weeks=k)
    we = min(ws + datetime.timedelta(days=7), last_full + datetime.timedelta(days=1))
    if we <= ws: continue
    key = ws.strftime("%Y-%W")
    label = f"{ws.strftime('%d.%m')}–{(ws + datetime.timedelta(days=6)).strftime('%d.%m')}"
    weeks.append((key, label, ws, we))
year_from = datetime.date(YEAR, 1, 1)
year_to = last_full + datetime.timedelta(days=1)

# ---------- 1. Приход/оплата по поставщикам ----------
def prihod_oplata(d1, d2):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": ["Counteragent.Name", "TransactionType"],
            "aggregateFields": ["Sum.Incoming"],
            "filters": {"DateTime.DateTyped": daterange_filter(d1, d2),
                        "Department": {"filterType": "IncludeValues", "values": [DEP]},
                        "TransactionType": {"filterType": "IncludeValues", "values": T_PRIHOD + T_OPLATA}}}
    sup = {}
    for x in olap(body):
        ca = (x.get("Counteragent.Name") or "—").strip()
        tt = str(x.get("TransactionType")); v = x.get("Sum.Incoming") or 0
        e = sup.setdefault(ca, {"prihod": 0, "oplata": 0})
        if tt in T_PRIHOD: e["prihod"] += v
        elif tt in T_OPLATA: e["oplata"] += v
    out = [{"name": k, "prihod": round(v["prihod"]), "oplata": round(v["oplata"]), "itogo": round(v["prihod"] + v["oplata"])}
           for k, v in sup.items() if abs(v["prihod"]) > 0.5 or abs(v["oplata"]) > 0.5]
    out.sort(key=lambda x: -x["itogo"])
    return out

def pack_po(periods):
    res = {}
    for key, *rest in periods:
        d1, d2 = rest[-2], rest[-1]
        rows = prihod_oplata(d1, d2)
        res[key] = {"suppliers": rows,
                    "prihod": sum(r["prihod"] for r in rows),
                    "oplata": sum(r["oplata"] for r in rows),
                    "n": len(rows)}
        if len(rest) == 3:
            res[key]["label"] = rest[0]
    return res

log("1) приход/оплата: месяцы...")
po_months = pack_po([(k, d1, d2) for k, d1, d2 in months])
log("   недели...")
po_weeks = pack_po([(k, lbl, d1, d2) for k, lbl, d1, d2 in weeks])
log("   год...")
po_year = prihod_oplata(year_from, year_to)
po_year_obj = {"suppliers": po_year, "prihod": sum(r["prihod"] for r in po_year), "oplata": sum(r["oplata"] for r in po_year), "n": len(po_year)}
log(f"   год: приход {po_year_obj['prihod']:,.0f} · оплата {po_year_obj['oplata']:,.0f} · поставщиков {po_year_obj['n']}")

# ---------- 2. Закупочные цены по позициям ----------
def ceny(d1, d2):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": ["Product.Name"],
            "aggregateFields": ["Amount", "Sum.Incoming"],
            "filters": {"DateTime.DateTyped": daterange_filter(d1, d2),
                        "Department": {"filterType": "IncludeValues", "values": [DEP]},
                        "TransactionType": {"filterType": "IncludeValues", "values": T_PRIHOD}}}
    out = []
    for x in olap(body):
        nm = (x.get("Product.Name") or "").strip()
        amt = x.get("Amount") or 0; sm = x.get("Sum.Incoming") or 0
        if not nm or abs(amt) < 0.001 or sm <= 0: continue
        out.append({"name": nm, "qty": round(amt, 2), "sum": round(sm), "price": round(sm / amt, 2)})
    out.sort(key=lambda x: -x["sum"])
    return out

log("2) цены: месяцы...")
ce_months = {k: {"products": ceny(d1, d2)} for k, d1, d2 in months}
log("   недели...")
ce_weeks = {k: {"label": lbl, "products": ceny(d1, d2)} for k, lbl, d1, d2 in weeks}
log("   год...")
ce_year = {"products": ceny(year_from, year_to)}
log(f"   год: позиций {len(ce_year['products'])}")

# ---------- 2в. Что закупали: товар × поставщик ----------
def tovary(d1, d2):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": ["Product.Name", "Product.MeasureUnit", "Counteragent.Name"],
            "aggregateFields": ["Amount", "Sum.Incoming"],
            "filters": {"DateTime.DateTyped": daterange_filter(d1, d2),
                        "Department": {"filterType": "IncludeValues", "values": [DEP]},
                        "TransactionType": {"filterType": "IncludeValues", "values": T_PRIHOD}}}
    out = []
    for x in olap(body):
        pn = (x.get("Product.Name") or "").strip()
        ca = (x.get("Counteragent.Name") or "—").strip()
        un = (x.get("Product.MeasureUnit") or "").strip()
        amt = x.get("Amount") or 0; sm = x.get("Sum.Incoming") or 0
        if not pn or abs(amt) < 0.001 or sm <= 0: continue
        out.append({"product": pn, "supplier": ca, "unit": un, "qty": round(amt, 2), "sum": round(sm), "price": round(sm / amt, 2)})
    out.sort(key=lambda x: -x["sum"])
    return out[:1500]

# ---------- 2г. Списания (WRITEOFF): что и сколько списали ----------
def spisanie(d1, d2):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": ["Product.Name", "Product.MeasureUnit"],
            "aggregateFields": ["Amount", "Sum.Incoming", "Sum.Outgoing"],
            "filters": {"DateTime.DateTyped": daterange_filter(d1, d2),
                        "Department": {"filterType": "IncludeValues", "values": [DEP]},
                        "TransactionType": {"filterType": "IncludeValues", "values": ["WRITEOFF"]}}}
    out = []
    for x in olap(body):
        pn = (x.get("Product.Name") or "").strip()
        un = (x.get("Product.MeasureUnit") or "").strip()
        amt = abs(x.get("Amount") or 0)
        sm = abs((x.get("Sum.Outgoing") or 0) - (x.get("Sum.Incoming") or 0)) or abs(x.get("Sum.Incoming") or 0)
        if not pn or (amt < 0.001 and sm < 1): continue
        out.append({"product": pn, "unit": un, "qty": round(amt, 2), "sum": round(sm)})
    out.sort(key=lambda x: -x["sum"])
    return out[:1200]

log("2в) что закупали: месяцы...")
tv_months = {k: {"rows": tovary(d1, d2)} for k, d1, d2 in months}
log("    недели...")
tv_weeks = {k: {"label": lbl, "rows": tovary(d1, d2)} for k, lbl, d1, d2 in weeks}
log("    год...")
tv_year = {"rows": tovary(year_from, year_to)}
log(f"    год: строк товар×поставщик {len(tv_year['rows'])}")

log("2г) списания: месяцы...")
sp_months = {k: spisanie(d1, d2) for k, d1, d2 in months}
log("    недели...")
sp_weeks = {k: spisanie(d1, d2) for k, lbl, d1, d2 in weeks}
log("    год...")
sp_year = spisanie(year_from, year_to)
log(f"    год: списано позиций {len(sp_year)}")

# ---------- День и Период: последние 14 дней (лёгкие срезы: приход/оплата, цены, что закупали) ----------
# Движение/остатки по дням не считаем (тяжёлые balance-снимки) — оборачиваемость остаётся по неделе/месяцу/году.
RUW = {0: "пн", 1: "вт", 2: "ср", 3: "чт", 4: "пт", 5: "сб", 6: "вс"}
NDAYS = 14
po_days = {}; ce_days = {}; tv_days = {}; day_keys = []; dmeta = {}
try:
    log("день) последние", NDAYS, "дней: приход/оплата · цены · что закупали...")
    for kk in range(NDAYS - 1, -1, -1):
        d1 = last_full - datetime.timedelta(days=kk)
        d2 = d1 + datetime.timedelta(days=1)
        key = d1.isoformat()
        day_keys.append(key)
        dmeta[key] = {"ru": d1.strftime("%d.%m") + " · " + RUW[d1.weekday()]}
        po_rows = prihod_oplata(d1, d2)
        po_days[key] = {"suppliers": po_rows,
                        "prihod": sum(r["prihod"] for r in po_rows),
                        "oplata": sum(r["oplata"] for r in po_rows), "n": len(po_rows)}
        ce_days[key] = {"products": ceny(d1, d2)}
        tv_days[key] = {"rows": tovary(d1, d2)}
    log("    дней собрано:", len(day_keys))
except Exception as e:
    log("день) ошибка — режимы День/Период пропущены:", e)
    po_days = {}; ce_days = {}; tv_days = {}; day_keys = []; dmeta = {}

# ---------- 3. Остатки по складам ----------
# имена складов (XML)
store_name = {}
try:
    txt = s.get(f"{URL}/resto/api/corporation/stores", params={"key": tok}, verify=False, timeout=120).text
    for m in re.finditer(r"<id>([^<]+)</id>\s*<(?:code|name)>[^<]*</(?:code|name)>?\s*(?:<name>([^<]*)</name>)?", txt):
        pass
    # надёжнее: пары id..name внутри каждого item
    for item in re.findall(r"<corporateItemDto[^>]*>.*?</corporateItemDto>", txt, re.S) or re.findall(r"<item[^>]*>.*?</item>", txt, re.S):
        i = re.search(r"<id>([^<]+)</id>", item); n = re.search(r"<name>([^<]*)</name>", item)
        if i and n: store_name[i.group(1)] = n.group(1)
    if not store_name:  # запасной разбор — все id/name по порядку
        ids = re.findall(r"<id>([^<]+)</id>", txt); nms = re.findall(r"<name>([^<]*)</name>", txt)
        for i, n in zip(ids, nms): store_name[i] = n
    log("3) складов с именами:", len(store_name))
except Exception as e:
    log("3) stores name err:", e)

_sb_cache = {}
def stores_balance(d):
    ck = d.isoformat()
    if ck in _sb_cache: return _sb_cache[ck]
    js = s.get(f"{URL}/resto/api/v2/reports/balance/stores", params={"key": tok, "timestamp": d.strftime("%Y-%m-%dT00:00:00")}, verify=False, timeout=180).json()
    byst = {}; total = 0
    prod = {}
    for r in js:
        sid = r.get("store"); sm = r.get("sum") or 0
        byst[sid] = byst.get(sid, 0) + sm; total += sm
        pr = r.get("product")
        prod.setdefault(sid, {}).setdefault(pr, [0, 0])
        prod[sid][pr][0] += r.get("amount") or 0; prod[sid][pr][1] += sm
    _sb_cache[ck] = (byst, total, prod)
    return byst, total, prod

_stock_cache = {}
def stock_qty(d):
    """Остаток КОЛИЧЕСТВА по товару (uuid) на дату d, суммарно по складам."""
    key = d.isoformat()
    if key in _stock_cache: return _stock_cache[key]
    js = s.get(f"{URL}/resto/api/v2/reports/balance/stores", params={"key": tok, "timestamp": d.strftime("%Y-%m-%dT00:00:00")}, verify=False, timeout=180).json()
    qty = {}
    for r in js:
        pid = r.get("product")
        qty[pid] = qty.get(pid, 0) + (r.get("amount") or 0)
    _stock_cache[key] = qty
    return qty

log("   остатки текущие...")
byst_cur, ost_total, prod_cur = stores_balance(today)
# имена товаров для топа по складам
prod_ids = set()
for sid, pm in prod_cur.items():
    for pid, (a, sm) in sorted(pm.items(), key=lambda x: -x[1][1])[:15]:
        prod_ids.add(pid)
prod_name = {}
try:
    pl = s.get(f"{URL}/resto/api/v2/entities/products/list", params={"key": tok, "includeDeleted": "false"}, verify=False, timeout=180).json()
    for p in pl:
        if p.get("id") in prod_ids or True:
            prod_name[p.get("id")] = p.get("name") or ""
    log("   товаров в справочнике:", len(prod_name))
except Exception as e:
    log("   products list err:", e)

ost_stores = []
for sid, sm in sorted(byst_cur.items(), key=lambda x: -x[1]):
    top = []
    for pid, (a, s2) in sorted(prod_cur.get(sid, {}).items(), key=lambda x: -x[1][1])[:12]:
        top.append({"name": prod_name.get(pid, pid), "amount": round(a, 2), "sum": round(s2)})
    ost_stores.append({"store": store_name.get(sid, sid), "sum": round(sm), "top": top})
log(f"   остатки итог {ost_total:,.0f} по {len(ost_stores)} складам")
# Полный список сырья на складе «Основной склад (сырье) ФЗ» — для халал-аналитики (по остаткам)
SYR_STORE = "Основной склад (сырье) ФЗ"
syr_sid = next((sid for sid in prod_cur if store_name.get(sid) == SYR_STORE), None)
sklad_syrye = {"store": SYR_STORE, "items": []}
if syr_sid:
    for pid, (a, sm) in prod_cur.get(syr_sid, {}).items():
        nm = prod_name.get(pid, "")
        if nm.startswith("С*"):
            sklad_syrye["items"].append({"name": nm, "qty": round(a, 3), "sum": round(sm)})
    sklad_syrye["items"].sort(key=lambda x: -x["sum"])
log(f"   сырьё на складе '{SYR_STORE}': {len(sklad_syrye['items'])} позиций для халал")

# тренд остатков по месяцам (конец месяца) и неделям (конец недели)
ost_trend_m = []
for mi in range(1, lastm + 1):
    de = min(eom(mi), last_full + datetime.timedelta(days=1))
    _, tot, _ = stores_balance(de)
    ost_trend_m.append({"k": f"{YEAR}-{mi:02d}", "label": RUM[mi], "total": round(tot)})
ost_trend_w = []
for key, lbl, ws, we in weeks[-8:]:
    _, tot, _ = stores_balance(we)
    ost_trend_w.append({"k": key, "label": lbl, "total": round(tot)})
log("   тренд остатков собран")

# ---------- Движение по складу: остаток нач -> закупили -> списали -> остаток кон ----------
def stock_by_name(d):
    out = {}
    for pid, q in stock_qty(d).items():
        nm = prod_name.get(pid)
        if nm: out[nm] = out.get(nm, 0) + q
    return out

def movement(d1, d2, tvrows, sprows):
    buy = {}; wo = {}; unit = {}
    for r in tvrows:
        buy[r["product"]] = buy.get(r["product"], 0) + r["qty"]; unit.setdefault(r["product"], r.get("unit") or "")
    for r in sprows:
        wo[r["product"]] = wo.get(r["product"], 0) + r["qty"]; unit.setdefault(r["product"], r.get("unit") or "")
    names = set(buy) | set(wo)
    if not names: return []
    op = stock_by_name(d1); cl = stock_by_name(d2)
    rows = []
    for nm in names:
        rows.append({"product": nm, "unit": unit.get(nm, ""),
                     "open": round(op.get(nm, 0), 2), "buy": round(buy.get(nm, 0), 2),
                     "writeoff": round(wo.get(nm, 0), 2), "close": round(cl.get(nm, 0), 2)})
    rows.sort(key=lambda x: -(x["buy"] + x["writeoff"]))
    return rows[:1500]

log("   движение по складу: месяцы...")
dv_months = {k: {"rows": movement(bom(mi), min(eom(mi), last_full + datetime.timedelta(days=1)), tv_months[k]["rows"], sp_months[k])} for mi, k in [(mi, f"{YEAR}-{mi:02d}") for mi in range(1, lastm + 1)]}
log("   недели...")
dv_weeks = {k: {"label": lbl, "rows": movement(ws, we, tv_weeks[k]["rows"], sp_weeks[k])} for k, lbl, ws, we in weeks}
log("   год...")
dv_year = {"rows": movement(year_from, year_to, tv_year["rows"], sp_year)}
log(f"   движение готово · строк(год) {len(dv_year['rows'])}")

# ---------- Разрез по складам: сырьё -> производство ----------
FOCUS = ["Основной склад (сырье) ФЗ", "Склад Производство ФЗ"]
name2id = {}
for sid, nm in store_name.items():
    name2id[nm] = sid
# ед. измерения по имени товара (из прихода/списаний)
unit_by_name = {}
for r in tv_year["rows"]:
    unit_by_name.setdefault(r["product"], r.get("unit") or "")
for r in sp_year:
    unit_by_name.setdefault(r["product"], r.get("unit") or "")

def flow_by_store(d1, d2, ttypes):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": ["Store"],
            "aggregateFields": ["Sum.Incoming"],
            "filters": {"DateTime.DateTyped": daterange_filter(d1, d2),
                        "Department": {"filterType": "IncludeValues", "values": [DEP]},
                        "TransactionType": {"filterType": "IncludeValues", "values": ttypes}}}
    out = {}
    for x in olap(body):
        st = (x.get("Store") or "").strip()
        out[st] = out.get(st, 0) + (x.get("Sum.Incoming") or 0)
    return out

log("склады) поток сырьё->производство: месяцы...")
def store_periods(periods, withlabel=False):
    res = {}
    for tup in periods:
        if withlabel:
            key, lbl, d1, d2 = tup
        else:
            key, d1, d2 = tup; lbl = (mmeta.get(key, {}) or {}).get("ru", key) if False else None
        bst1, _, _ = stores_balance(d1)
        bst2, _, _ = stores_balance(d2)
        pr = flow_by_store(d1, d2, T_PRIHOD)
        wo = flow_by_store(d1, d2, ["WRITEOFF"])
        per = {}
        for nm in FOCUS:
            sid = name2id.get(nm)
            per[nm] = {"open": round(bst1.get(sid, 0)), "close": round(bst2.get(sid, 0)),
                       "prihod": round(pr.get(nm, 0)), "spisanie": round(wo.get(nm, 0))}
        res[key] = {"stores": per}
        if withlabel: res[key]["label"] = lbl
    return res

sk_months = store_periods([(k, d1, d2) for k, d1, d2 in months])
log("   недели...")
sk_weeks = store_periods([(k, lbl, ws, we) for k, lbl, ws, we in weeks[-8:]], withlabel=True)
log("   год...")
sk_year_bst1, _, _ = stores_balance(year_from)
sk_year_bst2, _, _ = stores_balance(year_to)
sk_pr = flow_by_store(year_from, year_to, T_PRIHOD)
sk_wo = flow_by_store(year_from, year_to, ["WRITEOFF"])
sk_year = {"stores": {nm: {"open": round(sk_year_bst1.get(name2id.get(nm), 0)), "close": round(sk_year_bst2.get(name2id.get(nm), 0)),
                          "prihod": round(sk_pr.get(nm, 0)), "spisanie": round(sk_wo.get(nm, 0))} for nm in FOCUS}}

# текущий остаток по фокус-складам: топ товаров
sk_current = {}
for nm in FOCUS:
    sid = name2id.get(nm)
    pm = prod_cur.get(sid, {})
    top = []
    for pid, (a, s2) in sorted(pm.items(), key=lambda x: -x[1][1])[:15]:
        pnm = prod_name.get(pid, pid)
        top.append({"product": pnm, "unit": unit_by_name.get(pnm, ""), "qty": round(a, 2), "sum": round(s2)})
    sk_current[nm] = {"total": round(byst_cur.get(sid, 0)), "top": top}
log("   склады: разрез готов; приход по складам сработал:" + str(any(sk_year["stores"][n]["prihod"] for n in FOCUS)))

# ---------- 4. КЗ: компании и суммы долга из листа «КЗ» Google-файла ДЗ КЗ ----------
def num(v):
    if v is None: return 0.0
    v = str(v).replace("\xa0", "").replace(" ", "").replace(" ", "").replace(",", ".").strip()
    if not v or v in ("-", "—", "–"): return 0.0
    try: return float(v)
    except: return 0.0

log("4) КЗ из листа ДЗ КЗ (компании и суммы)...")
kz_rows = []; kz_date = ""
try:
    gr = requests.get(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={KZ_GID}", timeout=30)
    grows = list(csv.reader(io.StringIO(gr.content.decode("utf-8-sig"))))
    if len(grows) > 2 and grows[2]:
        kz_date = (grows[2][0] or "").strip()
    hdr = grows[3] if len(grows) > 3 else []
    log("   заголовки листа:", " | ".join((c or "")[:24] for c in hdr[:8]))
    # колонки: 0=Поставщик, 1=Задолженность перед поставщиками, 2=Приход товара, 3=Оплата
    for row in grows[4:]:
        nm = (row[0] if row else "").strip()
        if not nm or re.sub(r"[^0-9a-zа-яё]", "", nm.lower()) == "": continue
        if re.match(r"^[\d\s.,\-]+$", nm): continue  # строки-числа/итоги
        if re.match(r"^\s*(итого|итог|всего|total|остаток|баланс|сумма|результат)\b", nm, re.I): continue  # итоговые строки — не поставщики
        debt = num(row[1]) if len(row) > 1 else 0
        prihod = num(row[2]) if len(row) > 2 else 0
        oplata = num(row[3]) if len(row) > 3 else 0
        kz_rows.append({"name": nm, "debt": round(debt), "prihod": round(prihod), "oplata": round(oplata)})
    log(f"   компаний в листе: {len(kz_rows)} · дата листа: {kz_date}")
except Exception as e:
    log("   Google КЗ err:", e)
kz_rows.sort(key=lambda x: -x["debt"])
kz_total = sum(r["debt"] for r in kz_rows if r["debt"] > 0)
kz_ndebt = sum(1 for r in kz_rows if r["debt"] > 0)
log(f"   итог КЗ по листу: {kz_total:,.0f} · с долгом: {kz_ndebt} из {len(kz_rows)}")

# ---------- запись ----------
mmeta = {f"{YEAR}-{mi:02d}": {"ru": f"{RUM[mi]} {YEAR}"} for mi in range(1, lastm + 1)}
data = {
    "updated": today.strftime("%d.%m.%Y"),
    "updatedFull": today.strftime("%d.%m.%Y ") + almaty.now().strftime("%H:%M"),
    "through": last_full.strftime("%d.%m.%Y"),
    "months": [k for k, _, _ in months], "mmeta": mmeta,
    "weeks": [{"k": k, "label": lbl} for k, lbl, _, _ in weeks],
    "days": day_keys, "dmeta": dmeta,
    "prihodOplata": {"months": po_months, "weeks": po_weeks, "year": po_year_obj, "days": po_days},
    "ceny": {"months": ce_months, "weeks": ce_weeks, "year": ce_year, "days": ce_days},
    "tovary": {"months": tv_months, "weeks": tv_weeks, "year": tv_year, "days": tv_days},
    "dvizhenie": {"months": dv_months, "weeks": dv_weeks, "year": dv_year},
    "sklady": {"focus": FOCUS, "current": sk_current, "months": sk_months, "weeks": sk_weeks, "year": sk_year},
    "ostatki": {"total": round(ost_total), "stores": ost_stores, "trendM": ost_trend_m, "trendW": ost_trend_w},
    "sklad_syrye": sklad_syrye,
    "kz": {"total": kz_total, "date": kz_date, "listN": len(kz_rows), "ndebt": kz_ndebt, "rows": kz_rows},
}
json.dump(data, open(os.path.join(HERE, "zakup.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
sz = os.path.getsize(os.path.join(HERE, "zakup.json"))
log(f"ГОТОВО -> zakup.json  ({sz/1024:.0f} КБ)")
LOG.close(); print("OK")
