# -*- coding: utf-8 -*-
"""«Рычаги прибыли» — где завод теряет деньги и сколько стоит каждый рычаг.

Считает пять вещей, которые на пищевом производстве обычно и решают результат:
  1. Ценовая дисциплина — по какой цене один и тот же товар уходит разным
     покупателям и сколько денег стоит отклонение от средней цены завода.
  2. Хвост ассортимента — сколько позиций делают 80% выручки и чего стоит хвост.
  3. Потери — возвраты, порча, брак, недостачи: доля к выручке и её динамика.
  4. Ножницы — статьи затрат в % к выручке 2025 против 2026: что не сжалось
     вслед за оборотом.
  5. План — рычаги, ранжированные по деньгам в год.

Источники: iiko (contractor_items.js, sku_live.js) — свежие, до вчера;
управленческий ОПиУ (xlsx) — по закрытым месяцам, для потерь и структуры затрат.
Результат: рычаги.html. Запускается в CI после gen_contractor_items.py и SKU_iiko/generate.py.
"""
import io, json, os, re, datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = "рычаги.html"
MSS = ["", "янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

LOSS_LINES = [
    ("1.3.Недостача инвентаризации", "Недостача при инвентаризации"),
    ("1.30.Возвраты от дистрибьютеров", "Возвраты от дистрибьюторов"),
    ("1.16.Мусор", "Вывоз и утилизация"),
    ("1.28.Брак", "Брак"),
    ("1.7.Истек срок хранения (порча)", "Истёк срок хранения"),
    ("1.24.Бракераж", "Бракераж"),
    ("1.27.Нарушение тех.процесса", "Нарушение техпроцесса"),
    ("1.11.Списание сломанных ТМЗ", "Списание сломанных ТМЗ"),
    ("1.13.Коррекция отрицательных остатков на складе", "Коррекция минусовых остатков"),
]
SCISSOR_LINES = [
    ("1.1.Себестоимость продуктовая", "Продуктовая себестоимость", "var"),
    ("Итого 2.ФОТ Производство", "ФОТ производства", "fix"),
    ("ИТОГО 3.1.ФОТ АУП", "ФОТ АУП", "fix"),
    ("Логистика доставка", "Логистика доставки", "var"),
    ("1.18.Электроэнергия", "Электроэнергия", "var"),
    ("Итого 3.Арендная плата", "Аренда", "fix"),
    ("1.5.Расходный материал производство", "Расходные материалы", "var"),
    ("Итого 3.3. РазныеАдмРасходы", "Административные расходы", "fix"),
    ("2.4.Маркетинг", "Маркетинг", "fix"),
]


def load_js(fn):
    p = os.path.join(HERE, fn)
    if not os.path.exists(p):
        return None
    t = io.open(p, encoding="utf-8").read()
    i = t.index("=")
    obj, _ = json.JSONDecoder().raw_decode(t[i + 1:].lstrip())
    return obj


# ── 1. цена: индекс покупателя и разрывы по позициям ─────────────────────────
def prices(CTR, SKU, MOK):
    """Сравниваем цену каждого покупателя со средневзвешенной ценой завода
    на тот же самый товар. Это честное сравнение: набор товара у всех разный,
    поэтому берём его же набор и переоцениваем по средней цене."""
    year = {c["name"]: c for c in CTR.get("year", [])}
    if not year:
        return None
    tot = defaultdict(lambda: [0.0, 0.0])
    for c in year.values():
        for it in c.get("items", []):
            a = tot[it["n"]]
            a[0] += it.get("q") or 0
            a[1] += it.get("r") or 0

    y26 = [i for i, m in enumerate(MOK) if m.startswith("2026")]
    unit = {}
    for x in SKU.get("skus", []):
        q = sum(abs(x["monthly_qty"][i] or 0) for i in y26)
        if not q:
            continue
        r = sum(x["monthly_rev"][i] or 0 for i in y26)
        v = sum(x["monthly_vp"][i] or 0 for i in y26)
        unit[x["name"]] = (r - v) / q

    rows = []
    for cn, c in year.items():
        if (c.get("rev") or 0) < 15_000_000:
            continue
        gap = base = 0.0
        items = []
        for it in c.get("items", []):
            q = it.get("q") or 0
            r = it.get("r") or 0
            if q <= 0:
                continue
            tq, tr = tot[it["n"]]
            if tq <= 0:
                continue
            avg = tr / tq
            g = q * avg - r
            gap += g
            base += q * avg
            if abs(g) > 200_000:
                items.append({"n": it["n"], "q": round(q), "p": round(r / q),
                              "avg": round(avg), "g": round(g),
                              "c": round(unit.get(it["n"], 0))})
        items.sort(key=lambda x: -x["g"])
        rows.append({"n": cn, "rev": round(c.get("rev") or 0), "gap": round(gap),
                     "pct": round(gap / base * 100, 1) if base else 0,
                     "items": items[:12] + ([] if len(items) <= 12 else items[-4:])})
    rows.sort(key=lambda x: -x["gap"])
    # Скидка обязана расти с объёмом: дистрибьютор берёт дешевле розницы, это норма.
    # Аномалия — когда мелкий покупатель берёт дешевле крупного.
    for r in rows:
        bigger = [q for q in rows if q["rev"] >= r["rev"] * 2]
        worst_big = max([q["pct"] for q in bigger], default=None)
        r["anom"] = bool(bigger) and r["pct"] > (worst_big or 0) + 3 and r["pct"] > 5
        r["bigger"] = (max(bigger, key=lambda q: q["rev"])["n"] if bigger else "")
        r["biggerpct"] = worst_big if bigger else None
    return rows


# ── 2. хвост ассортимента ────────────────────────────────────────────────────
def assortment(SKU, MOK):
    y26 = [i for i, m in enumerate(MOK) if m.startswith("2026")]
    rows = []
    promo = []
    for x in SKU.get("skus", []):
        rev = sum(x["monthly_rev"][i] or 0 for i in y26)
        vp = sum(x["monthly_vp"][i] or 0 for i in y26)
        q = sum(abs(x["monthly_qty"][i] or 0) for i in y26)
        mo = sum(1 for i in y26 if (x["monthly_rev"][i] or 0) > 0)
        if q > 0 and rev < q * 5:            # отгружено практически бесплатно — акция
            promo.append({"n": x["name"], "q": round(q), "c": round(-vp)})
            continue
        if rev <= 0:
            continue
        rows.append({"n": x["name"], "cat": x.get("cat") or "—", "rev": rev,
                     "vp": vp, "q": q, "mo": mo})
    rows.sort(key=lambda r: -r["rev"])
    tot = sum(r["rev"] for r in rows) or 1
    totvp = sum(r["vp"] for r in rows)
    cum = 0
    n80 = n95 = 0
    curve = []
    for i, r in enumerate(rows, 1):
        cum += r["rev"]
        if not n80 and cum >= tot * 0.8:
            n80 = i
        if not n95 and cum >= tot * 0.95:
            n95 = i
        if i % max(1, len(rows) // 160) == 0 or i == len(rows):
            curve.append([i, round(cum / tot * 100, 2)])
    tail = [r for r in rows if r["rev"] < 1_000_000]
    neg = [r for r in rows if r["vp"] < 0]
    neg.sort(key=lambda r: r["vp"])
    promo.sort(key=lambda p: -p["c"])
    by_cat = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        a = by_cat[r["cat"]]
        a[0] += r["rev"]; a[1] += r["vp"]; a[2] += 1
    cats = [{"n": k, "rev": round(v[0]), "vp": round(v[1]), "cnt": v[2],
             "m": round(v[1] / v[0] * 100, 1) if v[0] else 0}
            for k, v in by_cat.items() if v[0] > 3_000_000]
    cats.sort(key=lambda c: -c["rev"])
    return {
        "n": len(rows), "rev": round(tot), "vp": round(totvp),
        "n80": n80, "n95": n95, "curve": curve,
        "tail": {"cnt": len(tail), "rev": round(sum(r["rev"] for r in tail)),
                 "vp": round(sum(r["vp"] for r in tail)),
                 "once": sum(1 for r in tail if r["mo"] <= 2)},
        "top": [{"n": r["n"], "rev": round(r["rev"]), "vp": round(r["vp"]),
                 "m": round(r["vp"] / r["rev"] * 100, 1)} for r in rows[:20]],
        "neg": [{"n": r["n"], "rev": round(r["rev"]), "vp": round(r["vp"]),
                 "q": round(r["q"])} for r in neg[:12]],
        "negtot": round(sum(r["vp"] for r in neg)), "negcnt": len(neg),
        "promo": promo[:12], "promotot": round(sum(p["c"] for p in promo)),
        "promoqty": sum(p["q"] for p in promo), "promocnt": len(promo),
        "cats": cats[:14],
    }


# ── 3-4. потери и ножницы (управленческий ОПиУ) ──────────────────────────────
def opiu():
    try:
        from gen_fullcost import load_pl
    except Exception as e:
        print("[!] ОПиУ не прочитан:", e)
        return None
    months, R = load_pl()

    def v(k, ms):
        d = R.get(k, {})
        return sum(d.get(m, 0) for m in ms)

    y25 = [m for m in months if m.startswith("2025")]
    y26 = [m for m in months if m.startswith("2026")]
    if not y25 or not y26:
        return None
    r25, r26 = v("Итого Выручка", y25), v("Итого Выручка", y26)
    if not r25 or not r26:
        return None

    loss = []
    for k, t in LOSS_LINES:
        a, b = v(k, y25), v(k, y26)
        if abs(a) + abs(b) < 300_000:
            continue
        loss.append({"n": t, "a": round(a), "b": round(b),
                     "pa": round(a / r25 * 100, 2), "pb": round(b / r26 * 100, 2)})
    loss.sort(key=lambda x: -x["pb"])
    lt25 = sum(x["a"] for x in loss)
    lt26 = sum(x["b"] for x in loss)

    lmon = []
    for m in months:
        s = sum(R.get(k, {}).get(m, 0) for k, _ in LOSS_LINES)
        rv = R.get("Итого Выручка", {}).get(m, 0)
        if rv:
            lmon.append([m, round(s), round(s / rv * 100, 2)])

    sc = []
    for k, t, g in SCISSOR_LINES:
        a, b = v(k, y25), v(k, y26)
        if not a and not b:
            continue
        pa, pb = a / r25 * 100, b / r26 * 100
        am, bm = a / len(y25), b / len(y26)
        sc.append({"n": t, "g": g, "pa": round(pa, 2), "pb": round(pb, 2),
                   "d": round(pb - pa, 2), "money": round((pb - pa) / 100 * r26),
                   "am": round(am), "bm": round(bm),
                   "dm": round(bm - am), "dmp": round((bm / am - 1) * 100, 1) if am else 0})
    sc.sort(key=lambda x: -x["d"])

    return {"m25": len(y25), "m26": len(y26), "r25": round(r25), "r26": round(r26),
            "first": months[0], "last": months[-1],
            "loss": loss, "lt25": round(lt25), "lt26": round(lt26),
            "pl25": round(lt25 / r25 * 100, 2), "pl26": round(lt26 / r26 * 100, 2),
            "lmon": lmon, "sc": sc}


def build():
    CTR = load_js("contractor_items.js")
    SKU = load_js("sku_live.js")
    if not CTR or not SKU:
        raise SystemExit("нет contractor_items.js / sku_live.js")
    MOK = SKU.get("mo_keys") or []
    P = prices(CTR, SKU, MOK)
    A = assortment(SKU, MOK)
    O = opiu()

    mo26 = [m for m in MOK if m.startswith("2026")]
    nmo = len([m for m in mo26 if any((x["monthly_rev"][MOK.index(m)] or 0) for x in SKU["skus"][:200])]) or len(mo26)
    year_k = 12.0 / max(1, nmo)

    # ── рычаги в деньгах на год ──
    lev = []
    if P:
        under = [r for r in P if r["gap"] > 3_000_000]
        anom = [r for r in P if r.get("anom")]
        if under:
            lev.append({
                "t": "Подтянуть цену отстающих покупателей к средней",
                "money": round(sum(r["gap"] for r in under) * year_k * 0.5),
                "full": round(sum(r["gap"] for r in under) * year_k),
                "who": ", ".join(r["n"].split("(")[0].strip() for r in under[:3]),
                "how": ("Разрыв к средней цене завода на их же набор товара — %s за %d мес. "
                        "Скидка обязана расти с объёмом, поэтому у дистрибьютора цена ниже — это норма. "
                        % (fmt(sum(r["gap"] for r in under)), nmo)) +
                       (("Ненормально другое: %s берёт на %s%% ниже средней при обороте %s — глубже, "
                         "чем %s с оборотом %s. Такая скидка объёмом не объясняется." %
                         (anom[0]["n"], rus(anom[0]["pct"]), fmt(anom[0]["rev"]),
                          anom[0]["bigger"], fmt([q for q in P if q["n"] == anom[0]["bigger"]][0]["rev"])))
                        if anom else
                        "Половина разрыва обычно отыгрывается пересмотром прайса, вторая половина — плата за объём и отсрочку."),
                "hard": "переговоры", "k": "price"})
    if O:
        back = (O["pl26"] - O["pl25"]) / 100 * O["r26"] * (12.0 / max(1, O["m26"]))
        if back > 0:
            lev.append({
                "t": "Вернуть потери к уровню прошлого года",
                "money": round(back), "full": round(back),
                "who": ", ".join(x["n"] for x in O["loss"][:2]),
                "how": "Потери выросли с %s%% до %s%% выручки. Возврат к прошлогодней доле — "
                       "это %s в год при нынешнем обороте. Основной вклад: %s." %
                       (rus(O["pl25"]), rus(O["pl26"]), fmt(back),
                        ", ".join("%s %s%%" % (x["n"].lower(), rus(x["pb"])) for x in O["loss"][:2])),
                "hard": "процессы и учёт", "k": "loss"})
        for x in O["sc"][:3]:
            if x["d"] < 0.4:
                continue
            grew = x["dm"] > am_eps(x["am"])
            lev.append({
                "t": ("Сократить «%s» вслед за выручкой" % x["n"]) if not grew
                     else ("Остановить рост статьи «%s»" % x["n"]),
                "money": round(x["money"] * (12.0 / max(1, O["m26"]))),
                "full": round(x["money"] * (12.0 / max(1, O["m26"]))),
                "who": x["n"],
                "how": ("Статья съедает %s%% выручки против %s%% в прошлом году: +%s пункта, "
                        "или %s в год на нынешнем обороте. " %
                        (rus(x["pb"]), rus(x["pa"]), rus(x["d"]),
                         fmt(x["money"] * (12.0 / max(1, O["m26"]))))) +
                       (("В тенге статья выросла: %s в месяц против %s — это %s%% роста при падающей выручке." %
                         (fmt(x["bm"]), fmt(x["am"]), rus(x["dmp"], 0))) if grew else
                        ("В тенге статья почти не изменилась (%s в месяц против %s) — доля выросла потому, "
                         "что упала выручка. Значит рычага два: либо вернуть объём, либо резать саму статью." %
                         (fmt(x["bm"]), fmt(x["am"])))),
                "hard": "решение руководства" if x["g"] == "fix" else "операционка",
                "k": "scissors"})
    if A["promotot"] > 500_000:
        lev.append({
            "t": "Посчитать акции как расход, а не как «ноль»",
            "money": round(A["promotot"] * year_k * 0.3), "full": round(A["promotot"] * year_k),
            "who": "позиции «Акция N+1»",
            "how": "%d штук отгружено по нулевой цене, себестоимость %s за %d мес. "
                   "Это реальные деньги, но в отчётности они растворяются в себестоимости: "
                   "по каждой акции не видно ни отдачи, ни окупаемости." %
                   (A["promoqty"], fmt(A["promotot"]), nmo),
            "hard": "учёт", "k": "promo"})
    if A["tail"]["cnt"] > 200:
        lev.append({
            "t": "Проредить хвост ассортимента",
            "money": 0, "full": 0,
            "who": "%d позиций из %d" % (A["tail"]["cnt"], A["n"]),
            "how": "%d позиций (%s%% ассортимента) дают %s%% выручки. Прямой экономии в ОПиУ они "
                   "не создают, но каждая позиция — это переналадка, отдельная закупка, остаток "
                   "с коротким сроком и место на складе. Сокращение хвоста высвобождает мощность "
                   "под ходовые SKU, а не режет затраты напрямую." %
                   (A["tail"]["cnt"], rus(A["tail"]["cnt"] / A["n"] * 100, 0),
                    rus(A["tail"]["rev"] / A["rev"] * 100, 0)),
            "hard": "ассортиментный комитет", "k": "tail"})
    lev.sort(key=lambda x: -x["money"])

    return {"prices": P, "asrt": A, "opiu": O, "lev": lev, "nmo": nmo,
            "mo26": mo26,
            "updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))
                       .strftime("%d.%m.%Y %H:%M"),
            "through": (SKU.get("through") or (load_js("sku_live.js") or {}).get("updated") or "")}


def am_eps(a):
    return a * 0.05


def rus(v, d=1):
    return (("%." + str(d) + "f") % v).replace(".", ",")


def fmt(v):
    a = abs(v) / 1e6
    s = ("%.0f" if a >= 100 else "%.1f") % a
    return ("−" if v < 0 else "") + s.replace(".", ",") + " млн ₸"


def main():
    data = build()
    tpl = io.open(os.path.join(HERE, "_шаблон_рычаги.html"), encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    io.open(os.path.join(HERE, OUT), "w", encoding="utf-8").write(html)
    tot = sum(l["money"] for l in data["lev"])
    print("Рычаги прибыли: %d рычагов на %.1f млн ₸/год, покупателей %d, SKU %d, потери %.2f%%"
          % (len(data["lev"]), tot / 1e6, len(data["prices"] or []),
             data["asrt"]["n"], (data["opiu"] or {}).get("pl26", 0)))


if __name__ == "__main__":
    main()
