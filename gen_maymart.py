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
"adm": 0.17347
},
"2026-02": {
"food": 0.51888,
"prod": 0.06725,
"fot": 0.27792,
"ar": 0.03217,
"com": 0.04779,
"adm": 0.17711
},
"2026-03": {
"food": 0.50547,
"prod": 0.0651,
"fot": 0.25429,
"ar": 0.03114,
"com": 0.07399,
"adm": 0.15446
},
"2026-04": {
"food": 0.4968,
"prod": 0.06002,
"fot": 0.26593,
"ar": 0.03022,
"com": 0.05435,
"adm": 0.15025
},
"2026-05": {
"food": 0.49077,
"prod": 0.06899,
"fot": 0.22907,
"ar": 0.02891,
"com": 0.04993,
"adm": 0.144
}
}
PL_AVG = {"food": 0.50246, "prod": 0.06603, "fot": 0.25757, "ar": 0.0307, "com": 0.05441, "adm": 0.15986}
FOODCOST = {"Упак Плов по-ташкентски (1порц)": 0.5011, "Упак Удон с говядиной (1порц)": 0.4262, "Упак Кимпаб с тунцом (1шт)": 0.4933, "Упак Лагман по-домашнему (1порц)": 0.4087, "Упак Манты с говядиной (1порц)": 0.5797, "Упак Бифштекс с яйцом и картофелем (1порц)": 0.4868, "Упак Плов с курицей (1порц)": 0.3337, "Упак Бефстроганов с картофельным пюре (1порц)": 0.4342, "Упак Зразы куриные с сырным соусом и фузилли (1порц)": 0.4292, "Упак Кимпаб с курицей (1шт)": 0.5424, "Упак Гуйру цомян (1порц)": 0.4697, "Упак Котлета домашняя с рисом и овощами (1порц)": 0.5182, "Упак Куриные котлеты с картофельным пюре и овощами (1порц)": 0.447, "Упак Пенне болоньезе (1порц)": 0.4808, "Упак Шницель куриный с гречкой (1порц)": 0.436, "Упак Тефтели говяжьи с гречкой и овощами (1порц)": 0.4151, "Упак Блины с мясом (3шт)": 0.5297, "Упак Шницель куриный с картофельным пюре (1порц)": 0.4397, "Упак Пельмени с говядиной (1 порц)": 0.5785, "Упак Курица с сыром и гречкой (1порц)": 0.4154, "Упак Салат Гнездо глухаря (1порц)": 0.5056, "Упак Паста с курицей и грибами (1порц)": 0.4806, "Упак Блины с творогом (3шт)": 0.3483, "Упак Курица с сыром и картофельным пюре (1порц)": 0.4375, "Упак Салат Цезарь с курицей (1порц)": 0.5131, "Упак Круассан с курицей (1шт)": 0.3869, "Упак Блины с курицей (3шт)": 0.3937, "Упак Онигири с лососем (1шт)": 0.4328, "Упак Онигири с тунцом (1шт)": 0.2931, "Упак Салат Мимоза (1порц)": 0.4267, "Упак Вареники с картофелем (1порц)": 0.302, "Упак Запеканка картофельная с курицей (по-французски) (1порц)": 0.49, "Упак Курица с сыром с пастой фузилли (1порц)": 0.4407, "Упак Курица с сыром с рисом и паутини (1порц)": 0.4344, "Упак Салат Оливье (1порц)": 0.5087, "Упак Клаб Сэндвич с индейкой (1шт)": 0.4553, "Упак Пельмени с курицей (1 порц)": 0.4149, "Упак Круассан с индейкой (1шт)": 0.3998, "Упак Сэндвич с колбасой (1шт)": 0.4589, "Упак Ролл-салат с курицей (1шт)": 0.5909, "Упак Багет с индейкой (1шт)": 0.4017, "Упак Сельдь под шубой (1порц)": 0.4066, "Упак Онигири с курицей (1шт)": 0.3483, "Упак Клаб Сэндвич с говядиной (1шт)": 0.4408, "Упак Салат Малибу (1порц)": 0.5213, "Упак Блины с ветчиной и сыром (3шт)": 0.4351, "Упак Клаб Сэндвич с курицей (1шт)": 0.4473, "Упак Макароны по-флотски (1порц)": 0.5359, "Упак Солянка (1порц)": 0.5343, "Упак Клаб Сэндвич крок-месье (1шт)": 0.4323, "Упак Морс Черная смородина 0,5 (1шт)": 0.4959, "Упак Компот из сухофруктов 0,5 (1шт)": 0.3246, "Упак Жареная говядина с картофелем и овощами (1порц)": 0.4708, "Упак Казон кабоб с овощами (1порц)": 0.4494, "Упак Курица карри с картофельным пюре (1порц)": 0.4738, "Упак Курица карри с турецким рисом (1порц)": 0.5162, "Упак Спагетти с курицей в грибном соусе (1порц)": 0.5094, "Упак Куриная грудка с овощным рататуем (1порц)": 0.512, "Упак Спагетти с курицей в соусе том ям (1порц)": 0.472, "Упак Хот дог (1шт)": 0.6811, "Упак Жареные сосиски с пюре и капустой (1порц)": 0.4426, "Упак Суп борщ с говядиной (1порц)": 0.4626, "Упак Суп говяжий с фрикадельками (1порц)": 0.3632, "ЛЛ* Упак Круассан с курицей (1шт)": 0.3869, "Упак Самса с курицей сырая ФЗ СМ (30 шт гофра)": 0.3439, "ЛЛ* Упак Круассан с лососем (1шт)": 0.3816, "Упак Суп лапша с курицей (1порц)": 0.4296, "ЛЛ* Упак Плов по-ташкентски (1порц)": 0.5011, "Упак Чиабатта с говядиной и омлетом (1шт)": 0.4135, "ЛЛ* Упак Ролл-салат с лососем (1шт)": 0.6498, "Упак Клаб Сэндвич с говядиной замор (24шт гофра)": 0.348, "Упак Сосиска в тесте  готов СМ (30шт гофра)": 0.4119, "ЛЛ* Упак Сэндвич с колбасой (1шт)": 0.4589, "Упак Круассан с лососем (1шт)": 0.3816, "Упак Эклер крем-брюле (6 упак гофра)": 0.4552, "ЛЛ* Упак Гуйру цомян (1порц)": 0.4697, "Упак Самса с курицей готов ФЗ СМ (30шт гофра )": 0.3592, "Упак Самса с говядиной сырая ФЗ СМ (30 шт гофра)": 0.482, "RP* Упак Булка с яблоком готов СМ (15 шт гофра)": 0.28, "Упак Клаб Сэндвич с курицей замор (24 шт гофра)": 0.3968, "RP* Упак Брецель-дог (20шт)": 0.5658, "RP* Упак Маффин шоколадный (24шт)": 0.5066, "ЛЛ* Упак Бризоль с рисом (1порц)": 0.6263, "ЛЛ* Упак Шницель куриный с картофельным пюре (1порц)": 0.4397, "ЛЛ* Упак Багет с индейкой (1шт)": 0.4017, "ЛЛ* Упак Хот дог (1шт)": 0.6811, "RP* Упак Сосиска в тесте  готов СМ (30шт гофра)": 0.4233, "ЛЛ* Упак Блины с ветчиной и сыром (3шт)": 0.4351, "ЛЛ* Упак Чиабатта с говядиной и омлетом (1шт)": 0.4135, "ЛЛ* Упак Шницель куриный с гречкой (1порц)": 0.436, "Б* Самса с курицей ФЗ (1шт)": 0.8584, "ЛЛ* Упак Блины с мясом (3шт)": 0.5297, "ЛЛ* Упак Клаб Сэндвич с курицей (1шт)": 0.4473, "ЛЛ* Упак Бифштекс с яйцом и картофелем (1порц)": 0.4868, "ЛЛ* Упак Кимпаб с тунцом (1шт)": 0.4933, "Упак Маффин с черной смородиной (24шт)": 0.5515, "ЛЛ* Упак Курица с сыром с пастой фузилли (1порц)": 0.4407, "ЛЛ* Упак Ролл-салат с курицей (1шт)": 0.5909, "ЛЛ* Упак Онигири с тунцом (1шт)": 0.2931, "ЛЛ* Упак Тучикены с картофельным пюре (1порц)": 0.571, "Упак Бризоль с рисом (1порц)": 0.6263, "RP* Упак Пирожок с капустой  готов СМ (30 шт гофра)": 0.3329, "RP* Упак Пирожок с картофелем готов СМ (30 шт гофра)": 0.432, "ЛЛ* Упак Пенне болоньезе (1порц)": 0.4808, "ЛЛ* Упак Онигири с лососем (1шт)": 0.4328, "RP* Упак Улитка с изюмом готов СМ (10 шт гофра)": 0.326, "ЛЛ* Упак Блины с яблоком (3шт)": 0.3675, "Упак Ролл-салат с лососем (1шт)": 0.6498, "ЛЛ* Упак Котлета пожарская с картофельным пюре (1порц)": 0.5163, "ЛЛ* Упак Кимпаб с курицей (1шт)": 0.5424, "Упак Котлеты куриные с картофельным пюре и капустой (1порц)": 0.5429, "ЛЛ* Упак Паста с курицей и грибами (1порц)": 0.4806, "Упак Сосиска в тесте СМ (8шт)": 0.3447, "RP* Упак Блины с ветчиной и сыром (3шт)": 0.5071, "Упак Эклер крем-брюле (5шт)": 0.4173, "Упак Салат с хрустящей курочкой (1порц)": 0.3442, "Упак Салат фунчоза с овощами (1порц)": 0.4074, "RP* Упак Плов по-ташкентски (1порц)": 0.5498, "RP* Упак Куриные котлеты с картофельным пюре и овощами (1порц)": 0.5159, "RP* Упак Багет с курицей под гриль (1шт)": 0.4956, "АР* Упак Бефстроганов с картофельным пюре (1порц)": 0.5367, "ЛЛ* Упак Вареники с картофелем (1порц)": 0.302, "RP* Упак Блины с творогом (3шт)": 0.4073, "ЛЛ* Упак Клаб Сэндвич с говядиной (1шт)": 0.4408, "Упак Красный бархат в стакане с вилкой (1шт)": 0.4692, "АР* Упак Шницель куриный с гречкой (1порц)": 0.4713, "АР* Упак Салат Цезарь с курицей (1порц)": 0.5301, "ЛЛ* Упак Манты с говядиной (1порц)": 0.5797, "ЛЛ* Упак Блины с творогом (3шт)": 0.3483, "Упак Сникерс в стакане с вилкой (1шт)": 0.4113, "RP* Упак Манты с говядиной (1порц)": 0.6143, "RP* Упак Булка с маком готов СМ (15 шт гофра)": 0.295, "Упак Медовик в стакане с вилкой (1шт)": 0.4629}
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


def build():
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
            "est": m not in PL_RATIOS,
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
        "be": be, "points": plist, "skus": slist,
        "company": {"full": round(sum(a.values()) * 100, 1), "op": round((1 - sum(a.values())) * 100, 1)},
        "pl_months": sorted(PL_RATIOS.keys()),
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
      <div id="mm-verdict" style="margin:8px 0 14px"></div>
      <div id="mm-kpi" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px"></div>

      <div class="card" style="margin-top:14px">
        <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:8px">&#128200; Отгрузка, возвраты и маржа по месяцам</div>
        <div style="height:300px"><canvas id="mm-ch-months"></canvas></div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin-top:12px">
        <div class="card">
          <div style="font-size:13px;font-weight:700;color:#f1f5f9;margin-bottom:8px">&#129517; От отгрузки до маржи <span style="font-weight:500;font-size:11px;color:#64748b">— куда уходят деньги, с начала года</span></div>
          <div style="height:320px"><canvas id="mm-ch-fall"></canvas></div>
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
    function fmt(v){ var a=Math.abs(Math.round(v)); var s=a>=1e6?(a/1e6).toFixed(1).replace(".",",")+" млн":(a>=1e3?Math.round(a/1e3)+" тыс":String(a)); return (v<0?"−":"")+s; }
    function pc(v){ return String((Math.round(v*10)/10)).replace(".",",")+"%"; }
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

    function chMonths(){
      var cv=document.getElementById("mm-ch-months"); if(!cv||!window.Chart) return;
      try{var ex=Chart.getChart?Chart.getChart(cv):null; if(ex) ex.destroy();}catch(e){}
      var L=D.months.map(function(m){return m.lbl;});
      new Chart(cv.getContext("2d"),{data:{labels:L,datasets:[
        {type:"bar",label:"Нетто-выручка",data:D.months.map(function(m){return +(m.n/1e6).toFixed(2);}),backgroundColor:"#22c55e",borderRadius:5,stack:"s",order:3},
        {type:"bar",label:"Возвраты",data:D.months.map(function(m){return +(m.r/1e6).toFixed(2);}),backgroundColor:"#e2896b",borderRadius:5,stack:"s",order:3},
        {type:"line",label:"Маржа после полной с/с",data:D.months.map(function(m){return +(m.margin/1e6).toFixed(2);}),borderColor:"#ef4444",backgroundColor:"#ef4444",borderWidth:2,tension:.3,pointRadius:3,order:1},
        {type:"line",label:"% возврата",data:D.months.map(function(m){return m.pct;}),borderColor:"#c9a94e",backgroundColor:"#c9a94e",borderWidth:2,borderDash:[5,4],tension:.3,pointRadius:3,yAxisID:"y1",order:2}
      ]},options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{color:"#cbd5e1",font:{size:11},boxWidth:12}},datalabels:{display:false},
          tooltip:{callbacks:{label:function(c){return c.dataset.label+": "+(c.dataset.yAxisID==="y1"?pc(c.parsed.y):(String(c.parsed.y).replace(".",",")+" млн"));}}}},
        scales:{x:{stacked:true,ticks:{color:"#94a3b8",font:{size:12,weight:"600"}},grid:{display:false}},
          y:{stacked:true,ticks:{color:"#64748b",font:{size:10},callback:function(v){return v+" М";}},grid:{color:"rgba(51,65,85,.4)"}},
          y1:{position:"right",beginAtZero:true,ticks:{color:"#c9a94e",font:{size:10},callback:function(v){return v+"%";}},grid:{display:false}}}}});
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
      var pl=D.pl_months.map(function(m){return m.slice(5);}).join(", ");
      document.getElementById("mm-method").innerHTML=
        "<b>Кто такой Маймарт.</b> Все контрагенты с префиксом «90-» — "+D.totals.points+" торговых точек сети. Данные по отгрузке и возвратам берутся из iiko вместе с остальным дашбордом продаж.<br><br>"
        +"<b>Полная себестоимость.</b> Доли затрат взяты из управленческого ОПиУ 2026 (месяцы "+pl+", факт) и распределены на товар: продуктовая "+pc(R.food)+", производственные накладные "+pc(R.prod)+", ФОТ производства "+pc(R.fot)+", аренда "+pc(R.ar)+", доставка и реализация "+pc(R.com)+", администрация "+pc(R.adm)+". Итого "+pc(D.company.full)+" от выручки — именно поэтому завод в целом работает с операционной рентабельностью "+pc(D.company.op)+".<br><br>"
        +"<b>База распределения.</b> Производство, аренда и доставка считаются от <i>отгрузки</i>: товар произвели, упаковали и отвезли независимо от того, вернётся он или нет. Администрация распределяется от <i>нетто-выручки</i>. Возврат — это двойная потеря: не получили выручку и списали уже понесённые затраты.<br><br>"
        +"<b>Фудкост по товарам.</b> Продуктовая себестоимость каждого SKU — из отчёта «анализ себестоимости» (январь–май 2026), для несопоставленных позиций берётся средневзвешенная. Колонка «Потери» — себестоимость возвращённого товара вместе с производством и доставкой.<br><br>"
        +"<b>Порог безубыточности.</b> Максимальная доля возвратов, при которой выручка ещё покрывает соответствующий уровень затрат, при текущей цене отгрузки.<br><br>"
        +"<b>Что это не учитывает.</b> Возможные бонусы и ретро-скидки сети, отдельные условия по логистике, а также то, что часть возвратов может перерабатываться, а не утилизироваться. Месяцы после "+pl.split(", ").pop()+" считаются по средним долям ОПиУ.";
    }

    var built=false;
    function renderAll(){ kpi(); verdict(); beBlock(); plTable(); renderPoints(); renderSkus(); method(); if(window.Chart){ chMonths(); chFall(); } built=true; }
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


def inject(html, data):
    block = SECTION.replace("__MMDATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    # убираем прошлую версию секции, если пересобираем поверх
    i = html.find('<div class="section" id="maymart-analytics"')
    if i >= 0:
        j = html.find("<footer id=\"psig-sales\"", i)
        if j < 0:
            j = html.find("</body>", i)
        if j > 0:
            html = html[:i] + html[j:]
    for anchor in ('<footer id="psig-sales"', "</body>", "</html>"):
        k = html.find(anchor)
        if k >= 0:
            return html[:k] + block + "\n" + html[k:]
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
