# -*- coding: utf-8 -*-
"""Рекорды закупа за неделю — маленький файл для плашки на главной.

Главная не может тянуть zakup_data.js (почти мегабайт сжатых данных ради двух
строк), поэтому рядом кладём zakup_top.js: что больше всего закупили за
последнюю ПОЛНУЮ неделю, с прошлой неделей и годовым максимумом по той же
позиции — чтобы «рекорд» был рекордом, а не просто лидером недели.

Источник — zakup.json, если он рядом; иначе распаковываем уже собранный
zakup_data.js. Второй путь позволяет пересобрать плашку, не дёргая айко.
"""
import os, sys, json, re, gzip, base64, datetime
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))

def load():
    p = os.path.join(HERE, "zakup.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    t = open(os.path.join(HERE, "zakup_data.js"), encoding="utf-8").read()
    m = re.search(r'window\.__ZG="([^"]+)"', t)
    if not m:
        raise SystemExit("zakup_data.js не в ожидаемом формате")
    return json.loads(gzip.decompress(base64.b64decode(m.group(1))).decode("utf-8"))

D = load()
W = (D.get("tovary") or {}).get("weeks") or {}
if not W:
    raise SystemExit("в данных закупа нет недельного разреза")

through = D.get("through") or ""
dd, mm, yy = (through.split(".") + ["", "", ""])[:3]
th = datetime.date(int(yy), int(mm), int(dd)) if yy else None

def week_end(label):
    """Конец недели из подписи «14.09–20.09». Неделя, заехавшая на январь,
    считается прошлогодней — иначе декабрьская подпись дала бы дату в будущем."""
    a = label.split("–")[-1].strip()
    d2, m2 = a.split(".")
    y = th.year if th else datetime.date.today().year
    if th and int(m2) == 12 and th.month == 1:
        y -= 1
    return datetime.date(y, int(m2), int(d2))

# Берём только закрытые недели: в текущей закуп ещё идёт, и «рекорд» по ней
# был бы недосчитанным.
closed = [k for k in sorted(W) if th and week_end(W[k]["label"]) <= th]
if not closed:
    closed = sorted(W)[:-1] or sorted(W)
last = closed[-1]
prev = closed[-2] if len(closed) > 1 else None

rows = sorted(W[last].get("rows") or [], key=lambda r: -(r.get("sum") or 0))
prev_sum = {r["product"]: r.get("sum") or 0 for r in (W[prev].get("rows") if prev else [])}

# Годовой максимум по каждой позиции — по всем неделям, включая незакрытую:
# если рекорд поставлен раньше, он останется рекордом.
best = {}
for k in sorted(W):
    for r in W[k].get("rows") or []:
        s = r.get("sum") or 0
        if s > best.get(r["product"], (0, ""))[0]:
            best[r["product"]] = (s, W[k]["label"])

def short(n):
    """Убираем служебные префиксы номенклатуры: «С* », «У* », «ПФ* »."""
    return re.sub(r"^[А-ЯA-Z]{1,3}\*\s*", "", str(n or "")).strip()

top = []
for r in rows[:5]:
    s = r.get("sum") or 0
    mx, mxl = best.get(r["product"], (0, ""))
    top.append({
        "n": short(r.get("product")), "full": r.get("product"),
        "sup": r.get("supplier") or "", "u": r.get("unit") or "",
        "qty": round(r.get("qty") or 0, 1), "sum": round(s),
        "price": round(r.get("price") or 0, 2),
        "prev": round(prev_sum.get(r["product"], 0)),
        "rec": abs(mx - s) < 1,                 # неделя и есть годовой максимум
        "maxSum": round(mx), "maxLabel": mxl,
    })

# ── что подорожало за неделю ─────────────────────────────────────────
# Сравниваем цену за единицу с прошлой неделей по одним и тем же позициям.
# Мелочь отсекаем: на закупке в пару тысяч скачок цены ничего не значит,
# а в плашку попал бы первым.
CW = (D.get("ceny") or {}).get("weeks") or {}
MIN_SUM = 150000
up = []
if CW.get(last) and prev and CW.get(prev):
    A = {x["name"]: x for x in CW[last].get("products") or []}
    B = {x["name"]: x for x in CW[prev].get("products") or []}
    for n, a in A.items():
        b = B.get(n)
        if not b: continue
        pa, pb = a.get("price") or 0, b.get("price") or 0
        if pa <= 0 or pb <= 0 or (a.get("sum") or 0) < MIN_SUM: continue
        q = a.get("qty") or 0
        up.append({"n": short(n), "full": n, "was": round(pb, 2), "now": round(pa, 2),
                   "d": round((pa / pb - 1) * 100, 1), "sum": round(a.get("sum") or 0),
                   "qty": round(q, 1),
                   # переплата: во сколько обошёлся рост цены на этом объёме.
                   # Сортируем по ней, а не по процентам — иначе наверху
                   # оказывался бы скачок на копеечной позиции.
                   "over": round(q * (pa - pb))})
    up.sort(key=lambda x: -x["over"])
up = [x for x in up if x["d"] > 0][:5]

# ── что взяли впервые (или после долгого перерыва) ───────────────────
# «Впервые» считаем по всем неделям года, а не только по прошлой: иначе
# позиция, которую берут раз в месяц, каждый раз выглядела бы новинкой.
seen_before = {}
for k in sorted(W):
    if k >= last: break
    for r in W[k].get("rows") or []:
        seen_before[r["product"]] = W[k]["label"]
fresh = []
for r in rows:
    if (r.get("sum") or 0) < 300000: continue
    was = seen_before.get(r["product"])
    if was is None:
        fresh.append({"n": short(r.get("product")), "full": r.get("product"), "sup": r.get("supplier") or "",
                      "u": r.get("unit") or "", "qty": round(r.get("qty") or 0, 1),
                      "sum": round(r.get("sum") or 0), "first": True, "lastSeen": ""})
    else:
        gap = [k for k in sorted(W) if k < last and any(x["product"] == r["product"] for x in (W[k].get("rows") or []))]
        weeks_ago = len([k for k in sorted(W) if k < last]) - (sorted(W).index(gap[-1]) if gap else 0)
        if weeks_ago >= 4:
            fresh.append({"n": short(r.get("product")), "full": r.get("product"), "sup": r.get("supplier") or "",
                          "u": r.get("unit") or "", "qty": round(r.get("qty") or 0, 1),
                          "sum": round(r.get("sum") or 0), "first": False, "lastSeen": was})
fresh.sort(key=lambda x: -x["sum"])
fresh = fresh[:4]

out = {
    "up": up, "fresh": fresh,
    "updated": D.get("updatedFull") or D.get("updated") or "",
    "through": through, "week": last, "label": W[last]["label"],
    "prevLabel": (W[prev]["label"] if prev else ""),
    "weekSum": round(sum((r.get("sum") or 0) for r in rows)),
    "prevWeekSum": round(sum((r.get("sum") or 0) for r in (W[prev].get("rows") if prev else []))),
    "n": len(rows), "top": top,
}
open(os.path.join(HERE, "zakup_top.js"), "w", encoding="utf-8").write(
    "window.ZAKUP_TOP=" + json.dumps(out, ensure_ascii=False) + ";")
print("zakup_top.js: подорожало %d, впервые/после перерыва %d" % (len(up), len(fresh)))
print("zakup_top.js: неделя %s, позиций %d, лидер %s — %s ₸%s" % (
    out["label"], out["n"], top[0]["n"] if top else "—",
    format(top[0]["sum"], ",").replace(",", " ") if top else "0",
    " (рекорд года)" if top and top[0]["rec"] else ""))
