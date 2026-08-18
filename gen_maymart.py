# -*- coding: utf-8 -*-
"""Аналитика возвратов МАЙМАРТ с полной себестоимостью по ОПиУ.

Считает экономику сети «Маймарт» (группа контрагентов «90-…») по слоям затрат
из управленческого ОПиУ и встраивает скрытую секцию в продажи_2026.html.

Источники:
  • returns_meta.js  — отгрузка/возвраты по контрагентам, точкам и SKU (из iiko, обновляется в CI);
  • PL_RATIOS        — структура затрат из ОПиУ 2026 (янв–май, факт), доли от выручки;
  • FOODCOST         — продуктовая себестоимость по SKU из «анализ себестоимости» (янв–май 2026).

Обновлять PL_RATIOS и FOODCOST при закрытии новых месяцев (месяц закрыт к 18-му числу).
Запускается в CI после rebuild_sales.py.
"""
import json, os, re, datetime

HERE = os.path.dirname(os.path.abspath(__file__))

PL_RATIOS = {
"2026-01": {
"food": 0.5004,
"prod": 0.06879,
"fot": 0.26064,
"ar": 0.03105,
"com": 0.04601,
"adm": 0.17631
},
"2026-02": {
"food": 0.51888,
"prod": 0.06725,
"fot": 0.27792,
"ar": 0.03217,
"com": 0.04779,
"adm": 0.17916
},
"2026-03": {
"food": 0.50547,
"prod": 0.0651,
"fot": 0.25429,
"ar": 0.03114,
"com": 0.07399,
"adm": 0.16299
},
"2026-04": {
"food": 0.4968,
"prod": 0.06002,
"fot": 0.26593,
"ar": 0.03022,
"com": 0.05435,
"adm": 0.15641
},
"2026-05": {
"food": 0.49077,
"prod": 0.06899,
"fot": 0.22907,
"ar": 0.02891,
"com": 0.04993,
"adm": 0.15151
}
}
PL_AVG = {"food": 0.50246, "prod": 0.06603, "fot": 0.25757, "ar": 0.0307, "com": 0.05441, "adm": 0.16528}
FOODCOST = {"Упак Плов по-ташкентски (1порц)": 0.5011, "Упак Удон с говядиной (1порц)": 0.4262, "Упак Кимпаб с тунцом (1шт)": 0.4933, "Упак Лагман по-домашнему (1порц)": 0.4087, "Упак Манты с говядиной (1порц)": 0.5797, "Упак Бифштекс с яйцом и картофелем (1порц)": 0.4868, "Упак Плов с курицей (1порц)": 0.3337, "Упак Бефстроганов с картофельным пюре (1порц)": 0.4342, "Упак Зразы куриные с сырным соусом и фузилли (1порц)": 0.4292, "Упак Кимпаб с курицей (1шт)": 0.5424, "Упак Гуйру цомян (1порц)": 0.4697, "Упак Котлета домашняя с рисом и овощами (1порц)": 0.5182, "Упак Куриные котлеты с картофельным пюре и овощами (1порц)": 0.447, "Упак Пенне болоньезе (1порц)": 0.4808, "Упак Шницель куриный с гречкой (1порц)": 0.436, "Упак Тефтели говяжьи с гречкой и овощами (1порц)": 0.4151, "Упак Блины с мясом (3шт)": 0.5297, "Упак Шницель куриный с картофельным пюре (1порц)": 0.4397, "Упак Пельмени с говядиной (1 порц)": 0.5785, "Упак Курица с сыром и гречкой (1порц)": 0.4154, "Упак Салат Гнездо глухаря (1порц)": 0.5056, "Упак Паста с курицей и грибами (1порц)": 0.4806, "Упак Блины с творогом (3шт)": 0.3483, "Упак Курица с сыром и картофельным пюре (1порц)": 0.4375, "Упак Салат Цезарь с курицей (1порц)": 0.5131, "Упак Круассан с курицей (1шт)": 0.3869, "Упак Блины с курицей (3шт)": 0.3937, "Упак Онигири с лососем (1шт)": 0.4328, "Упак Онигири с тунцом (1шт)": 0.2931, "Упак Салат Мимоза (1порц)": 0.4267, "Упак Вареники с картофелем (1порц)": 0.302, "Упак Запеканка картофельная с курицей (по-французски) (1порц)": 0.49, "Упак Курица с сыром с пастой фузилли (1порц)": 0.4407, "Упак Курица с сыром с рисом и паутини (1порц)": 0.4344, "Упак Салат Оливье (1порц)": 0.5087, "Упак Клаб Сэндвич с индейкой (1шт)": 0.4553, "Упак Пельмени с курицей (1 порц)": 0.4149, "Упак Круассан с индейкой (1шт)": 0.3998, "Упак Сэндвич с колбасой (1шт)": 0.4589, "Упак Ролл-салат с курицей (1шт)": 0.5909, "Упак Багет с индейкой (1шт)": 0.4017, "Упак Сельдь под шубой (1порц)": 0.4066, "Упак Онигири с курицей (1шт)": 0.3483, "Упак Клаб Сэндвич с говядиной (1шт)": 0.4408, "Упак Салат Малибу (1порц)": 0.5213, "Упак Блины с ветчиной и сыром (3шт)": 0.4351, "Упак Клаб Сэндвич с курицей (1шт)": 0.4473, "Упак Макароны по-флотски (1порц)": 0.5359, "Упак Солянка (1порц)": 0.5343, "Упак Клаб Сэндвич крок-месье (1шт)": 0.4323, "Упак Морс Черная смородина 0,5 (1шт)": 0.4959, "Упак Компот из сухофруктов 0,5 (1шт)": 0.3246, "Упак Жареная говядина с картофелем и овощами (1порц)": 0.4708, "Упак Казон кабоб с овощами (1порц)": 0.4494, "Упак Курица карри с картофельным пюре (1порц)": 0.4738, "Упак Курица карри с турецким рисом (1порц)": 0.5162, "Упак Спагетти с курицей в грибном соусе (1порц)": 0.5094, "Упак Куриная грудка с овощным рататуем (1порц)": 0.512, "Упак Спагетти с курицей в соусе том ям (1порц)": 0.472, "Упак Хот дог (1шт)": 0.6811, "Упак Жареные сосиски с пюре и капустой (1порц)": 0.4426, "Упак Суп борщ с говядиной (1порц)": 0.4626, "Упак Суп говяжий с фрикадельками (1порц)": 0.3632, "ЛЛ* Упак Круассан с курицей (1шт)": 0.3869, "Упак Самса с курицей сырая ФЗ СМ (30 шт гофра)": 0.3439, "ЛЛ* Упак Круассан с лососем (1шт)": 0.3816, "Упак Суп лапша с курицей (1порц)": 0.4296, "ЛЛ* Упак Плов по-ташкентски (1порц)": 0.5011, "Упак Чиабатта с говядиной и омлетом (1шт)": 0.4135, "ЛЛ* Упак Ролл-салат с лососем (1шт)": 0.6498, "Упак Клаб Сэндвич с говядиной замор (24шт гофра)": 0.348, "Упак Сосиска в тесте  готов СМ (30шт гофра)": 0.4119, "ЛЛ* Упак Сэндвич с колбасой (1шт)": 0.4589, "Упак Круассан с лососем (1шт)": 0.3816, "Упак Эклер крем-брюле (6 упак гофра)": 0.4552, "ЛЛ* Упак Гуйру цомян (1порц)": 0.4697, "Упак Самса с курицей готов ФЗ СМ (30шт гофра )": 0.3592, "Упак Самса с говядиной сырая ФЗ СМ (30 шт гофра)": 0.482, "RP* Упак Булка с яблоком готов СМ (15 шт гофра)": 0.28, "Упак Клаб Сэндвич с курицей замор (24 шт гофра)": 0.3968, "RP* Упак Брецель-дог (20шт)": 0.5658, "RP* Упак Маффин шоколадный (24шт)": 0.5066, "ЛЛ* Упак Бризоль с рисом (1порц)": 0.6263, "ЛЛ* Упак Шницель куриный с картофельным пюре (1порц)": 0.4397, "ЛЛ* Упак Багет с индейкой (1шт)": 0.4017, "ЛЛ* Упак Хот дог (1шт)": 0.6811, "RP* Упак Сосиска в тесте  готов СМ (30шт гофра)": 0.4233, "ЛЛ* Упак Блины с ветчиной и сыром (3шт)": 0.4351, "ЛЛ* Упак Чиабатта с говядиной и омлетом (1шт)": 0.4135, "ЛЛ* Упак Шницель куриный с гречкой (1порц)": 0.436, "Б* Самса с курицей ФЗ (1шт)": 0.8584, "ЛЛ* Упак Блины с мясом (3шт)": 0.5297, "ЛЛ* Упак Клаб Сэндвич с курицей (1шт)": 0.4473, "ЛЛ* Упак Бифштекс с яйцом и картофелем (1порц)": 0.4868, "ЛЛ* Упак Кимпаб с тунцом (1шт)": 0.4933, "Упак Маффин с черной смородиной (24шт)": 0.5515, "ЛЛ* Упак Курица с сыром с пастой фузилли (1порц)": 0.4407, "ЛЛ* Упак Ролл-салат с курицей (1шт)": 0.5909, "ЛЛ* Упак Онигири с тунцом (1шт)": 0.2931, "ЛЛ* Упак Тучикены с картофельным пюре (1порц)": 0.571, "Упак Бризоль с рисом (1порц)": 0.6263, "RP* Упак Пирожок с капустой  готов СМ (30 шт гофра)": 0.3329, "RP* Упак Пирожок с картофелем готов СМ (30 шт гофра)": 0.432, "ЛЛ* Упак Пенне болоньезе (1порц)": 0.4808, "ЛЛ* Упак Онигири с лососем (1шт)": 0.4328, "RP* Упак Улитка с изюмом готов СМ (10 шт гофра)": 0.326, "ЛЛ* Упак Блины с яблоком (3шт)": 0.3675, "Упак Ролл-салат с лососем (1шт)": 0.6498, "ЛЛ* Упак Котлета пожарская с картофельным пюре (1порц)": 0.5163, "ЛЛ* Упак Кимпаб с курицей (1шт)": 0.5424, "Упак Котлеты куриные с картофельным пюре и капустой (1порц)": 0.5429, "ЛЛ* Упак Паста с курицей и грибами (1порц)": 0.4806, "Упак Сосиска в тесте СМ (8шт)": 0.3447, "RP* Упак Блины с ветчиной и сыром (3шт)": 0.5071, "Упак Эклер крем-брюле (5шт)": 0.4173, "Упак Салат с хрустящей курочкой (1порц)": 0.3442, "Упак Салат фунчоза с овощами (1порц)": 0.4074, "RP* Упак Плов по-ташкентски (1порц)": 0.5498, "RP* Упак Куриные котлеты с картофельным пюре и овощами (1порц)": 0.5159, "RP* Упак Багет с курицей под гриль (1шт)": 0.4956, "АР* Упак Бефстроганов с картофельным пюре (1порц)": 0.5367, "ЛЛ* Упак Вареники с картофелем (1порц)": 0.302, "RP* Упак Блины с творогом (3шт)": 0.4073, "ЛЛ* Упак Клаб Сэндвич с говядиной (1шт)": 0.4408, "Упак Красный бархат в стакане с вилкой (1шт)": 0.4692, "АР* Упак Шницель куриный с гречкой (1порц)": 0.4713, "АР* Упак Салат Цезарь с курицей (1порц)": 0.5301, "ЛЛ* Упак Манты с говядиной (1порц)": 0.5797, "ЛЛ* Упак Блины с творогом (3шт)": 0.3483, "Упак Сникерс в стакане с вилкой (1шт)": 0.4113, "RP* Упак Манты с говядиной (1порц)": 0.6143, "RP* Упак Булка с маком готов СМ (15 шт гофра)": 0.295, "Упак Медовик в стакане с вилкой (1шт)": 0.4629}
PL_ABS = {"2026-01": {"rev": 237310863, "op": -19742583}, "2026-02": {"rev": 226011522, "op": -27838396}, "2026-03": {"rev": 258037214, "op": -23989908}, "2026-04": {"rev": 262061486, "op": -16702850}, "2026-05": {"rev": 260781489, "op": -5002942}}
FOODCOST_DEFAULT = 0.456

GROUP_RE = re.compile(r'^\s*90\s*[-–]')
MS = ["", "Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
MN = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]


def load_returns():
    p = os.path.join(HERE, "returns_meta.js")
    txt = open(p, encoding="utf-8").read()
    return json.loads(txt.split("=", 1)[1].rstrip().rstrip(";"))


def ratio_for(month):
    return PL_RATIOS.get(month, PL_AVG)


def cost_layers(g, n, rt):
    """g — отгрузка (произведённый объём), n — нетто-выручка.
    Производство, аренда и доставка ложатся на весь произведённый объём,
    администрация распределяется по выручке."""
    return {
        "food": g * rt["food"],
        "prod": g * rt["prod"],
        "fot":  g * rt["fot"],
        "ar":   g * rt["ar"],
        "com":  g * rt["com"],
        "adm":  n * rt["adm"],
    }



def effective_ratios():
    """Доли затрат: факт из xlsx (эталон) + свежие месяцы из iiko (opiu_full.json),
    но только если сверка с эталоном прошла."""
    eff = dict(PL_RATIOS)
    ab = dict(PL_ABS)
    src = {m: "ОПиУ" for m in PL_RATIOS}
    p = os.path.join(HERE, "opiu_full.json")
    if os.path.exists(p):
        try:
            d = json.load(open(p, encoding="utf-8"))
            if d.get("check", {}).get("ok"):
                base = {k: sum(PL_RATIOS[x][k] for x in PL_RATIOS) / len(PL_RATIOS)
                        for k in ("food", "prod", "fot", "ar", "com", "adm")}
                for m, v in sorted(d.get("months", {}).items()):
                    if m in eff or not v.get("rev"):
                        continue
                    gaps = v.get("gaps") or []
                    if not v.get("ok", True) and not gaps:
                        continue                      # месяц брак по другой причине — пропускаем
                    r = dict(v["ratios"])
                    if gaps:
                        # начисления по этим статьям ещё не проведены — подставляем среднюю долю
                        for k in gaps:
                            r[k] = base[k]
                    eff[m] = r
                    rev = v["rev"]
                    ab[m] = {"rev": rev, "op": round(rev - rev * sum(r.values()))}
                    src[m] = "iiko" if not gaps else "iiko+оценка"
                print("доли затрат: xlsx %d мес. + iiko %d мес."
                      % (len(PL_RATIOS), len(eff) - len(PL_RATIOS)))
            else:
                print("[!] opiu_full.json не прошёл сверку — беру только xlsx")
        except Exception as e:
            print("[!] opiu_full.json не прочитан:", e)
    return eff, ab, src


def build():
    global PL_RATIOS, PL_AVG, PL_ABS
    PL_RATIOS, PL_ABS, PL_SRC = effective_ratios()
    PL_AVG = {k: sum(PL_RATIOS[m][k] for m in PL_RATIOS) / len(PL_RATIOS)
              for k in ("food", "prod", "fot", "ar", "com", "adm")}
    R = load_returns()
    months = sorted(R.get("by_month", {}).keys())
    pts = [c for c in R.get("contractors", []) if GROUP_RE.match(str(c.get("n", "")))]

    # ── помесячно ────────────────────────────────────────────────
    rows = []
    for m in months:
        g = sum((c.get("m", {}).get(m) or [0, 0])[1] for c in pts)
        r = sum((c.get("m", {}).get(m) or [0, 0])[0] for c in pts)
        if g <= 0:
            continue
        n = g - r
        rt = ratio_for(m)
        cl = cost_layers(g, n, rt)
        full = sum(cl.values())
        rows.append({
            "k": m, "lbl": MS[int(m.split("-")[1])], "g": round(g), "r": round(r), "n": round(n),
            "pct": round(r / g * 100, 1), "cost": {k: round(v) for k, v in cl.items()},
            "full": round(full), "margin": round(n - full),
            "est": "оценк" in PL_SRC.get(m, ""),
            "src": PL_SRC.get(m, "ОПиУ"),
        })

    G = sum(x["g"] for x in rows); RR = sum(x["r"] for x in rows); N = G - RR
    CL = {k: sum(x["cost"][k] for x in rows) for k in ("food", "prod", "fot", "ar", "com", "adm")}
    FULL = sum(CL.values())

    # ── пороги безубыточности (на средних долях) ─────────────────
    a = PL_AVG
    k_prod = a["food"] + a["prod"] + a["fot"] + a["ar"]          # производственная себестоимость
    k_deliv = k_prod + a["com"]                                   # + доставка и реализация
    be = {
        "food":  round((1 - a["food"]) * 100, 1),
        "prod":  round((1 - k_prod) * 100, 1),
        "deliv": round((1 - k_deliv) * 100, 1),
        "full":  round((1 - k_deliv / (1 - a["adm"])) * 100, 1),
    }

    # ── точки ────────────────────────────────────────────────────
    plist = []
    for c in pts:
        g, r = c.get("g", 0), c.get("r", 0)
        if g <= 0:
            continue
        n = g - r
        cl = cost_layers(g, n, a)
        full = sum(cl.values())
        plist.append({
            "n": re.sub(r'^\s*90\s*[-–]\s*', '', str(c["n"])).strip(),
            "g": round(g), "r": round(r), "n_": round(n),
            "pct": round(r / g * 100, 1), "margin": round(n - full),
            "mpct": round((n - full) / g * 100, 1),
        })
    plist.sort(key=lambda x: x["margin"])

    # ── SKU ──────────────────────────────────────────────────────
    conv = a["prod"] + a["fot"] + a["ar"] + a["com"]
    slist = []
    for p in R.get("products", []):
        r = p.get("r", 0)
        if r <= 0:
            continue
        fc = FOODCOST.get(p["n"], FOODCOST_DEFAULT)
        slist.append({
            "n": p["n"], "r": round(r), "g": round(p.get("g", 0)),
            "pct": p.get("s"), "q": p.get("q"), "fc": round(fc * 100, 1),
            "loss": round(r * (fc + conv)),
        })
    slist.sort(key=lambda x: -x["loss"])

    share_ret = round(RR / (R.get("total") or RR or 1) * 100, 1)

    return {
        "updated": (json.loads(open(os.path.join(HERE, "sales_meta.js"), encoding="utf-8")
                    .read().split("=", 1)[1].rstrip().rstrip(";")).get("pulled")
                    if os.path.exists(os.path.join(HERE, "sales_meta.js")) else ""),
        "months": rows, "totals": {
            "g": round(G), "r": round(RR), "n": round(N), "pct": round(RR / G * 100, 1) if G else 0,
            "cost": {k: round(v) for k, v in CL.items()}, "full": round(FULL),
            "margin": round(N - FULL), "mpct": round((N - FULL) / N * 100, 1) if N else 0,
            "cost_per_rev": round(FULL / N, 3) if N else 0,
            "ret_cost": round(RR * k_deliv), "share_of_all_returns": share_ret,
            "points": len(plist), "skus": len(slist),
        },
        "ratios": {k: round(v * 100, 1) for k, v in a.items()},
        "ratios_by_month": {m: {k: round(v * 100, 1) for k, v in PL_RATIOS[m].items()} for m in PL_RATIOS},
        "pl_abs": PL_ABS,
        "pl_fact": {
            "rev": sum(v["rev"] for v in PL_ABS.values()),
            "op": sum(v["op"] for v in PL_ABS.values()),
            "pct": round(sum(v["op"] for v in PL_ABS.values()) / sum(v["rev"] for v in PL_ABS.values()) * 100, 2),
            "full": round((sum(v["rev"] for v in PL_ABS.values()) - sum(v["op"] for v in PL_ABS.values()))
                          / sum(v["rev"] for v in PL_ABS.values()) * 100, 2),
        },
        "be": be, "points": plist, "skus": slist,
        "company": {"full": round(sum(a.values()) * 100, 1), "op": round((1 - sum(a.values())) * 100, 1)},
        "pl_months": sorted(PL_RATIOS.keys()),
        "pl_src": PL_SRC,
    }


SECTION = r'''
<div class="section" id="maymart-analytics" style="padding-top:6px" data-rv="9">
  <details id="mm-details" class="opiu-check" style="background:#1e293b;border:1px solid #334155;border-radius:14px;padding:0;overflow:hidden">
    <summary style="cursor:pointer;list-style:none;padding:14px 18px;font-size:14px;font-weight:700;color:#f1f5f9;display:flex;align-items:center;gap:8px;user-select:none;flex-wrap:wrap">
      <span style="color:#c9a94e"><span id="mm-caret">&#9656;</span> &#127978; Аналитика возвратов МАЙМАРТ</span>
      <span id="mm-sum" style="font-weight:600;font-size:12px;color:#e2896b"></span>
      <span style="font-weight:500;font-size:12px;color:#94a3b8;margin-left:auto">полная себестоимость по ОПиУ &middot; нажмите, чтобы раскрыть</span>
    </summary>
    <div style="padding:4px 14px 18px">
      <div class="card" style="margin:8px 0 12px;background:linear-gradient(160deg,#111c2e,#0f172a)">
        <div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;margin-bottom:2px">
          <div style="font-size:14px;font-weight:800;color:#f1f5f9">&#129518; Как из ОПиУ получается полная себестоимость</div>
          <div id="mm-scheme-sel" style="margin-left:auto;display:inline-flex;background:#0f172a;border:1px solid #334155;border-radius:9px;padding:2px"></div>
        </div>
        <div style="font-size:11.5px;color:#94a3b8;margin-bottom:12px">Каждый тенге выручки проходит шесть ступеней затрат. Нажмите на любую — покажу, что в неё входит, сколько это в деньгах и что с этим делать.</div>
        <div id="mm-scheme"></div>
        <div id="mm-scheme-detail" style="margin-top:12px"></div>
      </div>
      <div id="mm-verdict" style="margin:8px 0 12px"></div>
      <div class="card" style="margin:0 0 14px">
        <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:2px">&#127919; При каких показателях продавать в Маймарт выгодно</div>
        <div style="font-size:11.5px;color:#94a3b8;margin-bottom:10px">Две ручки, которыми можно управлять: доля возвратов и цена отгрузки. В таблице — результат канала за период при разных сочетаниях, объём тот же.</div>
        <div id="mm-cond"></div>
        <div id="mm-matrix" style="overflow-x:auto;margin-top:10px"></div>
        <div id="obs-cond" style="margin-top:10px"></div>
      </div>
      <div id="mm-kpi" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px"></div>

      <div class="card" style="margin-top:14px">
        <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:2px">&#128200; Когда канал выгоден, а когда нет</div>
        <div style="font-size:11.5px;color:#94a3b8;margin-bottom:10px">Столбик — сколько процентов отгрузки вернулось. Золотая линия — порог: пока возвраты ниже неё, месяц окупает производство и доставку. Синяя линия — результат месяца в деньгах.</div>
        <div id="mm-strip" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px"></div>
        <div style="height:320px"><canvas id="mm-ch-months"></canvas></div>
        <div id="mm-notes" style="margin-top:10px"></div>
        <div id="mm-verdict-months" style="margin-top:10px"></div>
        <div id="obs-months" style="margin-top:10px"></div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin-top:12px">
        <div class="card">
          <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:8px">&#129517; От отгрузки до маржи <span style="font-weight:500;font-size:11px;color:#64748b">— куда уходят деньги, с начала года</span></div>
          <div style="height:320px"><canvas id="mm-ch-fall"></canvas></div>
          <div id="obs-fall" style="margin-top:10px"></div>
        </div>
        <div class="card">
          <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:8px">&#129518; Порог безубыточности по возвратам</div>
          <div id="mm-be"></div>
        </div>
      </div>

      <div class="card" style="margin-top:12px">
        <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:8px">&#128202; Полная себестоимость Маймарта, с начала года</div>
        <div id="mm-pl" style="overflow-x:auto"></div>
      </div>

      <div class="card" style="margin-top:12px">
        <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px">
          <div style="font-size:13px;font-weight:700;color:#f1f5f9">&#127970; Точки сети</div>
          <span id="mm-pt-count" style="font-size:11.5px;color:#64748b"></span>
          <select id="mm-pt-sort" style="margin-left:auto;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer">
            <option value="margin">сортировка: по убытку</option>
            <option value="pct">по % возврата</option>
            <option value="g">по отгрузке</option>
          </select>
          <input id="mm-pt-q" type="text" placeholder="Поиск точки…" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:8px;padding:6px 10px;font-size:12px;min-width:150px">
        </div>
        <div id="mm-points" style="overflow-x:auto"></div>
      </div>

      <div class="card" style="margin-top:12px">
        <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px">
          <div style="font-size:13px;font-weight:700;color:#f1f5f9">&#128230; Товары — что возвращают</div>
          <span id="mm-sk-count" style="font-size:11.5px;color:#64748b"></span>
          <select id="mm-sk-sort" style="margin-left:auto;background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer">
            <option value="loss">сортировка: по потерям</option>
            <option value="pct">по % возврата</option>
            <option value="fc">по фудкосту</option>
          </select>
          <input id="mm-sk-q" type="text" placeholder="Поиск товара…" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:8px;padding:6px 10px;font-size:12px;min-width:150px">
        </div>
        <div id="mm-skus" style="overflow-x:auto"></div>
      </div>

      <details style="margin-top:12px;background:#0f172a;border:1px solid #334155;border-radius:12px;padding:10px 14px">
        <summary style="cursor:pointer;font-size:12.5px;font-weight:700;color:#c9a94e">&#10067; Как это посчитано</summary>
        <div id="mm-method" style="font-size:12px;color:#94a3b8;line-height:1.7;padding-top:8px"></div>
      </details>
    </div>
  </details>
  <script>window.MAYMART = __MMDATA__;</script>
  <script>
  (function(){
    var D = window.MAYMART; if(!D) return;
    var MS=["","Янв","Фев","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек"];
    var MN=["","январь","февраль","март","апрель","май","июнь","июль","август","сентябрь","октябрь","ноябрь","декабрь"];
    function fmt(v){ var a=Math.abs(Math.round(v)); var s=a>=1e6?(a/1e6).toFixed(1).replace(".",",")+" млн":(a>=1e3?Math.round(a/1e3)+" тыс":String(a)); return (v<0?"−":"")+s; }
    function pc(v){ var x=Math.round(v*10)/10; return (x<0?"−":"")+String(Math.abs(x)).replace(".",",")+"%"; }
    function esc(s){ return String(s).replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];}); }
    var T=D.totals, R=D.ratios, BE=D.be;
    var LAYERS=[["food","Продуктовая себестоимость","#ef4444"],["prod","Производственные накладные","#f97316"],["fot","ФОТ производства","#eab308"],["ar","Аренда и коммуналка","#a3e635"],["com","Доставка и реализация","#22d3ee"],["adm","Администрация (АУП)","#a78bfa"]];

    function kpi(){
      var neg = T.margin<0;
      var cards=[
        ["Отгружено", fmt(T.g), "с начала года", "#e2e8f0"],
        ["Возвраты", "−"+fmt(T.r), pc(T.pct)+" от отгрузки · "+pc(T.share_of_all_returns)+" всех возвратов завода", "#e2896b"],
        ["Выручка нетто", fmt(T.n), "то, что реально оплачено", "#22c55e"],
        ["Полная себестоимость", fmt(T.full), String(Math.round(T.cost_per_rev*100))+"₸ затрат на 100₸ выручки", "#f59e0b"],
        [neg?"Убыток":"Прибыль", fmt(T.margin), pc(T.mpct)+" к выручке · по заводу "+pc(D.company.op), neg?"#ef4444":"#22c55e"],
        ["Цена возвратов", "−"+fmt(T.ret_cost), "произвели и привезли то, что вернулось", "#e2896b"]
      ];
      document.getElementById("mm-kpi").innerHTML = cards.map(function(c){
        return '<div class="card" style="padding:12px 14px"><div style="font-size:11px;color:#94a3b8;font-weight:600;letter-spacing:.03em;text-transform:uppercase">'+c[0]+'</div>'
          +'<div style="font-size:22px;font-weight:800;color:'+c[3]+';margin:4px 0 2px">'+c[1]+'</div>'
          +'<div style="font-size:11px;color:#64748b;line-height:1.4">'+c[2]+'</div></div>';
      }).join("");
    }

    function verdict(){
      var neg=T.margin<0;
      var txt = neg
        ? "<b>Продавать в Маймарт в текущем виде убыточно.</b> С начала года сеть забрала "+fmt(T.r)+" возвратами — это "+pc(T.pct)+" от всей отгрузки и "+pc(T.share_of_all_returns)+" всех возвратов завода. После распределения полной себестоимости по ОПиУ канал даёт "+fmt(T.margin)+" убытка. Чтобы выйти в ноль по производству и доставке, возвраты должны быть не выше "+pc(BE.deliv)+", сейчас — "+pc(T.pct)+"."
        : "<b>Канал прибыльный.</b> Возвраты "+pc(T.pct)+" при пороге "+pc(BE.deliv)+", маржа "+fmt(T.margin)+".";
      document.getElementById("mm-verdict").innerHTML =
        '<div style="background:'+(neg?"rgba(239,68,68,.12)":"rgba(34,197,94,.12)")+';border:1px solid '+(neg?"rgba(239,68,68,.35)":"rgba(34,197,94,.35)")+';border-radius:12px;padding:12px 14px;font-size:13px;color:#e2e8f0;line-height:1.65">'+txt+'</div>';
    }

    var SCHEME=[
      {k:"food", t:"Продукты и сырьё", c:"#ef4444",
       what:"Себестоимость продуктовая и фритюрное масло — всё, что физически ушло в блюдо.",
       why:"Самая крупная статья. Управляется закупочными ценами, рецептурой и потерями на производстве.",
       act:"Пересмотр цен поставщиков, работа с фудкостом по позициям, контроль отклонений факта от калькуляции."},
      {k:"prod", t:"Производственные накладные", c:"#f97316",
       what:"Расходные материалы, электроэнергия, мусор, ремонты цеха, спецодежда, а также потери: недостача, порча, брак, бракераж и возвраты дистрибьюторам.",
       why:"Здесь сидят все потери. Формально это себестоимость, но большая часть — управляемые утечки.",
       act:"Инвентаризации, контроль сроков, разбор причин брака. Сокращение этой статьи почти полностью падает в прибыль."},
      {k:"fot", t:"ФОТ производства", c:"#eab308",
       what:"Зарплата цеха, налоги с неё, питание персонала, аренда квартир для сотрудников производства.",
       why:"Вторая по величине статья и почти постоянная: при падении объёма она не уменьшается и сразу съедает маржу.",
       act:"Выработка на человека, графики под фактический объём, пересмотр численности при снижении заказов."},
      {k:"ar", t:"Аренда и коммуналка", c:"#84cc16",
       what:"Аренда производственных площадей и коммунальные услуги по ним.",
       why:"Полностью постоянная статья: не зависит ни от объёма, ни от ассортимента.",
       act:"Пересмотр договора, субаренда неиспользуемых площадей, уплотнение производства."},
      {k:"com", t:"Реализация и логистика", c:"#22d3ee",
       what:"Доставка и логистика, маркетинг, продвижение товара, проработка новых блюд.",
       why:"Полупеременная: растёт с объёмом отгрузки, но маркетинг решается отдельно.",
       act:"Оптимизация маршрутов и частоты доставки, оценка отдачи от маркетинга по каналам."},
      {k:"adm", t:"Администрация (АУП)", c:"#a78bfa",
       what:"Зарплата и налоги АУП, административные расходы, НДС, банк, охрана, IT, связь, вознаграждения.",
       why:"Постоянная статья, не зависящая от продаж. Именно она делает полную себестоимость больше 100% при падении выручки.",
       act:"Это база для решения о масштабе: либо наращивать выручку под нынешний АУП, либо сокращать сам АУП."}
    ];
    var schemeMonth="avg";

    function schemeRatios(){
      if(schemeMonth==="avg") return {r:R, label:"среднее за "+D.pl_months.length+" мес.", rev:null};
      var rr=D.ratios_by_month[schemeMonth]||R;
      var ab=(D.pl_abs||{})[schemeMonth]||null;
      return {r:rr, label:MN[+schemeMonth.slice(5)]+" "+schemeMonth.slice(0,4), rev:ab?ab.rev:null};
    }

    function scheme(){
      var sel=document.getElementById("mm-scheme-sel");
      if(sel){
        var opts=[["avg","среднее"]].concat(D.pl_months.map(function(m){ return [m, MS[+m.slice(5)]]; }));
        sel.innerHTML=opts.map(function(o){ var on=o[0]===schemeMonth;
          return '<button type="button" data-m="'+o[0]+'" style="border:0;background:'+(on?"#c9a94e":"transparent")+';color:'+(on?"#111827":"#cbd5e1")+';font-size:11.5px;font-weight:700;padding:5px 10px;border-radius:7px;cursor:pointer">'+o[1]+'</button>';
        }).join("");
        sel.onclick=function(e){ var b=e.target.closest("button"); if(!b) return; schemeMonth=b.getAttribute("data-m"); scheme(); };
      }
      var S=schemeRatios(), rr=S.r;
      var total=SCHEME.reduce(function(a,x){ return a+(rr[x.k]||0); },0);
      var revTxt=S.rev?(" · выручка "+fmt(S.rev)):"";
      var left=100, steps=[];
      SCHEME.forEach(function(x){ var val=rr[x.k]||0; steps.push({x:x, val:val, from:left, to:left-val}); left-=val; });
      var W=function(p){ return Math.max(0,Math.min(100,p)); };

      var h='<div style="font-size:11.5px;color:#64748b;margin-bottom:8px">'+S.label+revTxt+' · каждая полоса — доля от выручки</div>';
      // шкала 100%
      h+='<div style="position:relative;height:26px;border-radius:8px;overflow:hidden;background:#0b1220;border:1px solid #1f2937;display:flex;margin-bottom:6px">';
      SCHEME.forEach(function(x){ var val=rr[x.k]||0;
        h+='<div data-step="'+x.k+'" title="'+x.t+'" style="width:'+W(val/Math.max(total,100)*100)+'%;background:'+x.c+';cursor:pointer;opacity:.9"></div>';
      });
      if(total<100) h+='<div style="flex:1;background:rgba(34,197,94,.35)"></div>';
      h+='</div>';
      h+='<div style="display:flex;justify-content:space-between;font-size:10.5px;color:#64748b;margin-bottom:14px"><span>0%</span><span>'
        +(total>100?('затраты '+pc(total)+' — выходим за 100% выручки'):('затраты '+pc(total)+', остаётся '+pc(100-total)))+'</span><span>'+pc(Math.max(total,100))+'</span></div>';

      // лесенка
      h+='<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px">';
      h+='<div style="background:#0b1220;border:1px solid #1f2937;border-radius:12px;padding:10px 12px">'
        +'<div style="font-size:10.5px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.04em">Выручка</div>'
        +'<div style="font-size:20px;font-weight:800;color:#e2e8f0;margin:3px 0">100%</div>'
        +'<div style="font-size:10.5px;color:#64748b">'+(S.rev?fmt(S.rev):"база расчёта")+'</div></div>';
      steps.forEach(function(st){
        var val=st.val, x=st.x;
        h+='<div data-step="'+x.k+'" style="background:#0b1220;border:1px solid #1f2937;border-left:4px solid '+x.c+';border-radius:12px;padding:10px 12px;cursor:pointer;transition:.15s" '
          +'onmouseover="this.style.background=\'#111c2e\'" onmouseout="this.style.background=\'#0b1220\'">'
          +'<div style="font-size:10.5px;color:#94a3b8;font-weight:700">'+x.t+'</div>'
          +'<div style="font-size:20px;font-weight:800;color:'+x.c+';margin:3px 0">−'+pc(val)+'</div>'
          +'<div style="font-size:10.5px;color:#64748b">осталось '+pc(st.to)+(S.rev?(" · "+fmt(S.rev*val/100)):"")+'</div></div>';
      });
      var fin=100-total;
      h+='<div style="background:'+(fin<0?"rgba(239,68,68,.12)":"rgba(34,197,94,.12)")+';border:1px solid '+(fin<0?"rgba(239,68,68,.4)":"rgba(34,197,94,.4)")+';border-radius:12px;padding:10px 12px">'
        +'<div style="font-size:10.5px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.04em">Результат</div>'
        +'<div style="font-size:20px;font-weight:800;color:'+(fin<0?"#ef4444":"#22c55e")+';margin:3px 0">'+pc(fin)+'</div>'
        +'<div style="font-size:10.5px;color:#64748b">'+(fin<0?"убыток на каждом тенге":"прибыль на каждом тенге")+'</div></div>';
      h+='</div>';
      document.getElementById("mm-scheme").innerHTML=h;

      var host=document.getElementById("mm-scheme");
      host.onclick=function(e){ var t=e.target.closest("[data-step]"); if(t) schemeDetail(t.getAttribute("data-step")); };
      schemeDetail(window.__mmStep||"food");
    }

    function schemeDetail(key){
      window.__mmStep=key;
      var x=null; SCHEME.forEach(function(s){ if(s.k===key) x=s; });
      if(!x) return;
      var S=schemeRatios(), val=S.r[key]||0;
      var money=S.rev?fmt(S.rev*val/100):null;
      var mm=D.pl_months.map(function(m){ return {m:m, v:(D.ratios_by_month[m]||{})[key]||0}; });
      var mn=mm.slice().sort(function(a,b){return a.v-b.v;})[0], mx=mm.slice().sort(function(a,b){return b.v-a.v;})[0];
      var el=document.getElementById("mm-scheme-detail");
      el.innerHTML='<div style="background:#0b1220;border:1px solid #1f2937;border-left:4px solid '+x.c+';border-radius:14px;padding:14px 16px">'
        +'<div style="display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;margin-bottom:8px">'
        +'<div style="font-size:14px;font-weight:800;color:#f1f5f9">'+x.t+'</div>'
        +'<div style="font-size:14px;font-weight:800;color:'+x.c+'">'+pc(val)+' от выручки'+(money?(" · "+money):"")+'</div>'
        +'<div style="margin-left:auto;font-size:11px;color:#64748b">разброс по месяцам: '+pc(mn.v)+' ('+MS[+mn.m.slice(5)]+') … '+pc(mx.v)+' ('+MS[+mx.m.slice(5)]+')</div></div>'
        +'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;font-size:12.5px;line-height:1.7;color:#cbd5e1">'
        +'<div><b style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:.04em">Что входит</b><br>'+x.what+'</div>'
        +'<div><b style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:.04em">Почему важно</b><br>'+x.why+'</div>'
        +'<div><b style="color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:.04em">Что с этим делать</b><br>'+x.act+'</div></div>'
        +'<div style="margin-top:10px;padding-top:10px;border-top:1px solid #1b2636;font-size:12px;color:#94a3b8">'
        +'В расчёте Маймарта эта статья ложится на '+((key==="adm")?"нетто-выручку":"всю отгрузку")+': '
        +fmt((key==="adm"?T.n:T.g)*val/100)+' за период — это '+pc((key==="adm"?T.n:T.g)*val/100/Math.abs(T.full)*100)+' всей полной себестоимости канала.</div></div>';
    }

    function conditions(){
      var kDeliv=(R.food+R.prod+R.fot+R.ar+R.com)/100;   // производство + доставка, доля от выручки при нынешней цене
      var adm=R.adm/100;
      var need=kDeliv/(1-adm);                            // требуемое произведение цена × (1 − возвраты)
      var G=T.g;
      function margin(p,r){ return G*p*(1-r)*(1-adm) - G*kDeliv; }
      function needPrice(r){ return need/(1-r); }         // во сколько раз поднять цену при данном уровне возвратов
      function needRet(p){ return 1 - need/p; }           // какая доля возвратов допустима при данной цене

      var rNow=T.pct/100;
      var pNow=needPrice(rNow);
      var el=document.getElementById("mm-cond"); if(!el) return;
      var rows=[
        ["Порог по производству и доставке", "возвраты не выше "+pc(BE.deliv), "сейчас "+pc(T.pct), T.pct<=BE.deliv],
        ["Полная окупаемость при нынешней цене", "недостижима", "даже при нулевых возвратах не хватает "+pc((need-1)*100)+" цены", false],
        ["Полная окупаемость при нынешних возвратах", "цена выше на "+pc((pNow-1)*100), "при возвратах "+pc(T.pct), false],
        ["Реалистичное сочетание", "возвраты "+pc(10)+" и цена выше на "+pc((needPrice(0.10)-1)*100), "результат выйдет в ноль", true],
        ["Мягкий вариант", "возвраты "+pc(15)+" и цена выше на "+pc((needPrice(0.15)-1)*100), "результат выйдет в ноль", true]
      ];
      el.innerHTML='<table style="width:100%;border-collapse:collapse;font-size:12.5px;min-width:520px">'
        +rows.map(function(r){
          return '<tr style="border-bottom:1px solid #1b2636">'
            +'<td style="padding:7px 4px;color:#cbd5e1">'+r[0]+'</td>'
            +'<td style="padding:7px 4px;text-align:right;font-weight:800;color:'+(r[3]?"#22c55e":"#f59e0b")+';white-space:nowrap">'+r[1]+'</td>'
            +'<td style="padding:7px 4px;text-align:right;color:#64748b;font-size:11.5px">'+r[2]+'</td></tr>';
        }).join("")+'</table>';

      var RS=[T.pct/100,0.20,0.15,0.10,0.05,0], PS=[1,1.05,1.10,1.15,1.20];
      var h='<table style="width:100%;border-collapse:collapse;font-size:12px;min-width:560px">'
        +'<tr><th style="text-align:left;padding:6px 5px;color:#64748b;font-size:10.5px;text-transform:uppercase;letter-spacing:.04em">Цена \\ возвраты</th>'
        +RS.map(function(r,i){ return '<th style="padding:6px 5px;text-align:right;color:'+(i===0?"#e2896b":"#64748b")+';font-size:11px;font-weight:800">'
            +pc(r*100)+(i===0?" сейчас":"")+'</th>'; }).join("")+'</tr>';
      PS.forEach(function(p){
        h+='<tr style="border-top:1px solid #1b2636"><td style="padding:6px 5px;color:#cbd5e1;font-weight:700;white-space:nowrap">'
          +(p===1?"как сейчас":"+"+Math.round((p-1)*100)+"%")+'</td>';
        RS.forEach(function(r){
          var m=margin(p,r), ok=m>=0;
          var bg=ok?"rgba(34,197,94,"+Math.min(.4,.12+m/1e8)+")":"rgba(239,68,68,"+Math.min(.35,.1+Math.abs(m)/1.4e8)+")";
          h+='<td style="padding:7px 5px;text-align:right;font-weight:800;white-space:nowrap;background:'+bg+';color:'+(ok?"#4ade80":"#fca5a5")+'">'
            +(m>=0?"+":"")+fmt(m)+'</td>';
        });
        h+='</tr>';
      });
      h+='</table><div style="font-size:11.5px;color:#64748b;margin-top:8px">Зелёная клетка — канал в плюсе за '+D.months.length
        +' мес. при том же объёме отгрузки. Красная — в минусе. Цена считается как изменение отпускной цены на весь ассортимент Маймарта.</div>';
      document.getElementById("mm-matrix").innerHTML=h;
    }

    var TONE={bad:["#ef4444","rgba(239,68,68,.10)"],warn:["#f59e0b","rgba(245,158,11,.10)"],
              good:["#22c55e","rgba(34,197,94,.10)"],info:["#38bdf8","rgba(56,189,248,.08)"],
              tip:["#c9a94e","rgba(201,169,78,.10)"]};
    var ICONS={};
    function obsBlock(id, title, items){
      var el=document.getElementById(id); if(!el) return;
      var meta=ICONS[id]||[];
      var rows=items.map(function(t,i){
        var m=meta[i]||["\u2022","info"], tone=TONE[m[1]]||TONE.info;
        return '<div style="display:flex;gap:10px;align-items:flex-start;background:'+tone[1]+';border-left:3px solid '+tone[0]
          +';border-radius:9px;padding:8px 11px;margin-bottom:6px">'
          +'<div style="font-size:16px;line-height:1.3;flex:0 0 auto">'+m[0]+'</div>'
          +'<div style="font-size:12.5px;line-height:1.7;color:#cbd5e1"><b style="color:'+tone[0]+'">'+(i+1)+'.</b> '+t+'</div></div>';
      }).join("");
      el.innerHTML='<details style="background:#0f172a;border:1px solid #1f2937;border-radius:12px;padding:10px 14px">'
        +'<summary style="cursor:pointer;font-size:12.5px;font-weight:800;color:#c9a94e;list-style:none">&#128161; '+title
        +' <span style="color:#64748b;font-weight:600">— '+items.length+' наблюдений, нажмите</span></summary>'
        +'<div style="margin-top:10px">'+rows+'</div></details>';
    }
    ICONS["obs-months"]=[["\uD83D\uDCCA","info"],["\uD83D\uDD34","bad"],["\u26A0\uFE0F","bad"],["\uD83E\uDD47","warn"],
      ["\uD83D\uDCC9","good"],["\uD83C\uDFAF","tip"],["\uD83D\uDCB8","warn"],["\u2195\uFE0F","info"],["\uD83E\uDDFE","bad"],["\u2728","good"]];
    ICONS["obs-fall"]=[["\uD83D\uDE9A","info"],["\uD83E\uDD69","bad"],["\uD83D\uDC77","warn"],["\uD83C\uDFED","info"],["\uD83D\uDEF5","info"],
      ["\uD83C\uDFE2","info"],["\uD83D\uDCC9","bad"],["\uD83D\uDCAF","bad"],["\u267B\uFE0F","warn"],["\uD83D\uDD0D","tip"]];
    ICONS["obs-cond"]=[["\uD83D\uDCD0","tip"],["\uD83D\uDEAB","bad"],["\uD83D\uDCC9","good"],["\uD83D\uDCC9","good"],["\uD83D\uDCB5","warn"],
      ["\uD83D\uDFE9","good"],["\uD83E\uDD1D","tip"],["\uD83E\uDD1D","tip"],["\u26A0\uFE0F","warn"],["\uD83E\uDDED","tip"]];
    function b_(t){ return '<b style="color:#f1f5f9">'+t+'</b>'; }

    function obsMonths(){
      var M=D.months, n=M.length;
      var over=M.filter(function(m){return m.pct>BE.deliv;});
      var best=M.slice().sort(function(a,b){return a.pct-b.pct;})[0];
      var worst=M.slice().sort(function(a,b){return b.pct-a.pct;})[0];
      var first=M.slice(0,3), last=M.slice(-3);
      var avgF=first.reduce(function(s,m){return s+m.pct;},0)/first.length;
      var avgL=last.reduce(function(s,m){return s+m.pct;},0)/last.length;
      var totalG=M.reduce(function(s,m){return s+m.g;},0);
      var perPP=totalG*0.01*(R.food+R.prod+R.fot+R.ar+R.com)/100;
      var ifBest=M.reduce(function(s,m){ return s+(m.g*(1-best.pct/100)*(1-R.adm/100)-m.g*(R.food+R.prod+R.fot+R.ar+R.com)/100); },0);
      var need=(T.pct-BE.deliv);
      obsBlock("obs-months","Что видно на графике возвратов",[
        "Средний уровень возвратов за период — "+b_(pc(T.pct))+" при пороге "+b_(pc(BE.deliv))+". Канал живёт втрое выше того уровня, который он способен вынести.",
        "Выше порога "+b_(over.length+" месяцев из "+n)+" — то есть провал не разовый, а системный: это норма работы канала, а не случайность.",
        "Худший месяц — "+b_(worst.lbl+": "+pc(worst.pct))+", убыток "+fmt(Math.abs(worst.margin))+". Один такой месяц стоит примерно как "+(Math.abs(worst.margin)/Math.max(1,Math.abs(best.margin))).toFixed(1).replace(".",",")+" лучших.",
        "Лучший месяц — "+b_(best.lbl+": "+pc(best.pct))+", и даже он "+(best.pct>BE.deliv?("выше порога на "+(best.pct-BE.deliv).toFixed(1).replace(".",",")+" пункта"):"уже в зелёной зоне")+".",
        "Первые три месяца дали в среднем "+pc(avgF)+", последние три — "+b_(pc(avgL))+": динамика "+(avgL<avgF?("улучшается, минус "+(avgF-avgL).toFixed(1).replace(".",",")+" пункта"):("ухудшается, плюс "+(avgL-avgF).toFixed(1).replace(".",",")+" пункта"))+".",
        "Чтобы попасть в зелёную зону, нужно снять "+b_((need).toFixed(1).replace(".",",")+" пункта возвратов")+" — в деньгах это примерно "+b_(fmt(totalG*need/100))+" товара за период, который сейчас едет обратно.",
        "Каждый процентный пункт возвратов стоит около "+b_(fmt(perPP))+" за период: столько завод тратит на производство и доставку того, что вернётся.",
        "Разброс между лучшим и худшим месяцем — "+b_((worst.pct-best.pct).toFixed(1).replace(".",",")+" пункта")+". Такая амплитуда означает, что уровень возвратов управляем: значит, дело в заказе и ротации, а не в природе товара.",
        "Суммарный убыток канала за "+n+" мес. — "+b_(fmt(T.margin))+", в среднем "+fmt(T.margin/n)+" в месяц.",
        "Если бы все месяцы были как лучший, результат составил бы "+b_(fmt(ifBest))+" вместо "+fmt(T.margin)+" — разница "+fmt(ifBest-T.margin)+" только за счёт дисциплины по возвратам."
      ]);
    }

    function obsFall(){
      var L=[["food","Продукты"],["prod","Производственные накладные"],["fot","ФОТ производства"],["ar","Аренда"],["com","Доставка"],["adm","Администрация"]];
      var costs=L.map(function(x){ return {k:x[0],t:x[1],v:T.cost[x[0]]}; }).sort(function(a,b){return b.v-a.v;});
      var prodPart=T.cost.food+T.cost.prod+T.cost.fot+T.cost.ar;
      obsBlock("obs-fall","Что видно на разложении от отгрузки до маржи",[
        "Отгрузка за период — "+b_(fmt(T.g))+", но до выручки доходит только "+b_(fmt(T.n))+": "+pc(T.pct)+" уезжает обратно ещё до первого рубля затрат.",
        "Самая тяжёлая ступень — "+b_(costs[0].t+": "+fmt(costs[0].v))+", это "+pc(costs[0].v/T.full*100)+" всей полной себестоимости канала.",
        "Вторая по весу — "+b_(costs[1].t+": "+fmt(costs[1].v))+"; вместе с первой они дают "+pc((costs[0].v+costs[1].v)/T.full*100)+" затрат.",
        "Производственный блок целиком (продукты, накладные, ФОТ, аренда) — "+b_(fmt(prodPart))+", это "+pc(prodPart/T.g*100)+" от отгрузки.",
        "Доставка и реализация — "+fmt(T.cost.com)+"; в пересчёте на один возвращённый тенге товара это "+fmt(T.cost.com*T.r/T.g)+" впустую.",
        "Администрация "+fmt(T.cost.adm)+" считается от нетто-выручки, а не от отгрузки — иначе канал выглядел бы ещё хуже на "+fmt(T.cost.adm*T.r/T.n)+".",
        "Полная себестоимость "+b_(fmt(T.full))+" против нетто-выручки "+fmt(T.n)+": разрыв "+b_(fmt(Math.abs(T.margin)))+".",
        "На каждые 100 ₸ выручки канал тратит "+b_(Math.round(T.cost_per_rev*100)+" ₸")+" против "+Math.round(D.company.full)+" ₸ по заводу в среднем.",
        "Стоимость самих возвратов — "+b_(fmt(T.ret_cost))+": это уже произведённый и доставленный товар, который пришлось списать.",
        "Если убрать только потери на возвратах, канал всё ещё не выйдет в плюс — не хватит "+b_(fmt(Math.abs(T.margin)-T.ret_cost))+", и это уже вопрос цены, а не логистики."
      ]);
    }

    function obsCond(){
      var kDeliv=(R.food+R.prod+R.fot+R.ar+R.com)/100, adm=R.adm/100, need=kDeliv/(1-adm), G=T.g;
      function margin(p,r){ return G*p*(1-r)*(1-adm) - G*kDeliv; }
      function needPrice(r){ return need/(1-r); }
      obsBlock("obs-cond","Как читать таблицу выгодности",[
        "Условие выгодности одно: "+b_("цена × (1 − доля возвратов) ≥ "+pc(need*100))+". Всё остальное — следствия из него.",
        "При нынешней цене канал не выходит в плюс ни при каких возвратах: даже при нуле не хватает "+b_(pc((need-1)*100))+".",
        "Снижение возвратов с "+pc(T.pct)+" до "+pc(15)+" улучшает результат на "+b_(fmt(margin(1,0.15)-margin(1,T.pct/100)))+" без единого изменения цены.",
        "Снижение до "+pc(10)+" даёт "+b_(fmt(margin(1,0.10)-margin(1,T.pct/100)))+", до "+pc(5)+" — "+b_(fmt(margin(1,0.05)-margin(1,T.pct/100)))+".",
        "Повышение цены на 5% при нынешних возвратах приносит "+b_(fmt(margin(1.05,T.pct/100)-margin(1,T.pct/100)))+" — заметно меньше, чем работа с возвратами.",
        "Первая зелёная клетка появляется при "+b_("цене +10% и возвратах 0%")+" либо "+b_("+15% и 5%")+" — это ориентир для переговоров с сетью.",
        "Реалистичная связка "+b_("возвраты 10% и цена +"+pc((needPrice(0.10)-1)*100))+" выводит канал ровно в ноль.",
        "Мягкая связка "+b_("возвраты 15% и цена +"+pc((needPrice(0.15)-1)*100))+" — тоже ноль, но требует большего роста цены.",
        "Матрица считает при неизменном объёме: если рост цены уменьшит отгрузку, зелёные клетки сместятся вправо — это стоит проверять на переговорах.",
        "Порядок действий по деньгам: сначала возвраты (дешевле всего), потом цена, и только затем — сокращение ассортимента под Маймарт."
      ]);
    }

    function chMonths(){
      var strip=document.getElementById("mm-strip");
      if(strip){
        strip.innerHTML=D.months.map(function(m){
          var ok=m.pct<=BE.deliv;
          return '<div style="flex:1;min-width:96px;background:'+(ok?"rgba(34,197,94,.14)":"rgba(239,68,68,.13)")
            +';border:1px solid '+(ok?"rgba(34,197,94,.45)":"rgba(239,68,68,.4)")+';border-radius:12px;padding:7px 9px;text-align:center">'
            +'<div style="font-size:11px;color:#94a3b8;font-weight:700">'+m.lbl
            +(m.est?' <span title="часть затрат ещё не проведена — доли взяты средние" style="background:rgba(167,139,250,.18);border:1px solid rgba(167,139,250,.5);color:#c4b5fd;border-radius:6px;padding:1px 5px;font-size:9px">оценка</span>':"")
            +'</div>'
            +'<div style="font-size:16px;font-weight:800;color:'+(ok?"#22c55e":"#ef4444")+';line-height:1.25">'+pc(m.pct)+'</div>'
            +'<div style="font-size:10.5px;color:#94a3b8">'+(m.margin<0?"убыток ":"прибыль ")+fmt(Math.abs(m.margin))+'</div></div>';
        }).join("");
      }
      var vm=document.getElementById("mm-verdict-months");
      if(vm){
        var good=D.months.filter(function(m){ return m.pct<=BE.deliv; });
        var best=D.months.slice().sort(function(a,b){ return a.pct-b.pct; })[0];
        var worst=D.months.slice().sort(function(a,b){ return b.pct-a.pct; })[0];
        vm.innerHTML='<div style="display:flex;gap:10px;flex-wrap:wrap;font-size:12px;color:#cbd5e1">'
          +'<span style="background:rgba(34,197,94,.14);border:1px solid rgba(34,197,94,.4);border-radius:9px;padding:6px 11px">'
          +'<b style="color:#22c55e">Ниже '+pc(BE.deliv)+'</b> — месяц в плюсе по производству и доставке</span>'
          +'<span style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.38);border-radius:9px;padding:6px 11px">'
          +'<b style="color:#ef4444">Выше '+pc(BE.deliv)+'</b> — каждый отгруженный тенге приносит убыток</span>'
          +'<span style="color:#94a3b8;padding:6px 0">Прибыльных месяцев: <b style="color:'+(good.length?"#22c55e":"#ef4444")+'">'
          +good.length+' из '+D.months.length+'</b> · лучший '+best.lbl+' ('+pc(best.pct)+'), худший '+worst.lbl+' ('+pc(worst.pct)+')</span></div>';
      }
      var cv=document.getElementById("mm-ch-months"); if(!cv||!window.Chart) return;
      try{var ex=Chart.getChart?Chart.getChart(cv):null; if(ex) ex.destroy();}catch(e){}
      var L=D.months.map(function(m){return m.lbl;});
      var worstI=0, bestI=0;
      D.months.forEach(function(m,i){ if(m.pct>D.months[worstI].pct) worstI=i; if(m.pct<D.months[bestI].pct) bestI=i; });
      var estI=-1; D.months.forEach(function(m,i){ if(m.est&&estI<0) estI=i; });
      var NOTES=[
        {i:worstI, num:"\u2460", tone:"#ef4444", txt:"Пик возвратов: "+D.months[worstI].lbl+" — "+pc(D.months[worstI].pct)+", убыток "+fmt(Math.abs(D.months[worstI].margin))},
        {i:bestI, num:"\u2461", tone:"#22c55e", txt:"Лучший месяц: "+D.months[bestI].lbl+" — "+pc(D.months[bestI].pct)+", но всё ещё выше порога"},
        {i:D.months.length-1, num:"\u2462", tone:"#c9a94e", txt:"Порог "+pc(BE.deliv)+": ниже этой линии месяц окупает производство и доставку"},
        {i:Math.max(0,D.months.length-3), num:"\u2463", tone:"#38bdf8", txt:"Последние три месяца: средний возврат "+pc(D.months.slice(-3).reduce(function(s2,m){return s2+m.pct;},0)/Math.min(3,D.months.length))}
      ];
      if(estI>=0) NOTES.push({i:estI, num:"\u2464", tone:"#a78bfa", txt:D.months[estI].lbl+": часть затрат ещё не проведена в учёте, доли взяты средние"});
      var noteEl=document.getElementById("mm-notes");
      if(noteEl) noteEl.innerHTML='<div style="display:flex;flex-wrap:wrap;gap:8px">'+NOTES.map(function(n){
        return '<div style="display:flex;gap:7px;align-items:center;background:#0f172a;border:1px solid #1f2937;border-left:3px solid '
          +n.tone+';border-radius:9px;padding:6px 10px;font-size:11.5px;color:#cbd5e1">'
          +'<span style="color:'+n.tone+';font-size:15px;font-weight:800">'+n.num+'</span>'+n.txt+'</div>';
      }).join("")+'</div>';
      var notePlugin={id:"mmnotes",afterDatasetsDraw:function(ch){
        var c=ch.ctx, bars=ch.getDatasetMeta(0), line=ch.getDatasetMeta(1), used={};
        c.save();
        NOTES.forEach(function(n){
          var el=(n.num==="\u2462")?(line.data[n.i]):(bars.data[n.i]);
          if(!el) return;
          var x=el.x, y=(n.num==="\u2462")?el.y:(el.y-26);
          if(n.num==="\u2463"){ y=ch.chartArea.top+14; }
          var slot=Math.round(x)+"_"+Math.round(y/24);
          while(used[slot]){ y-=24; slot=Math.round(x)+"_"+Math.round(y/24); }
          used[slot]=1;
          c.beginPath(); c.arc(x, y, 10, 0, Math.PI*2);
          c.fillStyle=n.tone; c.globalAlpha=.95; c.fill(); c.globalAlpha=1;
          c.fillStyle="#0b1220"; c.font="800 11px system-ui,-apple-system,sans-serif";
          c.textAlign="center"; c.textBaseline="middle";
          c.fillText(n.num, x, y+.5);
        });
        c.restore();
      }};
      var labelPlugin={id:"mmlab",afterDatasetsDraw:function(ch){
        var c=ch.ctx, ds=ch.getDatasetMeta(0);
        c.save(); c.font="800 11px system-ui,-apple-system,sans-serif"; c.textAlign="center";
        ds.data.forEach(function(el,i){
          var m=D.months[i], ok=m.pct<=BE.deliv;
          c.fillStyle=ok?"#22c55e":"#f87171";
          c.fillText(pc(m.pct), el.x, el.y-7);
        });
        var ms=ch.getDatasetMeta(2);
        c.font="700 10.5px system-ui,-apple-system,sans-serif"; c.fillStyle="#93c5fd";
        ms.data.forEach(function(el,i){
          var low = el.y > ch.chartArea.bottom-34;      // точка у самой оси — подпись сверху
          c.fillText(fmt(D.months[i].margin), el.x, low ? el.y-11 : el.y+16);
        });
        c.restore();
      }};
      var cx=cv.getContext("2d");
      function grad(c1,c2){ var g=cx.createLinearGradient(0,0,0,320); g.addColorStop(0,c1); g.addColorStop(1,c2); return g; }
      var gBad=grad("rgba(248,113,113,.95)","rgba(239,68,68,.35)"), gOk=grad("rgba(74,222,128,.95)","rgba(34,197,94,.32)");
      new Chart(cx,{data:{labels:L,datasets:[
        {type:"bar",label:"Возвраты, % от отгрузки",yAxisID:"y",order:3,borderRadius:8,borderSkipped:false,
         data:D.months.map(function(m){return m.pct;}),
         hoverBackgroundColor:D.months.map(function(m){return m.pct<=BE.deliv?"rgba(74,222,128,1)":"rgba(248,113,113,1)";}),
         backgroundColor:D.months.map(function(m){return m.pct<=BE.deliv?gOk:gBad;})},
        {type:"line",label:"Порог безубыточности "+pc(BE.deliv),yAxisID:"y",order:1,
         data:D.months.map(function(){return BE.deliv;}),
         borderColor:"#e3c46a",borderWidth:3,borderDash:[8,5],pointRadius:0,
         fill:{target:"origin",above:"rgba(34,197,94,.14)"}},
        {type:"line",label:"Результат месяца, ₸",yAxisID:"y1",order:2,
         data:D.months.map(function(m){return +(m.margin/1e6).toFixed(2);}),
         borderColor:"#60a5fa",backgroundColor:"#60a5fa",borderWidth:2,tension:.3,pointRadius:4,
         pointBackgroundColor:D.months.map(function(m){return m.margin<0?"#ef4444":"#22c55e";})}
      ]},options:{responsive:true,maintainAspectRatio:false,layout:{padding:{top:18}},
        interaction:{mode:"index",intersect:false},
        plugins:{legend:{labels:{color:"#cbd5e1",font:{size:11},boxWidth:12,usePointStyle:true}},datalabels:{display:false},
          tooltip:{callbacks:{label:function(c){
            var m=D.months[c.dataIndex];
            if(c.datasetIndex===0) return " возвраты "+pc(m.pct)+" при пороге "+pc(BE.deliv)+(m.pct>BE.deliv?" — выше нормы":" — в норме");
            if(c.datasetIndex===1) return " порог: столько возвратов канал выдерживает";
            return " результат "+fmt(m.margin)+" · отгрузка "+fmt(m.g)+", вернулось "+fmt(m.r);
          }}}},
        scales:{x:{ticks:{color:"#cbd5e1",font:{size:12,weight:"700"}},grid:{display:false}},
          y:{position:"left",beginAtZero:true,suggestedMax:40,title:{display:true,text:"возвраты, %",color:"#64748b",font:{size:10}},
             ticks:{color:"#94a3b8",font:{size:10},callback:function(v){return v+"%";}},grid:{color:"rgba(51,65,85,.35)"}},
          y1:{position:"right",title:{display:true,text:"результат, млн ₸",color:"#64748b",font:{size:10}},
              ticks:{color:"#60a5fa",font:{size:10},callback:function(v){return v+" М";}},grid:{display:false}}}},
        plugins:[labelPlugin,notePlugin]});
    }

    function chFall(){
      var cv=document.getElementById("mm-ch-fall"); if(!cv||!window.Chart) return;
      try{var ex=Chart.getChart?Chart.getChart(cv):null; if(ex) ex.destroy();}catch(e){}
      var steps=[["Отгрузка",T.g,"#c9a94e",true],["Возвраты",-T.r,"#e2896b",false]];
      LAYERS.forEach(function(l){ steps.push([l[1],-T.cost[l[0]],l[2],false]); });
      var labels=[],data=[],colors=[],cur=0;
      steps.forEach(function(s){
        if(s[3]){ labels.push(s[0]); data.push([0,s[1]/1e6]); colors.push(s[2]); cur=s[1]; }
        else { var nx=cur+s[1]; labels.push(s[0]); data.push([cur/1e6,nx/1e6]); colors.push(s[2]); cur=nx; }
      });
      labels.push(T.margin<0?"Убыток":"Прибыль"); data.push([0,cur/1e6]); colors.push(cur<0?"#ef4444":"#22c55e");
      new Chart(cv.getContext("2d"),{type:"bar",data:{labels:labels,datasets:[{data:data,backgroundColor:colors,borderRadius:4,barPercentage:.72}]},
        options:{indexAxis:"y",responsive:true,maintainAspectRatio:false,
          plugins:{legend:{display:false},datalabels:{display:false},
            tooltip:{callbacks:{label:function(c){var v=c.raw;return " "+fmt((v[1]-v[0])*1e6);}}}},
          scales:{x:{ticks:{color:"#64748b",font:{size:10},callback:function(v){return v+" М";}},grid:{color:"rgba(51,65,85,.4)"}},
            y:{ticks:{color:"#cbd5e1",font:{size:11}},grid:{display:false}}}}});
    }

    function beBlock(){
      var items=[["Покрыть только продукты (сырьё)",BE.food],["Покрыть производство: сырьё, ФОТ, накладные, аренда",BE.prod],["Покрыть производство и доставку",BE.deliv],["Покрыть всё, включая администрацию",BE.full]];
      var html='<div style="font-size:12px;color:#94a3b8;line-height:1.6;margin-bottom:10px">Максимальный процент возвратов, при котором канал ещё не в минусе — по уровням затрат. Факт Маймарта — <b style="color:#e2896b">'+pc(T.pct)+'</b>.</div>';
      items.forEach(function(it){
        var lim=it[1], ok=lim>T.pct, imposs=lim<0;
        var w=Math.max(0,Math.min(100,(imposs?0:lim)/50*100)), wf=Math.max(0,Math.min(100,T.pct/50*100));
        html+='<div style="margin-bottom:12px">'
          +'<div style="display:flex;justify-content:space-between;gap:8px;font-size:12px;color:#cbd5e1;margin-bottom:4px"><span>'+it[0]+'</span>'
          +'<b style="color:'+(imposs?"#ef4444":(ok?"#22c55e":"#f59e0b"))+'">'+(imposs?"недостижимо":("до "+pc(lim)))+'</b></div>'
          +'<div style="position:relative;height:8px;background:#0f172a;border-radius:5px;overflow:hidden">'
          +'<div style="position:absolute;left:0;top:0;bottom:0;width:'+w.toFixed(1)+'%;background:'+(ok?"rgba(34,197,94,.55)":"rgba(245,158,11,.45)")+'"></div>'
          +'<div style="position:absolute;left:'+wf.toFixed(1)+'%;top:-2px;bottom:-2px;width:2px;background:#e2896b"></div></div></div>';
      });
      html+='<div style="font-size:11.5px;color:#64748b;line-height:1.6;margin-top:6px">Красная риска — фактический уровень возвратов. Шкала до 50%.</div>';
      document.getElementById("mm-be").innerHTML=html;
    }

    function plTable(){
      var rows=[["Отгрузка (произведено и отгружено)",T.g,"#e2e8f0",""],["Возвраты",-T.r,"#e2896b",pc(T.pct)+" от отгрузки"],["Выручка нетто",T.n,"#22c55e","база 100%"]];
      LAYERS.forEach(function(l){ rows.push([l[1],-T.cost[l[0]],"#cbd5e1",pc(R[l[0]])+" от выручки завода"]); });
      rows.push(["Полная себестоимость",-T.full,"#f59e0b",""]);
      rows.push([T.margin<0?"Убыток канала":"Прибыль канала",T.margin,T.margin<0?"#ef4444":"#22c55e",pc(T.mpct)+" к нетто-выручке"]);
      var html='<table style="width:100%;border-collapse:collapse;font-size:12.5px;min-width:520px">';
      rows.forEach(function(r,i){
        var strong=(i<3||i>=rows.length-2);
        html+='<tr style="border-bottom:1px solid #1b2636">'
          +'<td style="padding:7px 4px;color:'+(strong?"#f1f5f9":"#cbd5e1")+';font-weight:'+(strong?700:500)+'">'+r[0]+'</td>'
          +'<td style="padding:7px 4px;text-align:right;white-space:nowrap;color:'+r[2]+';font-weight:'+(strong?800:600)+'">'+fmt(r[1])+'</td>'
          +'<td style="padding:7px 4px;text-align:right;white-space:nowrap;color:#64748b;font-size:11.5px">'+(r[3]||"")+'</td></tr>';
      });
      document.getElementById("mm-pl").innerHTML=html+'</table>';
    }

    var pst={sort:"margin",q:"",all:false}, sst={sort:"loss",q:"",all:false};
    function renderPoints(){
      var a=D.points.slice();
      if(pst.q){var q=pst.q.toLowerCase(); a=a.filter(function(x){return x.n.toLowerCase().indexOf(q)>=0;});}
      if(pst.sort==="margin") a.sort(function(x,y){return x.margin-y.margin;});
      else if(pst.sort==="pct") a.sort(function(x,y){return y.pct-x.pct;});
      else a.sort(function(x,y){return y.g-x.g;});
      var shown=pst.all?a:a.slice(0,15);
      var html='<table style="width:100%;border-collapse:collapse;font-size:12.5px;min-width:560px">'
        +'<tr style="color:#64748b;font-size:11px;font-weight:700;text-align:right"><th style="text-align:left;padding:4px">Точка</th><th style="padding:4px">Отгрузка</th><th style="padding:4px">Возврат</th><th style="padding:4px">%</th><th style="padding:4px">Результат</th></tr>';
      shown.forEach(function(p){
        var bad=p.pct>BE.deliv;
        html+='<tr style="border-bottom:1px solid #1b2636">'
          +'<td style="padding:6px 4px;color:#cbd5e1;max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(p.n)+'</td>'
          +'<td style="padding:6px 4px;text-align:right;color:#94a3b8;white-space:nowrap">'+fmt(p.g)+'</td>'
          +'<td style="padding:6px 4px;text-align:right;color:#e2896b;white-space:nowrap">−'+fmt(p.r)+'</td>'
          +'<td style="padding:6px 4px;text-align:right;font-weight:700;color:'+(bad?"#ef4444":"#22c55e")+'">'+pc(p.pct)+'</td>'
          +'<td style="padding:6px 4px;text-align:right;font-weight:700;white-space:nowrap;color:'+(p.margin<0?"#ef4444":"#22c55e")+'">'+fmt(p.margin)+'</td></tr>';
      });
      html+='</table>';
      if(a.length>15) html+='<div data-mmall="p" style="text-align:center;padding:10px 0 2px;cursor:pointer;color:#c9a94e;font-size:12.5px;font-weight:600">'+(pst.all?"▴ Свернуть":("▾ Показать все ("+a.length+")"))+'</div>';
      document.getElementById("mm-points").innerHTML=html;
      document.getElementById("mm-pt-count").textContent="точек "+D.points.length+" · порог безубыточности "+pc(BE.deliv);
    }
    function renderSkus(){
      var a=D.skus.slice();
      if(sst.q){var q=sst.q.toLowerCase(); a=a.filter(function(x){return x.n.toLowerCase().indexOf(q)>=0;});}
      if(sst.sort==="loss") a.sort(function(x,y){return y.loss-x.loss;});
      else if(sst.sort==="pct") a.sort(function(x,y){return (y.pct||0)-(x.pct||0);});
      else a.sort(function(x,y){return y.fc-x.fc;});
      var shown=sst.all?a:a.slice(0,15);
      var html='<table style="width:100%;border-collapse:collapse;font-size:12.5px;min-width:600px">'
        +'<tr style="color:#64748b;font-size:11px;font-weight:700;text-align:right"><th style="text-align:left;padding:4px">Товар</th><th style="padding:4px">Возврат</th><th style="padding:4px">% возвр.</th><th style="padding:4px">Фудкост</th><th style="padding:4px">Потери</th></tr>';
      shown.forEach(function(s){
        html+='<tr style="border-bottom:1px solid #1b2636">'
          +'<td style="padding:6px 4px;color:#cbd5e1;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(s.n)+'</td>'
          +'<td style="padding:6px 4px;text-align:right;color:#e2896b;white-space:nowrap">−'+fmt(s.r)+'</td>'
          +'<td style="padding:6px 4px;text-align:right;font-weight:700;color:'+((s.pct||0)>BE.deliv?"#ef4444":"#22c55e")+'">'+(s.pct!=null?pc(s.pct):"—")+'</td>'
          +'<td style="padding:6px 4px;text-align:right;color:#94a3b8">'+pc(s.fc)+'</td>'
          +'<td style="padding:6px 4px;text-align:right;font-weight:700;color:#ef4444;white-space:nowrap">−'+fmt(s.loss)+'</td></tr>';
      });
      html+='</table>';
      if(a.length>15) html+='<div data-mmall="s" style="text-align:center;padding:10px 0 2px;cursor:pointer;color:#c9a94e;font-size:12.5px;font-weight:600">'+(sst.all?"▴ Свернуть":("▾ Показать все ("+a.length+")"))+'</div>';
      document.getElementById("mm-skus").innerHTML=html;
      document.getElementById("mm-sk-count").textContent="товаров "+D.skus.length+" · % возврата — по всем покупателям";
    }

    function method(){
      var A=D.ratios, M=D.ratios_by_month, ABS=D.pl_abs||{}, F=D.pl_fact||null;
      var ms=Object.keys(M).sort();
      var MNAME={"01":"январь","02":"февраль","03":"март","04":"апрель","05":"май","06":"июнь","07":"июль","08":"август"};
      function H(n,t){ return '<div style="display:flex;gap:10px;align-items:baseline;margin:26px 0 10px">'
        +'<span style="background:#c9a94e;color:#0f172a;font-weight:900;font-size:11px;border-radius:7px;padding:3px 9px;white-space:nowrap">ШАГ '+n+'</span>'
        +'<span style="font-size:15px;font-weight:800;color:#f1f5f9">'+t+'</span></div>'; }
      function P(t){ return '<p style="margin:0 0 10px;font-size:13px;line-height:1.78;color:#cbd5e1">'+t+'</p>'; }
      function b(t){ return '<b style="color:#f1f5f9">'+t+'</b>'; }
      function CALC(rows){
        return '<div style="background:#0b1220;border:1px solid #1e293b;border-radius:12px;padding:12px 14px;margin:6px 0 12px;'
          +'font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;line-height:1.95;color:#9fe8ff;overflow-x:auto">'
          +rows.map(function(r){
              if(r===null) return '<div style="height:8px"></div>';
              if(typeof r==="string") return '<div style="color:#64748b">'+r+'</div>';
              return '<div><span style="color:#cbd5e1">'+r[0]+'</span>'
                +'<span style="color:#c9a94e"> = </span><span style="color:#7dd3fc">'+r[1]+'</span>'
                +(r[2]?('<span style="color:#64748b"> · '+r[2]+'</span>'):'')+'</div>';
            }).join("")+'</div>';
      }
      function TBL(head,rows,foot){
        var h='<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px;min-width:560px;margin:4px 0 12px">'
          +'<tr style="color:#64748b;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.04em">'
          +head.map(function(x,i){ return '<th style="text-align:'+(i?"right":"left")+';padding:6px 5px">'+x+'</th>'; }).join("")+'</tr>';
        rows.forEach(function(r){
          h+='<tr style="border-top:1px solid #1b2636">'+r.map(function(x,i){
            return '<td style="padding:5px 5px;text-align:'+(i?"right":"left")+';color:'+(i?"#cbd5e1":"#e2e8f0")+';white-space:nowrap">'+x+'</td>';
          }).join("")+'</tr>';
        });
        if(foot) h+='<tr style="border-top:2px solid #334155">'+foot.map(function(x,i){
          return '<td style="padding:7px 5px;text-align:'+(i?"right":"left")+';color:#f1f5f9;font-weight:800;white-space:nowrap">'+x+'</td>';
        }).join("")+'</tr>';
        return h+'</table></div>';
      }
      var h="";

      h+=P("Ниже — весь расчёт по шагам, с формулами и подставленными числами. Любую цифру можно проверить руками.");

      h+=H(1,"Что считаем и зачем");
      h+=P("Вопрос простой: выгодно ли заводу продавать в Маймарт. Валовая прибыль на этот вопрос не отвечает — она учитывает только сырьё. "
        +"Товар ещё нужно произвести, упаковать, довезти, и всё это время работают цех, склад, аренда и администрация. "
        +"Поэтому берём "+b("полную себестоимость")+": все затраты завода из управленческого ОПиУ распределяем на товар и смотрим, что остаётся от канала.");

      h+=H(2,"Кто такой Маймарт в цифрах");
      h+=P("В iiko сеть заведена как отдельные контрагенты с номером 90 в начале названия — «90-Аль-Фараби 69 Б», «90-мкр-н Коктем-3, дом 17» и так далее. "
        +"Скрипт берёт всех, чьё имя начинается на «90-»: это "+b(T.points+" торговых точек")+". "
        +"По каждой из них известны отгрузка по расходным накладным и возвраты — те же данные, что и в общем блоке возвратов выше.");
      h+=CALC([
        ["Отгрузка (по накладным)", fmt(T.g)],
        ["Возвраты", "−"+fmt(T.r), pc(T.pct)+" от отгрузки"],
        ["Нетто-выручка", fmt(T.n), "отгрузка минус возвраты"],
        null,
        "для сравнения: возвраты всей компании за тот же период",
        ["Доля Маймарта во всех возвратах", pc(T.share_of_all_returns)]
      ]);

      h+=H(3,"Затраты завода из ОПиУ — считаем доли");
      h+=P("Берём управленческий ОПиУ за "+b(ms.length+" мес. 2026 года")+" (факт, закрытые месяцы) и каждую группу затрат делим на выручку того же месяца. "
        +"Получаем, сколько тиын из каждого тенге выручки съедает каждая статья.");
      h+=TBL(["Месяц","Выручка","Продукты","Произв. накл.","ФОТ пр-ва","Аренда","Реализация","АУП","Итого"],
        ms.map(function(m){
          var r=M[m], a=ABS[m]||{}, sum=r.food+r.prod+r.fot+r.ar+r.com+r.adm;
          return [MNAME[m.slice(5)], a.rev?fmt(a.rev):"—", pc(r.food), pc(r.prod), pc(r.fot), pc(r.ar), pc(r.com), pc(r.adm), pc(sum)];
        }),
        ["Среднее", F?fmt(F.rev/ms.length):"—", pc(A.food), pc(A.prod), pc(A.fot), pc(A.ar), pc(A.com), pc(A.adm), pc(D.company.full)]);
      h+=P("Что входит в каждую строку: "+b("продукты")+" — сырьё и фритюрное масло; "
        +b("производственные накладные")+" — расходные материалы, электроэнергия, мусор, брак, порча, недостача, ремонты цеха, возвраты дистрибьюторам; "
        +b("ФОТ производства")+" — зарплата цеха с налогами и питанием; "
        +b("аренда")+" — аренда и коммуналка производства; "
        +b("реализация")+" — логистика, доставка, маркетинг; "
        +b("АУП")+" — зарплата администрации, налоги, банк, охрана, связь и прочие административные расходы.");

      h+=H(4,"Откуда берётся −"+pc(Math.abs(D.company.op))+" по заводу");
      h+=P("Если сложить все доли, получится, сколько стоит завод в пересчёте на тенге выручки. Больше 100% — значит завод тратит больше, чем зарабатывает.");
      h+=CALC([
        ["Продукты", pc(A.food)],
        ["Производственные накладные", "+ "+pc(A.prod)],
        ["ФОТ производства", "+ "+pc(A.fot)],
        ["Аренда и коммуналка", "+ "+pc(A.ar)],
        ["Реализация и логистика", "+ "+pc(A.com)],
        ["Администрация", "+ "+pc(A.adm)],
        null,
        ["ПОЛНАЯ СЕБЕСТОИМОСТЬ", pc(D.company.full), "затрат на 100 ₸ выручки"],
        ["Операционная рентабельность", pc(D.company.op), "100% − "+pc(D.company.full)]
      ]);
      if(F){
        h+=P("Это среднее по месяцам. Если вместо среднего сложить сами суммы за "+ms.length+" мес., получится чуть строже:");
        h+=CALC([
          ["Выручка за период", fmt(F.rev)],
          ["Операционный результат", fmt(F.op)],
          ["Рентабельность", pc(F.pct), fmt(F.op)+" ÷ "+fmt(F.rev)],
          ["Полная себестоимость", pc(F.full)]
        ]);
        h+=P("Разница между "+b(pc(D.company.op))+" и "+b(pc(F.pct))+" — это разница между "+b("средним по месяцам")+" и "
          +b("суммой за период")+": в месяцах с большей выручкой убыток меньше, и невзвешенное среднее их сглаживает. "
          +"Для распределения затрат на канал берём среднее по месяцам — оно устойчивее к разовым всплескам вроде ремонта или маркетинговой акции в одном месяце. "
          +"Обе цифры говорят одно и то же: завод работает примерно на "+b("7 копеек убытка с каждого тенге")+".");
      }

      h+=H(5,"На что распределяем затраты — самое важное решение");
      h+=P("Здесь легко ошибиться. Если считать «в лоб» — от выручки, — то возврат как будто ничего не стоит: не продали, значит и затрат нет. Но это неправда. "
        +"Товар, который вернулся, "+b("уже произведён")+": сырьё списано, цех отработал, упаковка потрачена, машина съездила туда и обратно. Поэтому:");
      h+=CALC([
        "производство, аренда, доставка — считаются от ОТГРУЖЕННОГО объёма",
        ["база", fmt(T.g), "вся отгрузка, включая то, что вернулось"],
        null,
        "администрация — считается от НЕТТО-ВЫРУЧКИ",
        ["база", fmt(T.n), "АУП обслуживает бизнес в целом, привязываем к деньгам"]
      ]);

      h+=H(6,"Считаем Маймарт");
      h+=P("Подставляем доли из шага 3 в базы из шага 5:");
      h+=CALC([
        ["Продукты", fmt(T.g)+" × "+pc(A.food)+" = "+fmt(T.cost.food)],
        ["Производственные накладные", fmt(T.g)+" × "+pc(A.prod)+" = "+fmt(T.cost.prod)],
        ["ФОТ производства", fmt(T.g)+" × "+pc(A.fot)+" = "+fmt(T.cost.fot)],
        ["Аренда", fmt(T.g)+" × "+pc(A.ar)+" = "+fmt(T.cost.ar)],
        ["Доставка и реализация", fmt(T.g)+" × "+pc(A.com)+" = "+fmt(T.cost.com)],
        ["Администрация", fmt(T.n)+" × "+pc(A.adm)+" = "+fmt(T.cost.adm)],
        null,
        ["ПОЛНАЯ СЕБЕСТОИМОСТЬ КАНАЛА", fmt(T.full)],
        ["Нетто-выручка", fmt(T.n)],
        ["РЕЗУЛЬТАТ", fmt(T.margin), "нетто-выручка минус полная себестоимость"],
        ["Затрат на 100 ₸ выручки", Math.round(T.cost_per_rev*100)+" ₸", "по заводу "+Math.round(D.company.full)+" ₸"]
      ]);
      h+=P("Разница с заводом в среднем — "+b(Math.round(T.cost_per_rev*100-D.company.full)+" ₸ на каждые 100 ₸")+". "
        +"Вся она объясняется одним: "+b(pc(T.pct)+" отгрузки возвращается")+", и затраты на этот объём никуда не деваются.");

      h+=H(7,"Порог безубыточности: откуда 8,9%");
      h+=P("Спрашиваем наоборот: какую долю возвратов канал вообще может выдержать при нынешних ценах? "
        +"Обозначим долю возвратов через r. Тогда нетто-выручка = отгрузка × (1 − r), а производственные и логистические затраты = отгрузка × "
        +pc(A.food+A.prod+A.fot+A.ar+A.com)+" — они от r не зависят.");
      h+=CALC([
        "покрыть только сырьё:",
        ["1 − r ≥ "+pc(A.food), "r ≤ "+pc(BE.food)],
        null,
        "покрыть производство целиком (сырьё + накладные + ФОТ + аренда):",
        ["1 − r ≥ "+pc(A.food+A.prod+A.fot+A.ar), "r ≤ "+pc(BE.prod)],
        null,
        "покрыть производство и доставку:",
        ["1 − r ≥ "+pc(A.food+A.prod+A.fot+A.ar+A.com), "r ≤ "+pc(BE.deliv)],
        null,
        "покрыть вообще всё, вместе с администрацией:",
        ["(1 − r) × (1 − "+pc(A.adm)+") ≥ "+pc(A.food+A.prod+A.fot+A.ar+A.com), "недостижимо при этой цене"],
        null,
        ["ФАКТ Маймарта", pc(T.pct), "против порога "+pc(BE.deliv)]
      ]);
      h+=P("Последняя строка недостижима не из-за возвратов, а из-за самой цены: даже при нулевых возвратах "
        +pc(A.food+A.prod+A.fot+A.ar+A.com)+" производства плюс "+pc(A.adm)+" администрации дают больше 100%. "
        +"Это ровно та же проблема, что и у завода в целом, — просто у Маймарта она усилена возвратами.");

      h+=H(8,"Сколько стоят сами возвраты");
      h+=P("Возврат — двойная потеря: не получили выручку и списали уже понесённые затраты. Считаем вторую часть:");
      h+=CALC([
        ["Себестоимость возвращённого", fmt(T.r)+" × "+pc(A.food+A.prod+A.fot+A.ar+A.com)+" = "+fmt(T.ret_cost)],
        ["Недополученная выручка", fmt(T.r)],
        null,
        ["Если бы возвраты были на уровне порога "+pc(BE.deliv), "экономия ≈ "+fmt((T.r-T.g*BE.deliv/100)*(A.food+A.prod+A.fot+A.ar+A.com)/100)]
      ]);

      h+=H(9,"Фудкост по каждому товару");
      h+=P("В таблице товаров колонка «фудкост» — не средняя по заводу, а по конкретному блюду: берётся из отчёта «анализ себестоимости» iiko "
        +"(себестоимость за единицу × количество ÷ выручка, усреднённое по январю–маю 2026). Сопоставлено "+b(D.skus.length+" позиций")+", "
        +"для несопоставленных берётся средневзвешенная по возвратам. Колонка «Потери» — это себестоимость возвращённого товара вместе с производством и доставкой: "
        +"возврат × (фудкост позиции + "+pc(A.prod+A.fot+A.ar+A.com)+" конверсии).");

      h+=H(10,"Что этот расчёт не учитывает");
      h+=P("Честно о слабых местах. "
        +b("Первое")+" — доли затрат взяты средние по заводу; если Маймарт производится на более дешёвой или более дорогой линии, его реальная себестоимость отличается. "
        +b("Второе")+" — бонусы, ретро-скидки и маркетинговые взносы сети в расчёт не входят, они сидят в общих затратах. "
        +b("Третье")+" — предполагается, что возвращённый товар утилизируется; если часть перерабатывается или продаётся со скидкой, потери меньше. "
        +b("Четвёртое")+" — месяцы после "+MNAME[ms[ms.length-1].slice(5)]+" считаются по средним долям, потому что ОПиУ за них ещё не закрыт. "
        +b("Пятое")+" — распределение администрации по выручке условно: можно распределять по объёму или по числу заказов, цифра результата изменится на несколько процентов, но знак — нет.");

      h+=H(11,"Как обновлять");
      h+=P("Отгрузка и возвраты подтягиваются из iiko автоматически при каждом прогоне (три раза в день). "
        +"Доли затрат зашиты в скрипте "+b("gen_maymart.py")+" — их нужно дополнять по мере закрытия месяцев: взять из «Отчёт о прибылях и убытках» новые колонки и добавить в таблицу PL_RATIOS. "
        +"Фудкост по позициям — из файла «анализ себестоимости». Пока новые месяцы не добавлены, расчёт использует средние доли и помечает такие месяцы как оценочные.");

      h+=P('<span style="color:#475569;font-size:11.5px">Расчёт собран '+(D.updated||"")+" · данные iiko и управленческий ОПиУ · система «Пульс»</span>");

      document.getElementById("mm-method").innerHTML=h;
    }

    var built=false;
    function renderAll(){ scheme(); kpi(); verdict(); conditions(); obsMonths(); obsFall(); obsCond(); beBlock(); plTable(); renderPoints(); renderSkus(); method(); if(window.Chart){ chMonths(); chFall(); } built=true; }
    function boot(){
      document.getElementById("mm-sum").textContent="возвраты "+pc(T.pct)+" · "+(T.margin<0?"убыток ":"прибыль ")+fmt(T.margin)+" с начала года";
      var det=document.getElementById("mm-details");
      det.addEventListener("toggle",function(){ var c=document.getElementById("mm-caret"); if(c) c.innerHTML=det.open?"&#9662;":"&#9656;"; if(det.open) renderAll(); });
      document.getElementById("mm-pt-sort").addEventListener("change",function(){ pst.sort=this.value; pst.all=false; renderPoints(); });
      document.getElementById("mm-pt-q").addEventListener("input",function(){ pst.q=this.value; pst.all=false; renderPoints(); });
      document.getElementById("mm-sk-sort").addEventListener("change",function(){ sst.sort=this.value; sst.all=false; renderSkus(); });
      document.getElementById("mm-sk-q").addEventListener("input",function(){ sst.q=this.value; sst.all=false; renderSkus(); });
      document.getElementById("maymart-analytics").addEventListener("click",function(e){
        var t=e.target.closest?e.target.closest("[data-mmall]"):null; if(!t) return;
        if(t.getAttribute("data-mmall")==="p"){ pst.all=!pst.all; renderPoints(); } else { sst.all=!sst.all; renderSkus(); }
      });
      if(det.open) renderAll();
    }
    if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",boot); else boot();
  })();
  </script>
</div>
'''


MM_BEG = "<!--MAYMART-START-->"
MM_END = "<!--MAYMART-END-->"


def inject(html, data):
    block = (MM_BEG + "\n"
             + SECTION.replace("__MMDATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
             + "\n" + MM_END + "\n")
    # ── убираем прошлую версию секции, если пересобираем поверх ──
    a = html.find(MM_BEG)
    if a >= 0:                                   # новая разметка с маркерами
        b = html.find(MM_END, a)
        html = html[:a] + (html[b + len(MM_END):] if b >= 0 else "")
    else:                                        # старая версия — секция стояла в самом низу
        i = html.find('<div class="section" id="maymart-analytics"')
        if i >= 0:
            j = html.find('<footer id="psig-sales"', i)
            if j < 0:
                j = html.find("</body>", i)
            if j > 0:
                html = html[:i] + html[j:]
    # ── ставим сразу под блоком «Аналитика возвратов» ──
    for anchor in ('<div class="section" id="wf-section"',
                   '<div class="section" id="ctr-section"',
                   '<footer id="psig-sales"', "</body>", "</html>"):
        k = html.find(anchor)
        if k >= 0:
            return html[:k] + block + html[k:]
    return html + block


def main():
    data = build()
    p = os.path.join(HERE, "продажи_2026.html")
    html = open(p, encoding="utf-8").read()
    open(p, "w", encoding="utf-8").write(inject(html, data))
    t = data["totals"]
    print("Маймарт: отгрузка %.1f млн, возвраты %.1f млн (%.1f%%), маржа %.1f млн, точек %d, SKU %d"
          % (t["g"] / 1e6, t["r"] / 1e6, t["pct"], t["margin"] / 1e6, t["points"], t["skus"]))


if __name__ == "__main__":
    main()
