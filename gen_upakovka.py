# -*- coding: utf-8 -*-
"""
УПАКОВКА из iiko -> upak_data.js

Отдельное направление закупа. Раздел «Закуп» отдаёт только крупнейшие
строки месяца, и по упаковке этого мало: половина позиций в месячные
срезы не попадает, а разреза по складам там нет вовсе. Здесь собирается
полный срез именно по упаковке — её видно по префиксу «У*» в названии.

Что собирается:
  1) справочники товаров и складов;
  2) остатки на сегодня: склад × позиция, количество и сумма (полностью,
     без обрезки) — отвечает на вопрос «где лежит, а где пусто»;
  3) движение по месяцам: приход и расход по позиции и по складу —
     отсюда видно, пользуемся ли позицией вообще и на каком складе;
  4) закуп по поставщикам: кто и на сколько поставляет каждую позицию.

Только чтение. Пишет upak_data.js и upak_LOG.txt.
"""
import sys, os, json, datetime, warnings, re
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import almaty
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import requests, hashlib
from iiko_export import URL, LOGIN, PASS

HERE = _os.path.dirname(_os.path.abspath(__file__))
DEP = "Фуд завод"
PFX = "У*"                     # так упаковка помечена в номенклатуре
MONTHS_BACK = 12
LOG = open(_os.path.join(HERE, "upak_LOG.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

s = requests.Session()
tok = s.get(f"{URL}/resto/api/auth",
            params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
            verify=False, timeout=60).text.strip().strip('"')
log("iiko auth ok", almaty.now().strftime("%H:%M:%S"))

def olap(body):
    r = s.post(f"{URL}/resto/api/v2/reports/olap",
               headers={"Cookie": f"key={tok}", "Content-Type": "application/json"},
               data=json.dumps(body), verify=False, timeout=300)
    if r.status_code != 200:
        log("  OLAP ERR", r.status_code, r.text[:180]); return []
    return r.json().get("data", [])

today = almaty.today()
last_full = today - datetime.timedelta(days=1)

def months_list(n):
    out, y, m = [], today.year, today.month
    for _ in range(n):
        out.append("%04d-%02d" % (y, m))
        m -= 1
        if m == 0: y, m = y - 1, 12
    return list(reversed(out))
MONTHS = months_list(MONTHS_BACK)
def m_bounds(key):
    y, m = int(key[:4]), int(key[5:])
    d1 = datetime.date(y, m, 1)
    d2 = datetime.date(y + (m == 12), 1 if m == 12 else m + 1, 1)
    return d1, min(d2, today + datetime.timedelta(days=1))

# ── 1. справочники ──────────────────────────────────────────────
log("1) справочники")
prod_name, prod_unit = {}, {}
pl = s.get(f"{URL}/resto/api/v2/entities/products/list",
           params={"key": tok, "includeDeleted": "false"}, verify=False, timeout=180).json()
for p in pl:
    prod_name[p.get("id")] = p.get("name") or ""
    prod_unit[p.get("id")] = (p.get("mainUnit") or p.get("unitName") or "") or ""
log("   товаров:", len(prod_name))

store_name = {}
try:
    txt = s.get(f"{URL}/resto/api/corporation/stores", params={"key": tok},
                verify=False, timeout=120).text
    for item in (re.findall(r"<corporateItemDto[^>]*>.*?</corporateItemDto>", txt, re.S)
                 or re.findall(r"<item[^>]*>.*?</item>", txt, re.S)):
        i = re.search(r"<id>([^<]+)</id>", item); n = re.search(r"<name>([^<]*)</name>", item)
        if i and n: store_name[i.group(1)] = n.group(1)
    if not store_name:
        ids = re.findall(r"<id>([^<]+)</id>", txt); nms = re.findall(r"<name>([^<]*)</name>", txt)
        for i, n in zip(ids, nms): store_name[i] = n
except Exception as e:
    log("   склады: ошибка", e)
log("   складов:", len(store_name))

def is_pack(name): return str(name or "").startswith(PFX)

# ── 2. остатки: склад × позиция ────────────────────────────────
log("2) остатки по складам")
bal = s.get(f"{URL}/resto/api/v2/reports/balance/stores",
            params={"key": tok, "timestamp": today.strftime("%Y-%m-%dT00:00:00")},
            verify=False, timeout=180).json()
stock = {}          # позиция -> склад -> [кол-во, сумма]
for r in bal:
    pid = r.get("product"); nm = prod_name.get(pid, "")
    if not is_pack(nm): continue
    sid = store_name.get(r.get("store"), r.get("store"))
    a = stock.setdefault(nm, {}).setdefault(sid, [0.0, 0.0])
    a[0] += r.get("amount") or 0
    a[1] += r.get("sum") or 0
log("   позиций упаковки с остатком:", len(stock))

# ── 3. движение по месяцам: позиция × склад ────────────────────
log("3) движение по месяцам")
def moves(d1, d2, by_store):
    fields = ["Product.Name"] + (["Store"] if by_store else [])
    body = {"reportType": "TRANSACTIONS", "buildSummary": "false",
            "groupByRowFields": fields,
            "aggregateFields": ["Amount.In", "Amount.Out"],
            "filters": {"DateTime.Typed": {"filterType": "DateRange", "periodType": "CUSTOM",
                          "from": d1.isoformat(), "to": d2.isoformat(),
                          "includeLow": True, "includeHigh": False},
                        "Department": {"filterType": "IncludeValues", "values": [DEP]}}}
    return olap(body)

mv = {}             # месяц -> позиция -> склад -> [приход, расход]
mv_tot = {}         # месяц -> позиция -> [приход, расход]
store_ok = None
for k in MONTHS:
    d1, d2 = m_bounds(k)
    if d1 >= d2: continue
    rows = moves(d1, d2, True)
    if store_ok is None:
        store_ok = any((r.get("Store") or "").strip() for r in rows)
        log("   разрез по складам:", "есть" if store_ok else "iiko его не отдаёт")
    if not store_ok:
        rows = moves(d1, d2, False)
    for r in rows:
        nm = r.get("Product.Name") or ""
        if not is_pack(nm): continue
        st = (r.get("Store") or "").strip() or "—"
        i = float(r.get("Amount.In") or 0); o = float(r.get("Amount.Out") or 0)
        if not i and not o: continue
        a = mv.setdefault(k, {}).setdefault(nm, {}).setdefault(st, [0.0, 0.0])
        a[0] += i; a[1] += o
        b = mv_tot.setdefault(k, {}).setdefault(nm, [0.0, 0.0])
        b[0] += i; b[1] += o
    log("   %s: позиций %d" % (k, len(mv.get(k, {}))))

# ── 4. закуп по поставщикам ────────────────────────────────────
log("4) закуп по поставщикам")
def buys(d1, d2):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "false",
            "groupByRowFields": ["Product.Name", "Counteragent.Name", "Product.MeasureUnit"],
            "aggregateFields": ["Sum.Incoming", "Amount.In"],
            "filters": {"DateTime.Typed": {"filterType": "DateRange", "periodType": "CUSTOM",
                          "from": d1.isoformat(), "to": d2.isoformat(),
                          "includeLow": True, "includeHigh": False},
                        "TransactionType": {"filterType": "IncludeValues", "values": ["INVOICE"]},
                        "Department": {"filterType": "IncludeValues", "values": [DEP]}}}
    return olap(body)

buy = {}            # позиция -> поставщик -> [сумма, кол-во]
buy_m = {}          # месяц -> позиция -> сумма
unit = {}
for k in MONTHS:
    d1, d2 = m_bounds(k)
    if d1 >= d2: continue
    for r in buys(d1, d2):
        nm = r.get("Product.Name") or ""
        if not is_pack(nm): continue
        sup = (r.get("Counteragent.Name") or "").strip() or "—"
        sm = float(r.get("Sum.Incoming") or 0); q = float(r.get("Amount.In") or 0)
        if not sm and not q: continue
        a = buy.setdefault(nm, {}).setdefault(sup, [0.0, 0.0])
        a[0] += sm; a[1] += q
        buy_m.setdefault(k, {})[nm] = buy_m.setdefault(k, {}).get(nm, 0) + sm
        u = (r.get("Product.MeasureUnit") or "").strip()
        if u: unit[nm] = u
log("   позиций в закупе:", len(buy))

# ── 5. сборка ──────────────────────────────────────────────────
names = sorted(set(list(stock.keys()) + list(buy.keys())
                   + [n for k in mv_tot for n in mv_tot[k]]))
log("5) всего позиций упаковки:", len(names))

items = []
for nm in names:
    st = stock.get(nm, {})
    items.append({
        "n": nm,
        "u": unit.get(nm, ""),
        "st": {k: [round(v[0], 2), round(v[1])] for k, v in st.items() if abs(v[0]) > 0.0001 or abs(v[1]) > 0.5},
        "mv": {k: {s2: [round(v[0], 2), round(v[1], 2)] for s2, v in (mv.get(k, {}).get(nm) or {}).items()}
               for k in MONTHS if mv.get(k, {}).get(nm)},
        "sup": {k: [round(v[0]), round(v[1], 2)] for k, v in (buy.get(nm) or {}).items()},
    })

out = {
    "updated": almaty.now().strftime("%d.%m.%Y %H:%M"),
    "through": last_full.isoformat(),
    "months": MONTHS,
    "storeSplit": bool(store_ok),
    "stores": sorted({s2 for it in items for s2 in it["st"]}
                     | {s2 for it in items for k in it["mv"] for s2 in it["mv"][k]}),
    "items": items,
}
p = _os.path.join(HERE, "upak_data.js")
tmp = p + ".tmp"
open(tmp, "w", encoding="utf-8").write("window.UPAK=" + json.dumps(out, ensure_ascii=False) + ";\n")
_os.replace(tmp, p)
log("готово: upak_data.js %d КБ, позиций %d, складов %d"
    % (_os.path.getsize(p) // 1024, len(items), len(out["stores"])))
