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

out = {
    "updated": D.get("updatedFull") or D.get("updated") or "",
    "through": through, "week": last, "label": W[last]["label"],
    "prevLabel": (W[prev]["label"] if prev else ""),
    "weekSum": round(sum((r.get("sum") or 0) for r in rows)),
    "prevWeekSum": round(sum((r.get("sum") or 0) for r in (W[prev].get("rows") if prev else []))),
    "n": len(rows), "top": top,
}
open(os.path.join(HERE, "zakup_top.js"), "w", encoding="utf-8").write(
    "window.ZAKUP_TOP=" + json.dumps(out, ensure_ascii=False) + ";")
print("zakup_top.js: неделя %s, позиций %d, лидер %s — %s ₸%s" % (
    out["label"], out["n"], top[0]["n"] if top else "—",
    format(top[0]["sum"], ",").replace(",", " ") if top else "0",
    " (рекорд года)" if top and top[0]["rec"] else ""))
