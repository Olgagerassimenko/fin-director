# -*- coding: utf-8 -*-
"""Полная себестоимость завода: анализ по ОПиУ + продажи по контрагентам.

Строит скрытую вкладку «Полная себестоимость: за счёт чего прибыль и убыток»
в дашборде себестоимости. Считает:
  • маржинальную прибыль, постоянные затраты, точку безубыточности и запас прочности по месяцам;
  • факторное разложение изменения прибыли (объём / маржинальность / постоянные) месяц к месяцу;
  • структуру затрат по 79 статьям ОПиУ;
  • выручку по каналам продаж (контрагентам) с 2025 года;
  • фудкост по категориям продукции.

Источники (лежат в репозитории):
  • «Отчет о прибылях и убытках 2025-2026.xlsx» — управленческий ОПиУ, янв-2025 … май-2026;
  • «8. Продажи 2025-2026гг..xlsx» — выручка по контрагентам помесячно;
  • «SKU_Себестоимость/2025-2026год анализ себестоимости по май.xlsx» — себестоимость по SKU.
Обновлять файлы при закрытии месяца — вкладка пересоберётся сама на следующем прогоне CI.
"""
import json, os, re, datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PL_FILE = "Отчет о прибылях и убытках 2025-2026.xlsx"
SALES_FILE = "8. Продажи 2025-2026гг..xlsx"
SKU_FILE = os.path.join("SKU_Себестоимость", "2025-2026год анализ себестоимости по май.xlsx")
TARGET = "дашборд_себестоимость_2025-2026.html"

MS = ["", "Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
MN = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

# ── классификация статей ОПиУ ────────────────────────────────────────────────
VARIABLE = ["1.1.Себестоимость продуктовая", "1.31.Масло фритюрное", "1.5.Расходный материал производство",
            "1.30.Возвраты от дистрибьютеров", "1.7.Истек срок хранения (порча)", "1.28.Брак", "1.24.Бракераж",
            "1.3.Недостача инвентаризации", "1.4.Излишки инвентаризации",
            "1.13.Коррекция отрицательных остатков на складе", "1.27.Нарушение тех.процесса",
            "1.26.За счет МОЛ", "1.16.Мусор", "1.18.Электроэнергия", "Логистика доставка"]
FIXED = ["Итого 2.ФОТ Производство", "Итого 3.Арендная плата", "ИТОГО 3.1.ФОТ АУП", "Итого 3.3. РазныеАдмРасходы",
         "2.4.Маркетинг", "2.5.1.Расходы по реализации Прочие", "2.5.5.Проработка новых блюд", "2.5.9.Продвижение товара",
         "1.2.Производ.расходы прочие", "1.9.Ремонт/Обслуживание производ.оборудования", "1.14.Ремонт помещений",
         "1.12.Спецодежда", "1.11.Списание сломанных ТМЗ", "1.20.Расходный материал тех.отдела",
         "1.25.Проработка блюд (текущих)", "Расходы по вознаграждениям", "Зарплата", "3.Расходы АДМ, прочие",
         "1.8.Пробы", "1.19.Вредные условия труда"]
# крупные блоки для структуры
LAYERS = [
    ("food",  "Продуктовая себестоимость", ["1.1.Себестоимость продуктовая", "1.31.Масло фритюрное"]),
    ("povh",  "Производственные накладные", ["1.2.Производ.расходы прочие", "1.3.Недостача инвентаризации",
              "1.4.Излишки инвентаризации", "1.5.Расходный материал производство", "1.7.Истек срок хранения (порча)",
              "1.9.Ремонт/Обслуживание производ.оборудования", "1.11.Списание сломанных ТМЗ", "1.12.Спецодежда",
              "1.13.Коррекция отрицательных остатков на складе", "1.14.Ремонт помещений", "1.16.Мусор",
              "1.18.Электроэнергия", "1.20.Расходный материал тех.отдела", "1.24.Бракераж",
              "1.25.Проработка блюд (текущих)", "1.26.За счет МОЛ", "1.27.Нарушение тех.процесса", "1.28.Брак",
              "1.30.Возвраты от дистрибьютеров", "1.8.Пробы", "1.19.Вредные условия труда"]),
    ("fot",   "ФОТ производства", ["Итого 2.ФОТ Производство"]),
    ("rent",  "Аренда и коммуналка", ["Итого 3.Арендная плата"]),
    ("comm",  "Реализация, логистика, маркетинг", ["Итого 2.Расходы по реализации(папка)"]),
    ("adm",   "Администрация (АУП)", ["Итого 3.Расходы АДМ"]),
]
DETAIL_LINES = ["1.1.Себестоимость продуктовая", "2.1.ЗП Производство", "2.5.Налоги Производство",
                "2.4.Питание персонала", "3.1.1.ЗП АУП", "3.1.4. Налоги АУП", "3.3.2.Налоги НДС",
                "3.1.Аренда (пр-во)", "3.2.Аренда КомУсл Пр-во", "1.18.Электроэнергия", "Логистика доставка",
                "2.4.Маркетинг", "3.3.1.Админ.расходы ПРОЧИЕ", "3.3.3.Услуги охраны", "1.30.Возвраты от дистрибьютеров",
                "1.3.Недостача инвентаризации", "1.5.Расходный материал производство", "1.28.Брак",
                "1.14.Ремонт помещений", "1.9.Ремонт/Обслуживание производ.оборудования", "3.1.2.Аренда квартир д/сотрудников (АУП)",
                "1.4.Излишки инвентаризации", "1.7.Истек срок хранения (порча)", "1.2.Производ.расходы прочие"]


def load_pl():
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(HERE, PL_FILE), data_only=True)
    ws = wb.active
    cols = {}
    for i, c in enumerate(ws[5]):
        m = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', str(c.value or "").strip())
        if m:
            cols["%s-%s" % (m.group(3), m.group(2))] = i
    rows = {}
    for r in ws.iter_rows(min_row=6, values_only=True):
        n = r[0]
        if not n:
            continue
        n = str(n).strip()
        vals = {k: (r[i] if isinstance(r[i], (int, float)) else 0) for k, i in cols.items()}
        if any(vals.values()):
            rows[n] = vals
    return sorted(cols), rows


def load_channels():
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(HERE, SALES_FILE), data_only=True, read_only=True)
    mre = re.compile(r'^(\d{2})\s*\(')
    res = defaultdict(lambda: defaultdict(float))
    names = defaultdict(lambda: defaultdict(float))
    for sheet in wb.sheetnames:
        y = re.search(r'(\d{4})', sheet)
        if not y:
            continue
        year = y.group(1)
        ws = wb[sheet]
        h5 = h6 = None
        body = []
        for i, r in enumerate(ws.iter_rows(values_only=True), 1):
            if i == 5: h5 = r
            elif i == 6: h6 = r
            elif i > 6: body.append(r)
        colmap, cur = {}, None
        for j in range(len(h6)):
            lbl = str(h5[j] or "").strip()
            m = mre.match(lbl)
            if m: cur = m.group(1)
            elif lbl.lower().startswith("итог"): cur = None
            if str(h6[j] or "").strip().startswith("Сумма прихода") and cur:
                colmap[j] = "%s-%s" % (year, cur)
        ctr = typ = None
        for r in body:
            if r[0]: ctr = str(r[0]).strip()
            if r[1]: typ = str(r[1]).strip()
            if not ctr or typ != "Выручка расходной накладной" or ctr.lower().startswith("итог"):
                continue
            for j, mk in colmap.items():
                v = r[j] if j < len(r) else None
                if isinstance(v, (int, float)) and v:
                    res[channel_of(ctr)][mk] += v
                    names[ctr][mk] += v
    return res, names


def channel_of(n):
    s = str(n).strip()
    m = re.match(r'^(\d+)\s*[-–]', s)
    num = m.group(1) if m else None
    low = s.lower()
    if num == "85" or "дфз" in low: return "ДФЗ · дистрибьютор"
    if num == "84" or "гамаус" in low: return "Гамаус · дистрибьютор"
    if num == "95" or "пикассо" in low: return "Фуд Пикассо · дистрибьютор"
    if num == "96" or "dsf" in low: return "DSF · дистрибьютор"
    if num == "90": return "Маймарт"
    if num == "102" or "яндекс" in low: return "Яндекс Лавка"
    if num == "7" or "kaspi" in low: return "Kaspi"
    if num in ("110", "99") or "азс" in low or "sinooil" in low: return "АЗС"
    if num in ("1", "2", "9") or "базилик" in low: return "Базилик"
    if "crave" in low: return "Crave Cafe"
    if "o-live" in low or num == "98": return "O-live"
    if "глово" in low or "glovo" in low: return "Glovo"
    return "Прочие"


def load_cats():
    import openpyxl
    p = os.path.join(HERE, SKU_FILE)
    if not os.path.exists(p):
        return {}, []
    wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
    cat = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    months = set()
    for s in wb.sheetnames:
        m = re.search(r'с (\d{2})\.(\d{2})\.(\d{4})', s)
        if not m:
            continue
        mk = "%s-%s" % (m.group(3), m.group(2))
        months.add(mk)
        for r in wb[s].iter_rows(min_row=5, values_only=True):
            if not r or not r[1]:
                continue
            try:
                qty = float(r[3] or 0); cpu = float(r[4] or 0); rev = float(r[6] or 0)
            except (TypeError, ValueError):
                continue
            c = (str(r[0] or "").strip() or "Прочее")
            cat[c][mk][0] += rev
            cat[c][mk][1] += qty * cpu
    return cat, sorted(months)


def build():
    months, R = load_pl()

    def v(k, m):
        return R.get(k, {}).get(m, 0)

    pl = {}
    for m in months:
        rev = v("Итого Выручка", m)
        var = sum(v(k, m) for k in VARIABLE)
        fix = sum(v(k, m) for k in FIXED)
        cm = rev - var
        cmr = cm / rev if rev else 0
        op = cm - fix
        bep = fix / cmr if cmr > 0 else 0
        layers = {key: sum(v(k, m) for k in keys) for key, _t, keys in LAYERS}
        pl[m] = {
            "rev": round(rev), "var": round(var), "fix": round(fix), "cm": round(cm),
            "cmr": round(cmr * 100, 2), "op": round(op), "bep": round(bep),
            "safety": round((rev - bep) / rev * 100, 1) if rev else 0,
            "gross": round(v("Валовая прибыль", m)), "net": round(v("ИТОГО ЧИСТАЯ ПРИБЫЛЬ", m)),
            "layers": {k: round(x) for k, x in layers.items()},
        }

    # факторное разложение изменения операционной прибыли
    for i, m in enumerate(months):
        if i == 0:
            pl[m]["fx"] = None
            continue
        p0, p1 = pl[months[i - 1]], pl[m]
        vol = (p1["rev"] - p0["rev"]) * p0["cmr"] / 100
        mar = p1["rev"] * (p1["cmr"] - p0["cmr"]) / 100
        fxd = -(p1["fix"] - p0["fix"])
        pl[m]["fx"] = {"vol": round(vol), "mar": round(mar), "fix": round(fxd),
                       "d": round(p1["op"] - p0["op"])}
    # год к году
    for m in months:
        prev = "%d-%s" % (int(m[:4]) - 1, m[5:])
        if prev in pl:
            p0, p1 = pl[prev], pl[m]
            pl[m]["yoy"] = {"vol": round((p1["rev"] - p0["rev"]) * p0["cmr"] / 100),
                            "mar": round(p1["rev"] * (p1["cmr"] - p0["cmr"]) / 100),
                            "fix": round(-(p1["fix"] - p0["fix"])),
                            "d": round(p1["op"] - p0["op"]), "prev": prev}
        else:
            pl[m]["yoy"] = None

    lines = []
    for name, vals in R.items():
        if name.startswith("Итого") or name.startswith("ИТОГО") or name in ("Валовая прибыль", "Торговая выручка", "Выручка"):
            continue
        tot = sum(vals.values())
        if abs(tot) < 500000:
            continue
        grp = "перем." if name in VARIABLE else ("постоян." if name in FIXED else "прочее")
        lines.append({"n": name, "g": grp, "m": {k: round(x) for k, x in vals.items() if x}})
    lines.sort(key=lambda x: -abs(sum(x["m"].values())))
    LOSS_LINES = ["1.30.Возвраты от дистрибьютеров", "1.28.Брак", "1.7.Истек срок хранения (порча)",
                  "1.3.Недостача инвентаризации", "1.24.Бракераж", "1.27.Нарушение тех.процесса",
                  "1.11.Списание сломанных ТМЗ"]
    keep = lines[:40]
    have = {x["n"] for x in keep}
    for nm in LOSS_LINES:
        if nm not in have and nm in R:
            keep.append({"n": nm, "g": "перем." if nm in VARIABLE else "постоян.",
                         "m": {k: round(x) for k, x in R[nm].items() if x}})
    lines = keep

    chan, names = load_channels()
    cmonths = sorted({m for d in chan.values() for m in d})
    # отсекаем неполный последний месяц продаж (менее 40% от среднего)
    tot_by_m = {m: sum(d.get(m, 0) for d in chan.values()) for m in cmonths}
    avg = sum(tot_by_m.values()) / max(1, len(tot_by_m))
    cmonths = [m for m in cmonths if tot_by_m[m] > avg * 0.4]
    chan_out = {c: {m: round(d.get(m, 0)) for m in cmonths if d.get(m)} for c, d in chan.items()}
    chan_out = {c: d for c, d in chan_out.items() if sum(d.values()) > 3000000}

    top_ctr = []
    for n, d in names.items():
        tot = sum(x for m, x in d.items() if m in cmonths)
        if tot > 20000000:
            top_ctr.append({"n": n, "t": round(tot), "m": {m: round(d.get(m, 0)) for m in cmonths if d.get(m)}})
    top_ctr.sort(key=lambda x: -x["t"])
    top_ctr = top_ctr[:40]

    cat, cmo = load_cats()
    cats = []
    for c, d in cat.items():
        rev = sum(x[0] for x in d.values()); cost = sum(x[1] for x in d.values())
        if rev < 5000000 or cost <= 0:
            continue
        fc = cost / rev
        if not (0.15 <= fc <= 0.98):
            continue
        cats.append({"n": c, "rev": round(rev), "cost": round(cost), "fc": round(fc * 100, 1),
                     "gp": round(rev - cost),
                     "m": {m: [round(x[0]), round(x[1])] for m, x in d.items() if x[0]}})
    cats.sort(key=lambda x: -x["rev"])

    y = {}
    for yr in ("2025", "2026"):
        ms = [m for m in months if m.startswith(yr)]
        if not ms:
            continue
        y[yr] = {"months": ms,
                 "rev": sum(pl[m]["rev"] for m in ms), "var": sum(pl[m]["var"] for m in ms),
                 "fix": sum(pl[m]["fix"] for m in ms), "op": sum(pl[m]["op"] for m in ms),
                 "cmr": round(sum(pl[m]["cm"] for m in ms) / max(1, sum(pl[m]["rev"] for m in ms)) * 100, 2)}

    return {
        "months": months, "pl": pl, "lines": lines,
        "layers": [{"k": k, "t": t} for k, t, _ in LAYERS],
        "chan": chan_out, "cmonths": cmonths, "ctr": top_ctr,
        "cats": cats[:16], "years": y,
        "built": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
    }


SECTION = r'''
<div id="fullcost-analytics" style="max-width:1400px;margin:26px auto 0;padding:0 16px;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <details id="fc-details" style="background:#111827;border:1px solid #1f2937;border-radius:16px;overflow:hidden">
    <summary style="cursor:pointer;list-style:none;padding:16px 20px;font-size:15px;font-weight:800;color:#f1f5f9;display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:linear-gradient(90deg,#111827,#0f172a)">
      <span style="color:#c9a94e"><span id="fc-caret">&#9656;</span> &#129518; Полная себестоимость: за счёт чего прибыль и убыток</span>
      <span id="fc-sum" style="font-weight:600;font-size:12px;color:#94a3b8"></span>
      <span style="font-weight:500;font-size:12px;color:#64748b;margin-left:auto">ОПиУ + продажи по контрагентам с 2025 года &middot; нажмите, чтобы раскрыть</span>
    </summary>
    <div style="padding:14px 18px 22px;background:#0b1220">

      <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px">
        <div id="fc-period" style="display:inline-flex;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:3px"></div>
        <select id="fc-month" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:9px;padding:7px 11px;font-size:12.5px;cursor:pointer"></select>
        <div id="fc-mode" style="display:inline-flex;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:3px"></div>
        <button id="fc-open" type="button" style="margin-left:auto;background:#c9a94e;color:#111827;border:0;border-radius:10px;padding:9px 16px;font-size:12.5px;font-weight:800;cursor:pointer">&#128203; Полный разбор</button>
      </div>

      <div id="fc-kpi" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(158px,1fr));gap:9px"></div>
      <div id="fc-alert" style="margin-top:12px"></div>

      <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:14px;margin-top:12px">
        <div style="font-size:13.5px;font-weight:700;color:#f1f5f9;margin-bottom:2px">&#128201; Выручка против точки безубыточности</div>
        <div style="font-size:11.5px;color:#64748b;margin-bottom:8px">столбики — выручка, линия — сколько нужно выручки, чтобы выйти в ноль. Разрыв между ними и есть прибыль или убыток.</div>
        <div style="height:330px"><canvas id="fc-ch1"></canvas></div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:12px;margin-top:12px">
        <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:14px">
          <div style="font-size:13.5px;font-weight:700;color:#f1f5f9;margin-bottom:2px">&#129521; Структура полной себестоимости</div>
          <div id="fc-struct-sub" style="font-size:11.5px;color:#64748b;margin-bottom:8px"></div>
          <div style="height:300px"><canvas id="fc-ch2"></canvas></div>
        </div>
        <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:14px">
          <div style="font-size:13.5px;font-weight:700;color:#f1f5f9;margin-bottom:2px">&#9878;&#65039; За счёт чего изменился результат</div>
          <div id="fc-fx-sub" style="font-size:11.5px;color:#64748b;margin-bottom:8px"></div>
          <div style="height:300px"><canvas id="fc-ch3"></canvas></div>
        </div>
      </div>

      <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:14px;margin-top:12px">
        <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px">
          <div style="font-size:13.5px;font-weight:700;color:#f1f5f9">&#128197; Месяц к месяцу</div>
          <span style="font-size:11.5px;color:#64748b">клик по строке — выбрать месяц</span>
          <div id="fc-cmp" style="margin-left:auto;display:inline-flex;background:#0f172a;border:1px solid #334155;border-radius:9px;padding:3px"></div>
        </div>
        <div id="fc-mom" style="overflow-x:auto"></div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:12px;margin-top:12px">
        <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:14px">
          <div style="font-size:13.5px;font-weight:700;color:#f1f5f9;margin-bottom:8px">&#128200; Статьи затрат: что выросло и что упало</div>
          <div id="fc-lines" style="overflow-x:auto"></div>
        </div>
        <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:14px">
          <div style="font-size:13.5px;font-weight:700;color:#f1f5f9;margin-bottom:8px">&#127978; Каналы продаж</div>
          <div style="height:250px;margin-bottom:8px"><canvas id="fc-ch4"></canvas></div>
          <div id="fc-chan" style="overflow-x:auto"></div>
        </div>
      </div>

      <div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:14px;margin-top:12px">
        <div style="font-size:13.5px;font-weight:700;color:#f1f5f9;margin-bottom:2px">&#127859; Фудкост по категориям продукции</div>
        <div style="font-size:11.5px;color:#64748b;margin-bottom:8px">по позициям с заполненной себестоимостью в отчёте о продажах iiko</div>
        <div style="height:300px"><canvas id="fc-ch5"></canvas></div>
      </div>

    </div>
  </details>

  <div id="fc-modal" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(2,6,23,.82);backdrop-filter:blur(3px);overflow-y:auto;padding:26px 14px">
    <div style="max-width:940px;margin:0 auto;background:#0f172a;border:1px solid #334155;border-radius:16px;box-shadow:0 24px 70px rgba(0,0,0,.6)">
      <div style="display:flex;align-items:center;gap:12px;padding:18px 24px;border-bottom:1px solid #1f2937;position:sticky;top:0;background:#0f172a;border-radius:16px 16px 0 0">
        <div>
          <div style="font-size:16px;font-weight:800;color:#f1f5f9;letter-spacing:-.01em">Полный разбор себестоимости и результата</div>
          <div id="fc-modal-sub" style="font-size:11.5px;color:#64748b;margin-top:2px"></div>
        </div>
        <button id="fc-close" type="button" style="margin-left:auto;background:#1e293b;color:#cbd5e1;border:1px solid #334155;border-radius:9px;padding:7px 13px;font-size:12.5px;font-weight:700;cursor:pointer">Закрыть</button>
      </div>
      <div id="fc-modal-body" style="padding:20px 26px 30px"></div>
    </div>
  </div>

  <script>window.FULLCOST = __FCDATA__;</script>
  <script>
  (function(){
    var D=window.FULLCOST; if(!D) return;
    var MS=["","Янв","Фев","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек"];
    var MN=["","январь","февраль","март","апрель","май","июнь","июль","август","сентябрь","октябрь","ноябрь","декабрь"];
    var LT={}; D.layers.forEach(function(l){ LT[l.k]=l.t; });
    var LC={food:"#ef4444",povh:"#f97316",fot:"#eab308",rent:"#84cc16",comm:"#22d3ee",adm:"#a78bfa"};
    function mln(v){ var a=Math.abs(v)/1e6; var s=(a>=100?a.toFixed(0):a.toFixed(1)).replace(".",","); return (v<0?"−":"")+s+" млн"; }
    function pc(v,d){ d=(d==null?1:d); return (v<0?"−":"")+Math.abs(v).toFixed(d).replace(".",",")+"%"; }
    function sg(v){ return (v>0?"+":"")+mln(v).replace("−","−"); }
    function lbl(m){ return MS[+m.slice(5)]+" "+m.slice(2,4); }
    function esc(s){ return String(s).replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];}); }

    var st={period:"all",month:D.months[D.months.length-1],mode:"abs",cmp:"mom"};
    function months(){ return st.period==="all"?D.months:D.months.filter(function(m){return m.indexOf(st.period)===0;}); }
    function agg(ms){
      var o={rev:0,var_:0,fix:0,op:0,layers:{}};
      D.layers.forEach(function(l){ o.layers[l.k]=0; });
      ms.forEach(function(m){ var p=D.pl[m]; o.rev+=p.rev; o.var_+=p.var; o.fix+=p.fix; o.op+=p.op;
        D.layers.forEach(function(l){ o.layers[l.k]+=p.layers[l.k]||0; }); });
      o.cm=o.rev-o.var_; o.cmr=o.rev?o.cm/o.rev*100:0; o.full=o.rev-o.op;
      o.bep=o.cmr>0?o.fix/(o.cmr/100):0; o.safety=o.rev?(o.rev-o.bep)/o.rev*100:0;
      return o;
    }
    function seg(id,items,cur,cb){
      var el=document.getElementById(id); if(!el) return;
      el.innerHTML=items.map(function(it){ var on=it[0]===cur;
        return '<button type="button" data-v="'+it[0]+'" style="border:0;background:'+(on?"#c9a94e":"transparent")+';color:'+(on?"#111827":"#cbd5e1")+';font-size:12px;font-weight:700;padding:6px 12px;border-radius:8px;cursor:pointer">'+it[1]+'</button>';
      }).join("");
      el.onclick=function(e){ var b=e.target.closest("button"); if(b) cb(b.getAttribute("data-v")); };
    }

    function kpi(){
      var a=agg(months()), p=D.pl[st.month];
      var neg=a.op<0;
      var cards=[
        ["Выручка",mln(a.rev),months().length+" мес.","#e2e8f0"],
        ["Маржинальная прибыль",pc(a.cmr),"выручка минус переменные","#22d3ee"],
        ["Постоянные затраты",mln(a.fix),(a.fix/months().length/1e6).toFixed(0)+" млн в месяц","#f59e0b"],
        ["Полная себестоимость",mln(a.full),Math.round(a.full/a.rev*100)+"₸ на 100₸ выручки","#fb923c"],
        [neg?"Операционный убыток":"Операционная прибыль",mln(a.op),pc(a.op/a.rev*100)+" к выручке",neg?"#ef4444":"#22c55e"],
        ["Точка безубыточности",mln(a.bep/months().length),"выручки в месяц","#a78bfa"],
        ["Запас прочности",pc(a.safety),a.safety<0?"выручки не хватает":"есть подушка",a.safety<0?"#ef4444":"#22c55e"],
        [MN[+st.month.slice(5)]+" "+st.month.slice(0,4),mln(p.op),"результат месяца",p.op<0?"#ef4444":"#22c55e"]
      ];
      document.getElementById("fc-kpi").innerHTML=cards.map(function(c){
        return '<div style="background:#111827;border:1px solid #1f2937;border-radius:12px;padding:11px 13px">'
          +'<div style="font-size:10px;color:#94a3b8;font-weight:700;letter-spacing:.04em;text-transform:uppercase;line-height:1.3">'+c[0]+'</div>'
          +'<div style="font-size:19px;font-weight:800;color:'+c[3]+';margin:5px 0 2px">'+c[1]+'</div>'
          +'<div style="font-size:10.5px;color:#64748b;line-height:1.35">'+c[2]+'</div></div>';
      }).join("");
    }

    function alertBox(){
      var a=agg(months()), gap=a.bep-a.rev, mo=months().length;
      var need=a.rev?((a.bep/a.rev-1)*100):0;
      var html;
      if(a.op<0){
        html='<b>Убыток '+mln(a.op)+'.</b> Чтобы выйти в ноль, при нынешней маржинальности '+pc(a.cmr)+' нужно либо поднять выручку на '+pc(need)+' ('+mln(gap/mo)+' в месяц), либо срезать постоянные затраты на '+mln(-a.op/mo)+' в месяц, либо поднять маржинальность на '+(-a.op/a.rev*100).toFixed(1).replace(".",",")+' пункта.';
      } else {
        html='<b>Прибыль '+mln(a.op)+'.</b> Запас прочности '+pc(a.safety)+': выручка может упасть на '+mln(a.rev-a.bep)+' до точки безубыточности.';
      }
      document.getElementById("fc-alert").innerHTML='<div style="background:'+(a.op<0?"rgba(239,68,68,.1)":"rgba(34,197,94,.1)")+';border:1px solid '+(a.op<0?"rgba(239,68,68,.32)":"rgba(34,197,94,.32)")+';border-radius:12px;padding:12px 15px;font-size:13px;color:#e2e8f0;line-height:1.65">'+html+'</div>';
    }

    function destroy(id){ var cv=document.getElementById(id); if(!cv||!window.Chart) return null; try{var e=Chart.getChart?Chart.getChart(cv):null; if(e)e.destroy();}catch(x){} return cv; }
    var AX={ticks:{color:"#64748b",font:{size:10}},grid:{color:"rgba(51,65,85,.35)"}};

    function ch1(){
      var cv=destroy("fc-ch1"); if(!cv) return; var ms=months();
      new Chart(cv.getContext("2d"),{data:{labels:ms.map(lbl),datasets:[
        {type:"bar",label:"Выручка",data:ms.map(function(m){return +(D.pl[m].rev/1e6).toFixed(1);}),backgroundColor:ms.map(function(m){return D.pl[m].op<0?"rgba(239,68,68,.55)":"rgba(34,197,94,.55)";}),borderRadius:5,order:3},
        {type:"line",label:"Точка безубыточности",data:ms.map(function(m){return +(D.pl[m].bep/1e6).toFixed(1);}),borderColor:"#c9a94e",backgroundColor:"#c9a94e",borderWidth:2.5,tension:.25,pointRadius:3,order:1},
        {type:"line",label:"Операционная прибыль",data:ms.map(function(m){return +(D.pl[m].op/1e6).toFixed(1);}),borderColor:"#38bdf8",backgroundColor:"#38bdf8",borderWidth:2,borderDash:[5,4],tension:.25,pointRadius:2,yAxisID:"y1",order:2}
      ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:"index",intersect:false},
        plugins:{legend:{labels:{color:"#cbd5e1",font:{size:11},boxWidth:12}},datalabels:{display:false},
          tooltip:{callbacks:{label:function(c){return c.dataset.label+": "+String(c.parsed.y).replace(".",",")+" млн";}}}},
        scales:{x:{ticks:{color:"#94a3b8",font:{size:11,weight:"600"}},grid:{display:false}},
          y:Object.assign({},AX,{title:{display:true,text:"млн ₸",color:"#475569",font:{size:10}}}),
          y1:{position:"right",ticks:{color:"#38bdf8",font:{size:10}},grid:{display:false}}}}});
    }

    function ch2(){
      var cv=destroy("fc-ch2"); if(!cv) return; var ms=months(), pctMode=st.mode==="pct";
      document.getElementById("fc-struct-sub").textContent=pctMode?"доли от выручки, %":"абсолютные суммы, млн ₸";
      var ds=D.layers.map(function(l){ return {label:l.t,backgroundColor:LC[l.k],borderRadius:3,
        data:ms.map(function(m){ var x=D.pl[m].layers[l.k]||0; return pctMode?+(x/D.pl[m].rev*100).toFixed(1):+(x/1e6).toFixed(1); })}; });
      if(pctMode) ds.push({label:"Результат",type:"line",borderColor:"#f8fafc",backgroundColor:"#f8fafc",borderWidth:2,pointRadius:2,tension:.25,
        data:ms.map(function(m){ return +(D.pl[m].op/D.pl[m].rev*100).toFixed(1); })});
      new Chart(cv.getContext("2d"),{type:"bar",data:{labels:ms.map(lbl),datasets:ds},
        options:{responsive:true,maintainAspectRatio:false,
          plugins:{legend:{labels:{color:"#cbd5e1",font:{size:10},boxWidth:10}},datalabels:{display:false},
            tooltip:{callbacks:{label:function(c){return c.dataset.label+": "+String(c.parsed.y).replace(".",",")+(pctMode?"%":" млн");}}}},
          scales:{x:{stacked:true,ticks:{color:"#94a3b8",font:{size:10}},grid:{display:false}},
            y:Object.assign({stacked:true},AX)}}});
    }

    function ch3(){
      var cv=destroy("fc-ch3"); if(!cv) return;
      var p=D.pl[st.month], f=(st.cmp==="yoy"?p.yoy:p.fx);
      var sub=document.getElementById("fc-fx-sub");
      if(!f){ sub.textContent="для этого месяца нет базы сравнения"; return; }
      var base=st.cmp==="yoy"?f.prev:D.months[D.months.indexOf(st.month)-1];
      sub.textContent=MN[+st.month.slice(5)]+" "+st.month.slice(0,4)+" против "+MN[+base.slice(5)]+" "+base.slice(0,4)+" · изменение прибыли "+sg(f.d);
      var steps=[["Было",D.pl[base].op,"#64748b",true],["Объём продаж",f.vol,f.vol>=0?"#22c55e":"#ef4444",false],
                 ["Маржинальность",f.mar,f.mar>=0?"#22c55e":"#ef4444",false],["Постоянные затраты",f.fix,f.fix>=0?"#22c55e":"#ef4444",false]];
      var labels=[],data=[],colors=[],cur=0;
      steps.forEach(function(s){ if(s[3]){ cur=s[1]; labels.push(s[0]); data.push([0,cur/1e6]); colors.push(s[2]); }
        else { var nx=cur+s[1]; labels.push(s[0]); data.push([cur/1e6,nx/1e6]); colors.push(s[2]); cur=nx; } });
      labels.push("Стало"); data.push([0,cur/1e6]); colors.push(cur<0?"#ef4444":"#22c55e");
      new Chart(cv.getContext("2d"),{type:"bar",data:{labels:labels,datasets:[{data:data,backgroundColor:colors,borderRadius:4,barPercentage:.7}]},
        options:{indexAxis:"y",responsive:true,maintainAspectRatio:false,
          plugins:{legend:{display:false},datalabels:{display:false},
            tooltip:{callbacks:{label:function(c){var v=c.raw;return " "+mln((v[1]-v[0])*1e6);}}}},
          scales:{x:Object.assign({},AX),y:{ticks:{color:"#cbd5e1",font:{size:11}},grid:{display:false}}}}});
    }

    function ch4(){
      var cv=destroy("fc-ch4"); if(!cv) return;
      var ms=D.cmonths.filter(function(m){ return st.period==="all"||m.indexOf(st.period)===0; });
      var names=Object.keys(D.chan).sort(function(a,b){ return sum(D.chan[b])-sum(D.chan[a]); }).slice(0,8);
      function sum(o){ var s=0; for(var k in o) s+=o[k]; return s; }
      var PAL=["#60a5fa","#f59e0b","#34d399","#a78bfa","#f472b6","#22d3ee","#fb923c","#94a3b8"];
      new Chart(cv.getContext("2d"),{type:"bar",data:{labels:ms.map(lbl),datasets:names.map(function(n,i){
        return {label:n.split(" ·")[0],backgroundColor:PAL[i%PAL.length],borderRadius:3,data:ms.map(function(m){return +((D.chan[n][m]||0)/1e6).toFixed(1);})};
      })},options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{color:"#cbd5e1",font:{size:9.5},boxWidth:9}},datalabels:{display:false},
          tooltip:{callbacks:{label:function(c){return c.dataset.label+": "+String(c.parsed.y).replace(".",",")+" млн";}}}},
        scales:{x:{stacked:true,ticks:{color:"#94a3b8",font:{size:9.5}},grid:{display:false}},y:Object.assign({stacked:true},AX)}}});
    }

    function ch5(){
      var cv=destroy("fc-ch5"); if(!cv) return;
      var cs=D.cats.slice(0,14);
      new Chart(cv.getContext("2d"),{data:{labels:cs.map(function(c){return c.n;}),datasets:[
        {type:"bar",label:"Выручка, млн",data:cs.map(function(c){return +(c.rev/1e6).toFixed(1);}),backgroundColor:"#334155",borderRadius:4,yAxisID:"y",order:3},
        {type:"bar",label:"Валовая прибыль, млн",data:cs.map(function(c){return +(c.gp/1e6).toFixed(1);}),backgroundColor:"#22c55e",borderRadius:4,yAxisID:"y",order:2},
        {type:"line",label:"Фудкост, %",data:cs.map(function(c){return c.fc;}),borderColor:"#c9a94e",backgroundColor:"#c9a94e",borderWidth:2,pointRadius:3,tension:.25,yAxisID:"y1",order:1}
      ]},options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{color:"#cbd5e1",font:{size:10},boxWidth:10}},datalabels:{display:false}},
        scales:{x:{ticks:{color:"#94a3b8",font:{size:10},maxRotation:40,minRotation:0},grid:{display:false}},
          y:Object.assign({},AX),y1:{position:"right",ticks:{color:"#c9a94e",font:{size:10},callback:function(v){return v+"%";}},grid:{display:false}}}}});
    }

    function momTable(){
      var ms=months();
      var h='<table style="width:100%;border-collapse:collapse;font-size:12.5px;min-width:820px">'
        +'<tr style="color:#64748b;font-size:10.5px;font-weight:800;text-align:right;text-transform:uppercase;letter-spacing:.04em">'
        +'<th style="text-align:left;padding:6px 4px">Месяц</th><th style="padding:6px 4px">Выручка</th><th style="padding:6px 4px">Δ выручки</th>'
        +'<th style="padding:6px 4px">Маржин.</th><th style="padding:6px 4px">Δ маржин.</th><th style="padding:6px 4px">Постоянные</th>'
        +'<th style="padding:6px 4px">Δ постоян.</th><th style="padding:6px 4px">Результат</th><th style="padding:6px 4px">Δ результата</th><th style="padding:6px 4px">Запас</th></tr>';
      ms.forEach(function(m,i){
        var p=D.pl[m], base=(st.cmp==="yoy"?(p.yoy?p.yoy.prev:null):(D.months[D.months.indexOf(m)-1]||null));
        var b=base?D.pl[base]:null;
        var dr=b?(p.rev-b.rev)/b.rev*100:null, dm=b?(p.cmr-b.cmr):null, df=b?(p.fix-b.fix)/b.fix*100:null, dop=b?(p.op-b.op):null;
        function cell(v,txt,inv){ var c=v==null?"#64748b":((inv?-v:v)>0?"#22c55e":((inv?-v:v)<0?"#ef4444":"#94a3b8"));
          return '<td style="padding:6px 4px;text-align:right;white-space:nowrap;color:'+c+';font-weight:700">'+txt+'</td>'; }
        h+='<tr data-m="'+m+'" style="border-top:1px solid #1b2636;cursor:pointer;background:'+(m===st.month?"rgba(201,169,78,.09)":"transparent")+'">'
          +'<td style="padding:6px 4px;color:#e2e8f0;font-weight:700">'+MS[+m.slice(5)]+" "+m.slice(0,4)+'</td>'
          +'<td style="padding:6px 4px;text-align:right;color:#cbd5e1">'+mln(p.rev)+'</td>'
          +cell(dr,dr==null?"—":pc(dr))
          +'<td style="padding:6px 4px;text-align:right;color:#22d3ee;font-weight:700">'+pc(p.cmr)+'</td>'
          +cell(dm,dm==null?"—":((dm>0?"+":"")+dm.toFixed(1).replace(".",",")+" пп"))
          +'<td style="padding:6px 4px;text-align:right;color:#f59e0b">'+mln(p.fix)+'</td>'
          +cell(df,df==null?"—":pc(df),true)
          +'<td style="padding:6px 4px;text-align:right;font-weight:800;color:'+(p.op<0?"#ef4444":"#22c55e")+'">'+mln(p.op)+'</td>'
          +cell(dop,dop==null?"—":sg(dop))
          +'<td style="padding:6px 4px;text-align:right;color:'+(p.safety<0?"#ef4444":"#22c55e")+'">'+pc(p.safety)+'</td></tr>';
      });
      var el=document.getElementById("fc-mom"); el.innerHTML=h+'</table>';
      el.onclick=function(e){ var tr=e.target.closest("tr[data-m]"); if(!tr) return; st.month=tr.getAttribute("data-m"); render(); };
    }

    function linesTable(){
      var m=st.month, base=(st.cmp==="yoy"?(D.pl[m].yoy?D.pl[m].yoy.prev:null):(D.months[D.months.indexOf(m)-1]||null));
      var rows=D.lines.map(function(l){ var cur=l.m[m]||0, prv=base?(l.m[base]||0):0;
        return {n:l.n,g:l.g,cur:cur,prv:prv,d:cur-prv,dp:prv?((cur-prv)/Math.abs(prv)*100):null}; })
        .filter(function(r){ return Math.abs(r.cur)>300000||Math.abs(r.d)>300000; });
      rows.sort(function(a,b){ return Math.abs(b.d)-Math.abs(a.d); });
      var h='<div style="font-size:11.5px;color:#64748b;margin-bottom:6px">'+MN[+m.slice(5)]+" "+m.slice(0,4)+(base?(" против "+MN[+base.slice(5)]+" "+base.slice(0,4)):"")+'</div>'
        +'<table style="width:100%;border-collapse:collapse;font-size:12px;min-width:380px">';
      rows.slice(0,14).forEach(function(r){
        h+='<tr style="border-top:1px solid #1b2636">'
          +'<td style="padding:5px 4px;color:#cbd5e1;max-width:210px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(r.n.replace(/^\d+(\.\d+)*\./,""))+' <span style="color:#475569;font-size:10px">'+r.g+'</span></td>'
          +'<td style="padding:5px 4px;text-align:right;color:#94a3b8;white-space:nowrap">'+mln(r.cur)+'</td>'
          +'<td style="padding:5px 4px;text-align:right;font-weight:700;white-space:nowrap;color:'+(r.d>0?"#ef4444":"#22c55e")+'">'+sg(r.d)+'</td></tr>';
      });
      document.getElementById("fc-lines").innerHTML=h+'</table>';
    }

    function chanTable(){
      var ms=D.cmonths.filter(function(m){ return st.period==="all"||m.indexOf(st.period)===0; });
      var last=ms[ms.length-1], prev=ms[ms.length-2];
      var rows=Object.keys(D.chan).map(function(n){
        var tot=0; ms.forEach(function(m){ tot+=D.chan[n][m]||0; });
        var a=D.chan[n][last]||0, b=prev?(D.chan[n][prev]||0):0;
        return {n:n,t:tot,a:a,d:a-b,dp:b?((a-b)/b*100):null};
      }).filter(function(r){ return r.t>0; });
      rows.sort(function(x,y){ return y.t-x.t; });
      var tot=rows.reduce(function(s,r){return s+r.t;},0);
      var h='<div style="font-size:11.5px;color:#64748b;margin:6px 0">последний месяц в данных — '+MN[+last.slice(5)]+" "+last.slice(0,4)+'</div>'
        +'<table style="width:100%;border-collapse:collapse;font-size:12px;min-width:380px">';
      rows.slice(0,10).forEach(function(r){
        h+='<tr style="border-top:1px solid #1b2636">'
          +'<td style="padding:5px 4px;color:#cbd5e1;max-width:190px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(r.n)+'</td>'
          +'<td style="padding:5px 4px;text-align:right;color:#94a3b8">'+mln(r.t)+'</td>'
          +'<td style="padding:5px 4px;text-align:right;color:#64748b">'+pc(r.t/tot*100,0)+'</td>'
          +'<td style="padding:5px 4px;text-align:right;font-weight:700;white-space:nowrap;color:'+(r.d>0?"#22c55e":(r.d<0?"#ef4444":"#64748b"))+'">'+sg(r.d)+'</td></tr>';
      });
      document.getElementById("fc-chan").innerHTML=h+'</table>';
    }
    __MODAL__

    function render(){
      seg("fc-period",[["all","Весь период"],["2025","2025"],["2026","2026"]],st.period,function(v){ st.period=v;
        var ms=months(); if(ms.indexOf(st.month)<0) st.month=ms[ms.length-1]; render(); });
      seg("fc-mode",[["abs","₸"],["pct","% от выручки"]],st.mode,function(v){ st.mode=v; render(); });
      seg("fc-cmp",[["mom","к прошлому месяцу"],["yoy","к прошлому году"]],st.cmp,function(v){ st.cmp=v; render(); });
      var sel=document.getElementById("fc-month");
      sel.innerHTML=months().map(function(m){ return '<option value="'+m+'"'+(m===st.month?" selected":"")+'>'+MN[+m.slice(5)]+" "+m.slice(0,4)+'</option>'; }).join("");
      sel.onchange=function(){ st.month=this.value; render(); };
      kpi(); alertBox(); momTable(); linesTable(); chanTable();
      if(window.Chart){ ch1(); ch2(); ch3(); ch4(); ch5(); }
    }

    function boot(){
      var a=agg(D.months);
      document.getElementById("fc-sum").textContent="выручка "+mln(a.rev)+" · результат "+mln(a.op)+" · "+D.months.length+" мес.";
      var det=document.getElementById("fc-details");
      det.addEventListener("toggle",function(){ var c=document.getElementById("fc-caret"); if(c) c.innerHTML=det.open?"&#9662;":"&#9656;"; if(det.open) render(); });
      document.getElementById("fc-open").onclick=function(){ openModal(); };
      document.getElementById("fc-close").onclick=function(){ document.getElementById("fc-modal").style.display="none"; document.body.style.overflow=""; };
      document.getElementById("fc-modal").onclick=function(e){ if(e.target===this){ this.style.display="none"; document.body.style.overflow=""; } };
      if(det.open) render();
    }
    if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",boot); else boot();
  })();
  </script>
</div>
'''


MODAL_JS = r'''
    function openModal(){
      var ms=months(), a=agg(ms), n=ms.length;
      var y25=D.years["2025"], y26=D.years["2026"];
      var cmp=null;
      if(y26){
        var same=y26.months.map(function(m){ return "2025"+m.slice(4); }).filter(function(m){ return D.pl[m]; });
        if(same.length===y26.months.length){ cmp={a:agg(same),b:agg(y26.months),ms:same,ms2:y26.months}; }
      }
      var sorted=ms.slice().sort(function(x,y){ return D.pl[y].op-D.pl[x].op; });
      var best=sorted[0], worst=sorted[sorted.length-1];
      var revS=ms.slice().sort(function(x,y){ return D.pl[y].rev-D.pl[x].rev; });
      var LOSS=["1.30.Возвраты от дистрибьютеров","1.28.Брак","1.7.Истек срок хранения (порча)","1.3.Недостача инвентаризации","1.24.Бракераж","1.27.Нарушение тех.процесса","1.11.Списание сломанных ТМЗ"];
      function lineSum(name,mm){ var l=null; D.lines.forEach(function(x){ if(x.n===name) l=x; }); if(!l) return 0;
        var s=0; mm.forEach(function(m){ s+=l.m[m]||0; }); return s; }
      var lossTot=0; LOSS.forEach(function(k){ lossTot+=lineSum(k,ms); });

      var chanMs=D.cmonths.filter(function(m){ return st.period==="all"||m.indexOf(st.period)===0; });
      var chRows=Object.keys(D.chan).map(function(nm){
        var t=0; chanMs.forEach(function(m){ t+=D.chan[nm][m]||0; });
        var last3=chanMs.slice(-3).reduce(function(s,m){ return s+(D.chan[nm][m]||0); },0)/Math.max(1,Math.min(3,chanMs.length));
        var first3=chanMs.slice(0,3).reduce(function(s,m){ return s+(D.chan[nm][m]||0); },0)/Math.max(1,Math.min(3,chanMs.length));
        return {n:nm,t:t,last:last3,first:first3,d:last3-first3};
      }).sort(function(x,y){ return y.t-x.t; });
      var gone=chRows.filter(function(r){ return r.first>5e6 && r.last<r.first*0.2; }).sort(function(x,y){ return x.d-y.d; });
      var grown=chRows.filter(function(r){ return r.d>3e6; }).sort(function(x,y){ return y.d-x.d; });

      var deficit=-a.op, perMonth=deficit/n;
      var needRev=a.cmr>0?(deficit/(a.cmr/100)):0;

      function H(t){ return '<div style="font-size:11px;font-weight:800;color:#c9a94e;letter-spacing:.09em;text-transform:uppercase;margin:22px 0 8px;padding-bottom:6px;border-bottom:1px solid #1f2937">'+t+'</div>'; }
      function P(t){ return '<p style="margin:0 0 9px;font-size:13px;line-height:1.72;color:#cbd5e1">'+t+'</p>'; }
      function KV(rows){
        return '<table style="width:100%;border-collapse:collapse;font-size:12.5px;margin:4px 0 10px">'+rows.map(function(r){
          return '<tr style="border-bottom:1px solid #16202f"><td style="padding:6px 2px;color:#94a3b8">'+r[0]+'</td>'
            +'<td style="padding:6px 2px;text-align:right;font-weight:700;color:'+(r[2]||"#e2e8f0")+';white-space:nowrap;font-variant-numeric:tabular-nums">'+r[1]+'</td></tr>';
        }).join("")+'</table>';
      }
      function LI(items){ return '<ol style="margin:2px 0 10px;padding-left:20px;font-size:13px;line-height:1.75;color:#cbd5e1">'+items.map(function(t){ return '<li style="margin-bottom:6px">'+t+'</li>'; }).join("")+'</ol>'; }
      function b(t){ return '<b style="color:#f1f5f9">'+t+'</b>'; }

      var h="";
      h+=H("1 · Резюме");
      h+=P("За "+n+" мес. выручка "+b(mln(a.rev))+", полная себестоимость "+b(mln(a.full))+", результат "+b(mln(a.op))+" ("+pc(a.op/a.rev*100)+" к выручке). На каждые 100 ₸ выручки приходится "+b(Math.round(a.full/a.rev*100)+" ₸")+" затрат.");
      h+=KV([["Выручка",mln(a.rev)],["Переменные затраты",mln(a.var_),"#fb923c"],["Маржинальная прибыль",mln(a.cm)+" · "+pc(a.cmr),"#22d3ee"],
             ["Постоянные затраты",mln(a.fix),"#f59e0b"],["Операционный результат",mln(a.op),a.op<0?"#ef4444":"#22c55e"],
             ["Точка безубыточности, в месяц",mln(a.bep/n),"#a78bfa"],["Фактическая выручка, в месяц",mln(a.rev/n)],
             ["Запас прочности",pc(a.safety),a.safety<0?"#ef4444":"#22c55e"]]);

      h+=H("2 · Выручка");
      h+=P("Лучший месяц по выручке — "+b(MN[+revS[0].slice(5)]+" "+revS[0].slice(0,4))+" ("+mln(D.pl[revS[0]].rev)+"), худший — "+b(MN[+revS[revS.length-1].slice(5)]+" "+revS[revS.length-1].slice(0,4))+" ("+mln(D.pl[revS[revS.length-1]].rev)+"). Разброс "+mln(D.pl[revS[0]].rev-D.pl[revS[revS.length-1]].rev)+" — это "+pc((D.pl[revS[0]].rev/D.pl[revS[revS.length-1]].rev-1)*100)+" к минимуму.");
      if(cmp){
        var dr=(cmp.b.rev-cmp.a.rev)/cmp.a.rev*100;
        h+=P("Сопоставимый период "+b(MN[+cmp.ms2[0].slice(5)]+"–"+MN[+cmp.ms2[cmp.ms2.length-1].slice(5)])+": 2026 год дал "+b(mln(cmp.b.rev))+" против "+mln(cmp.a.rev)+" в 2025 — "+b(pc(dr))+" ("+sg(cmp.b.rev-cmp.a.rev)+")."
          +(dr<0?" Провал выручки и есть основная причина убытка."
                :" То есть выручка год к году не упала — значит результат ухудшили не продажи, а маржинальность и постоянные затраты."));
        var h2=D.months.filter(function(m){ return m.indexOf("2025")===0 && +m.slice(5)>=7; });
        if(h2.length){
          var a2=agg(h2), am2=a2.rev/h2.length, am26=cmp.b.rev/cmp.ms2.length;
          h+=P("Но если сравнивать со вторым полугодием 2025 ("+b(mln(am2)+" в месяц")+"), то текущий уровень "+b(mln(am26)+" в месяц")+" — это "+b(pc((am26/am2-1)*100))+", то есть "+b(mln(Math.abs(am2-am26))+" выручки в месяц")+", которых не хватает при неизменных постоянных затратах.");
        }
      }
      h+=P("Прибыльных месяцев "+b(ms.filter(function(m){return D.pl[m].op>0;}).length+" из "+n)+". Лучший результат — "+b(MN[+best.slice(5)]+" "+best.slice(0,4)+": "+mln(D.pl[best].op))+", худший — "+b(MN[+worst.slice(5)]+" "+worst.slice(0,4)+": "+mln(D.pl[worst].op))+".");

      h+=H("3 · Маржинальность: сколько остаётся после переменных затрат");
      h+=P("Средняя маржинальность периода — "+b(pc(a.cmr))+". Это доля выручки, которая доходит до покрытия постоянных затрат. Каждый процентный пункт маржинальности стоит "+b(mln(a.rev/n/100))+" в месяц.");
      if(cmp){
        var dm=cmp.b.cmr-cmp.a.cmr;
        h+=P("В сопоставимом периоде маржинальность "+(dm<0?"упала":"выросла")+" с "+b(pc(cmp.a.cmr))+" до "+b(pc(cmp.b.cmr))+" — это "+b((dm>0?"+":"")+dm.toFixed(1).replace(".",",")+" пункта")+", или "+b(sg(cmp.b.rev*dm/100))+" результата на нынешних объёмах.");
      }
      var fl=[]; D.layers.forEach(function(l){ fl.push([l.t,mln(a.layers[l.k])+" · "+pc(a.layers[l.k]/a.rev*100),LC[l.k]]); });
      h+=P("Структура полной себестоимости за период:");
      h+=KV(fl);

      h+=H("4 · Постоянные затраты");
      h+=P("Постоянные затраты — "+b(mln(a.fix))+" за период, в среднем "+b(mln(a.fix/n))+" в месяц. Они не зависят от объёма продаж, поэтому при падении выручки бьют по результату напрямую.");
      if(cmp){
        var nb=cmp.ms2.length, na=cmp.ms.length;
        var df=cmp.b.fix/nb-cmp.a.fix/na;
        h+=P("В сопоставимом периоде постоянные "+(df>0?"выросли":"снизились")+" на "+b(mln(Math.abs(df))+" в месяц")+" ("+pc((cmp.b.fix/nb)/(cmp.a.fix/na)*100-100)+"). Это "+b(mln(df*nb))+" за период.");
      }

      h+=H("5 · Точка безубыточности");
      h+=P("При маржинальности "+b(pc(a.cmr))+" для покрытия постоянных затрат нужна выручка "+b(mln(a.bep/n)+" в месяц")+". Фактическая — "+b(mln(a.rev/n))+". Разрыв "+b(mln(Math.abs(a.bep/n-a.rev/n)))+" в месяц"+(a.op<0?" — это и есть месячный убыток в пересчёте на выручку.":"."));
      var bepRows=ms.slice(-6).map(function(m){ var p=D.pl[m];
        return [MN[+m.slice(5)]+" "+m.slice(0,4), mln(p.rev)+" при пороге "+mln(p.bep)+" · "+pc(p.safety), p.safety<0?"#ef4444":"#22c55e"]; });
      h+=KV(bepRows);

      h+=H("6 · Каналы продаж: кто ушёл и кто пришёл");
      if(gone.length){
        h+=P(b("Потерянные каналы.")+" Сравнение первых и последних трёх месяцев данных:");
        h+=LI(gone.slice(0,4).map(function(r){ return b(r.n)+" — было "+mln(r.first)+" в месяц, стало "+mln(r.last)+". Потеря "+b(mln(r.d))+" выручки ежемесячно."; }));
      }
      if(grown.length){
        h+=P(b("Выросшие каналы:"));
        h+=LI(grown.slice(0,4).map(function(r){ return b(r.n)+" — с "+mln(r.first)+" до "+mln(r.last)+" в месяц, "+b(sg(r.d))+"."; }));
      }
      var netCh=(grown.reduce(function(s,r){return s+r.d;},0))+(gone.reduce(function(s,r){return s+r.d;},0));
      h+=P("Нетто-эффект по каналам: "+b(sg(netCh)+" выручки в месяц")+". При маржинальности "+pc(a.cmr)+" это "+b(sg(netCh*a.cmr/100))+" результата ежемесячно — "+(netCh<0?"ровно та дыра, которую нечем закрыть при неизменных постоянных затратах.":"вклад в прибыль."));
      var top=chRows.slice(0,5);
      h+=KV(top.map(function(r){ return [r.n, mln(r.t)+" · "+pc(r.t/chRows.reduce(function(s,x){return s+x.t;},0)*100,0)]; }));
      h+=P("Концентрация: три крупнейших канала дают "+b(pc(top.slice(0,3).reduce(function(s,r){return s+r.t;},0)/chRows.reduce(function(s,x){return s+x.t;},0)*100))+" всей выручки. Уход любого из них повторит сценарий текущего года.");

      h+=H("7 · Продукт и фудкост");
      if(D.cats.length){
        var cs=D.cats.slice(0,10);
        var bestC=cs.slice().sort(function(x,y){ return x.fc-y.fc; })[0];
        var worstC=cs.slice().sort(function(x,y){ return y.fc-x.fc; })[0];
        h+=P("Средний фудкост по категориям с заполненной себестоимостью — "+b(pc(cs.reduce(function(s,c){return s+c.cost;},0)/cs.reduce(function(s,c){return s+c.rev;},0)*100))+". Самая выгодная категория — "+b(bestC.n+" ("+pc(bestC.fc)+")")+", самая тяжёлая — "+b(worstC.n+" ("+pc(worstC.fc)+")")+".");
        h+=KV(cs.map(function(c){ return [c.n, mln(c.rev)+" выручки · фудкост "+pc(c.fc)+" · вал. прибыль "+mln(c.gp), c.fc>55?"#ef4444":(c.fc<45?"#22c55e":"#e2e8f0")]; }));
        h+=P("Категории с фудкостом выше 55% при полной себестоимости завода около "+pc(a.full/a.rev*100)+" не окупают даже производство — по ним нужен либо пересмотр цены, либо вывод из матрицы.");
      } else { h+=P("Данные по категориям недоступны."); }

      h+=H("8 · Потери внутри себестоимости");
      h+=P("Сумма статей потерь за период — "+b(mln(lossTot))+", это "+b(pc(lossTot/a.rev*100))+" выручки и "+b(pc(lossTot/Math.max(1,Math.abs(a.op))*100,0))+" от абсолютной величины результата.");
      h+=KV(LOSS.map(function(k){ var s=lineSum(k,ms); return [k.replace(/^\d+(\.\d+)*\./,""), mln(s)+" · "+pc(s/a.rev*100,2), s>a.rev*0.005?"#ef4444":"#e2e8f0"]; }));

      h+=H("9 · За счёт чего прибыль и за счёт чего убыток");
      h+=LI([
        b("Прибыль дают:")+" маржинальность "+pc(a.cmr)+" — каждый тенге выручки приносит "+b(Math.round(a.cmr)+" тиын")+" на покрытие постоянных затрат; объём в сильные месяцы (в лучшем месяце результат "+mln(D.pl[best].op)+"); каналы с растущим объёмом"+(grown.length?" — прежде всего "+grown[0].n:"")+".",
        b("Убыток создают:")+" падение выручки ниже порога "+mln(a.bep/n)+" в месяц; постоянные затраты "+mln(a.fix/n)+" в месяц, не сокращённые вслед за объёмом; потери в себестоимости "+mln(lossTot)+"; концентрация на нескольких крупных покупателях.",
        (function(){ var lv=a.rev/n*0.01*a.cmr/100, lf=a.fix/n*0.01, k=lv/lf;
          return b("Главный рычаг:")+" при нынешней структуре "+b("+1% выручки")+" даёт "+b(mln(lv))+" результата в месяц, а "+b("−1% постоянных затрат")+" — "+b(mln(lf))+". "
            +(k>1.15?("Наращивать объём примерно в "+b(k.toFixed(1).replace(".",",")+" раза")+" эффективнее, чем резать постоянные на тот же процент.")
              :(k<0.87?("Сокращать постоянные примерно в "+b((1/k).toFixed(1).replace(".",",")+" раза")+" эффективнее, чем наращивать объём на тот же процент.")
                :"Оба рычага дают почти одинаковый эффект, поэтому работать нужно с обоими сразу."));
        })()
      ]);

      h+=H("10 · Сценарии выхода в ноль");
      if(a.op<0){
        h+=LI([
          "Только за счёт объёма: нужно "+b("+"+mln(needRev/n)+" выручки в месяц")+" ("+b(pc(needRev/a.rev*100))+" к текущей) при сохранении маржинальности и постоянных.",
          "Только за счёт постоянных: сократить их на "+b(mln(perMonth)+" в месяц")+" ("+b(pc(perMonth/(a.fix/n)*100))+" от нынешних "+mln(a.fix/n)+").",
          "Только за счёт маржинальности: поднять её на "+b((deficit/a.rev*100).toFixed(1).replace(".",",")+" пункта")+" — с "+pc(a.cmr)+" до "+b(pc(a.cmr+deficit/a.rev*100))+". Это либо цена, либо фудкост, либо сокращение потерь.",
          "Комбинация, наиболее реалистичная: половина разрыва объёмом (+"+mln(needRev/n/2)+" выручки), четверть — маржинальностью (+"+(deficit/a.rev*100/4).toFixed(1).replace(".",",")+" пункта), четверть — постоянными (−"+mln(perMonth/4)+" в месяц)."
        ]);
      } else {
        h+=P("Период прибыльный. Запас прочности "+b(pc(a.safety))+": выручка может упасть на "+b(mln(a.rev-a.bep))+" до точки безубыточности.");
      }

      h+=H("11 · Методика и ограничения");
      h+=P("Данные — управленческий ОПиУ ("+D.months.length+" мес., "+MN[+D.months[0].slice(5)]+" "+D.months[0].slice(0,4)+" — "+MN[+D.months[D.months.length-1].slice(5)]+" "+D.months[D.months.length-1].slice(0,4)+") и отчёт о продажах по контрагентам из iiko. Переменными считаются статьи, зависящие от объёма: продуктовая себестоимость, расходные материалы, логистика, потери, электроэнергия. Постоянными — ФОТ производства и АУП, аренда, администрация, маркетинг, ремонты. Деление условное: часть статей полупеременные, поэтому точка безубыточности — ориентир, а не бухгалтерская величина. Выручка по каналам берётся по расходным накладным и может незначительно расходиться с ОПиУ из-за возвратов и внутренних перемещений. Прочие доходы и КПН в операционный результат не включены.");
      h+=P('<span style="color:#475569;font-size:11.5px">Собрано '+D.built+' · система «Пульс» · Ольга Герасименко</span>');

      document.getElementById("fc-modal-body").innerHTML=h;
      document.getElementById("fc-modal-sub").textContent=(st.period==="all"?"весь период":st.period)+" · "+n+" мес. · выручка "+mln(a.rev)+" · результат "+mln(a.op);
      document.getElementById("fc-modal").style.display="block";
      document.body.style.overflow="hidden";
    }
'''


def inject(html, data):
    block = SECTION.replace("__MODAL__", MODAL_JS).replace(
        "__FCDATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    i = html.find('<div id="fullcost-analytics"')
    if i >= 0:
        j = html.find("</body>", i)
        html = html[:i] + (html[j:] if j > 0 else "")
    k = html.find("</body>")
    if k >= 0:
        return html[:k] + block + "\n" + html[k:]
    return html + block


def main():
    data = build()
    p = os.path.join(HERE, TARGET)
    html = open(p, encoding="utf-8").read()
    open(p, "w", encoding="utf-8").write(inject(html, data))
    a = data["years"]
    tot_rev = sum(data["pl"][m]["rev"] for m in data["months"])
    tot_op = sum(data["pl"][m]["op"] for m in data["months"])
    print("Полная себестоимость: %d мес., выручка %.1f млн, результат %.1f млн, каналов %d, категорий %d"
          % (len(data["months"]), tot_rev / 1e6, tot_op / 1e6, len(data["chan"]), len(data["cats"])))


if __name__ == "__main__":
    main()
