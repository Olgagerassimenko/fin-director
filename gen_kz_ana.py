# -*- coding: utf-8 -*-
"""Аналитика кредиторской задолженности для страницы ДЗ/КЗ.

Читает готовые данные закупа (zakup_data.js) и складывает из них ответ на один
вопрос: сходятся ли поступления на склад с оплатами, и где закуп перекошен —
что берут сверх обычного, а что регулярно пропускают.

Считаются:
  weeks    — понедельно: поступило, оплачено, разрыв, накопленный разрыв,
             плюс сколько позиций взято сверх нормы и сколько пропущено;
  sup      — перекос по поставщикам за весь доступный период;
  advance  — кому платим заметно вперёд отгрузок (деньги ушли, товара нет);
  over6    — что заказано выше среднемесячного за 6 месяцев;
  spikes   — позиции последней полной недели, взятые сверх обычного;
  gaps     — регулярные позиции, которые на последней неделе не купили вовсе;
  frozen   — остатки сырья, которых хватит больше чем на 3 недели.

Пишет kz_ana.js рядом со страницей. Запускать после gen_zakup.py.
"""
import base64, gzip, json, os, re, statistics
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import almaty  # время завода — Алматы (UTC+5), не UTC раннера

HERE = os.path.dirname(os.path.abspath(__file__))


def load_zakup():
    src = open(os.path.join(HERE, "zakup_data.js"), encoding="utf-8").read()
    m = re.search(r'window\.__ZG\s*=\s*"([A-Za-z0-9+/=]+)"', src)
    if not m:
        raise SystemExit("zakup_data.js: не нашёл window.__ZG")
    return json.loads(gzip.decompress(base64.b64decode(m.group(1))).decode("utf-8"))


def build(D):
    W = [w["k"] for w in D["weeks"]]
    LAB = {w["k"]: w["label"] for w in D["weeks"]}
    po_w = D["prihodOplata"]["weeks"]
    tv_w = D["tovary"]["weeks"]
    tv_m = D["tovary"]["months"]
    debt = {r["name"]: r.get("debt", 0) for r in D.get("kz", {}).get("rows", [])}

    # ── закупки по позициям и неделям
    per = {}
    sup_of = {}
    for k in W:
        for r in tv_w.get(k, {}).get("rows", []):
            p = r["product"]
            per.setdefault(p, {})
            per[p][k] = per[p].get(k, 0) + r["sum"]
            if r.get("supplier"):
                sup_of[p] = r["supplier"]

    def skew(k):
        """Сколько на неделе k взяли сверх обычного и сколько регулярных позиций пропустили."""
        i = W.index(k)
        hist = W[max(0, i - 8):i]
        if len(hist) < 4:
            return None
        sp_n = sp_s = gp_n = gp_s = 0
        for p, byw in per.items():
            nz = [byw.get(h, 0) for h in hist if byw.get(h, 0) > 0]
            if len(nz) < 3:
                continue
            med = statistics.median(nz)
            cur = byw.get(k, 0)
            if cur > med * 1.5 and cur - med > 150000:
                sp_n += 1; sp_s += cur - med
            if cur == 0 and len(nz) >= max(4, int(len(hist) * 0.7)):
                gp_n += 1; gp_s += med
        return sp_n, round(sp_s), gp_n, round(gp_s)

    weeks = []
    cum = 0
    for k in W:
        sup = po_w.get(k, {}).get("suppliers", [])
        p = sum(x["prihod"] for x in sup)
        o = sum(x["oplata"] for x in sup)
        cum += o - p
        sk = skew(k) or (None, None, None, None)
        weeks.append({"k": k, "label": LAB[k], "prihod": round(p), "oplata": round(o),
                      "delta": round(o - p), "cum": round(cum),
                      "spN": sk[0], "spS": sk[1], "gpN": sk[2], "gpS": sk[3]})

    # ── перекос по поставщикам
    agg = {}
    for k in W:
        for x in po_w.get(k, {}).get("suppliers", []):
            a = agg.setdefault(x["name"], [0, 0])
            a[0] += x["prihod"]; a[1] += x["oplata"]
    sup_rows = [{"name": n, "prihod": round(v[0]), "oplata": round(v[1]),
                 "delta": round(v[1] - v[0]), "debt": round(debt.get(n, 0))}
                for n, v in agg.items() if v[0] or v[1]]
    sup_rows.sort(key=lambda r: -abs(r["delta"]))

    # ── кому платим вперёд: оплата заметно больше поступлений, а долга нет
    advance = [r for r in sup_rows if r["delta"] > 300000 and r["debt"] <= r["delta"] * 0.3]
    advance.sort(key=lambda r: -r["delta"])

    # ── что заказано выше среднего за 6 месяцев
    mk = sorted(tv_m.keys())
    base_m, cur_m = mk[-7:-1], mk[-1]
    hist_m, last_m = {}, {}
    for m in base_m:
        for r in tv_m.get(m, {}).get("rows", []):
            hist_m.setdefault(r["product"], []).append(r["sum"])
    for r in tv_m.get(cur_m, {}).get("rows", []):
        last_m[r["product"]] = last_m.get(r["product"], 0) + r["sum"]
        if r.get("supplier"):
            sup_of.setdefault(r["product"], r["supplier"])
    over6 = []
    for p, cur in last_m.items():
        h = hist_m.get(p, [])
        if len(h) < 3:
            continue
        avg = sum(h) / len(base_m)          # среднее по 6 месяцам, а не по месяцам с закупкой
        if cur > avg * 1.3 and cur - avg > 400000:
            over6.append({"n": p, "cur": round(cur), "avg": round(avg),
                          "x": round(cur / avg, 2) if avg else 0,
                          "extra": round(cur - avg), "sup": sup_of.get(p, "")})
    over6.sort(key=lambda r: -r["extra"])

    # ── последняя полная неделя: всплески и пропуски
    lastw = W[-2] if len(W) >= 2 else W[-1]
    i = W.index(lastw); hist = W[max(0, i - 8):i]
    spikes, gaps = [], []
    stock = {it["name"]: it for it in D.get("sklad_syrye", {}).get("items", [])}
    for p, byw in per.items():
        nz = [byw.get(h, 0) for h in hist if byw.get(h, 0) > 0]
        if len(nz) < 3:
            continue
        med = statistics.median(nz); cur = byw.get(lastw, 0)
        if cur > med * 1.5 and cur - med > 150000:
            spikes.append({"n": p, "cur": round(cur), "med": round(med),
                           "x": round(cur / med, 2) if med else 0,
                           "extra": round(cur - med), "sup": sup_of.get(p, "")})
        if cur == 0 and len(nz) >= max(4, int(len(hist) * 0.7)):
            st = stock.get(p, {})
            gaps.append({"n": p, "med": round(med), "wk": len(nz),
                         "stock": round(st.get("sum", 0)), "sup": sup_of.get(p, "")})
    spikes.sort(key=lambda r: -r["extra"])
    gaps.sort(key=lambda r: -r["med"])

    # ── замороженные остатки: хватит больше чем на 3 недели
    qper = {}
    for k in W[-9:-1]:
        for r in tv_w.get(k, {}).get("rows", []):
            qper[r["product"]] = qper.get(r["product"], 0) + r.get("qty", 0)
    frozen = []
    for name, it in stock.items():
        aq = qper.get(name, 0) / 8.0
        if aq <= 0 or it.get("sum", 0) < 150000:
            continue
        cov = it.get("qty", 0) / aq
        if cov >= 3:
            frozen.append({"n": name, "qty": round(it.get("qty", 0), 1),
                           "sum": round(it.get("sum", 0)), "cov": round(cov, 1),
                           "aq": round(aq, 1)})
    frozen.sort(key=lambda r: -r["sum"])

    return {"updated": almaty.now().strftime("%d.%m.%Y %H:%M"),
            "through": D.get("through", ""),
            "lastWeek": LAB.get(lastw, ""), "curMonth": cur_m,
            "baseMonths": [base_m[0], base_m[-1]] if base_m else [],
            "weeks": weeks, "sup": sup_rows[:40], "advance": advance[:20],
            "over6": over6[:25], "spikes": spikes[:25], "gaps": gaps[:25],
            "frozen": frozen[:25]}


if __name__ == "__main__":
    data = build(load_zakup())
    out = os.path.join(HERE, "kz_ana.js")
    open(out, "w", encoding="utf-8").write(
        "window.KZ_ANA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")
    print("kz_ana.js: недель %d, поставщиков %d, авансов %d, выше 6-мес среднего %d, "
          "всплесков %d, пропусков %d, замороженных %d"
          % (len(data["weeks"]), len(data["sup"]), len(data["advance"]), len(data["over6"]),
             len(data["spikes"]), len(data["gaps"]), len(data["frozen"])))
