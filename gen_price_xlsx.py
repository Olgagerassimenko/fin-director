# -*- coding: utf-8 -*-
"""
gen_price_xlsx.py — рабочая книга Excel «План повышения цен».

Зачем отдельный файл, а не выгрузка со страницы. На странице считает браузер,
и выгрузить он может только то, что уже посчитал: мёртвые числа. В переговорах
с клиентом нужно другое — открыть файл, поставить свой процент и сразу увидеть,
что будет с прибылью. Поэтому книга собирается здесь и уходит на сайт готовой,
а внутри неё живут формулы Excel: меняешь процент в колонке — пересчитывается
новая цена, прирост выручки, прирост валовой прибыли и запас по объёму.

Что внутри:
  «План»          — таблица по позициям с формулами и итогами. Сверху две
                    настройки: реакция объёма на цену и ориентир роста цены.
  «Цены по месяцам» — помесячная цена и количество по каждой позиции плюс
                    отдельный график на каждую: видно, стоит цена или растёт.
  «Методика»      — как считались рекомендация и эффект.

Данные берутся из contractor_items.js (что и почём забрал каждый контрагент по
месяцам) и sku_margin.js (маржа и категория позиции) — тех же файлов, на
которых работает страница «Повышение цен», так что цифры совпадают.

Запускается в пайплайне после gen_sku_margin.py.
"""
import os, re, json, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import almaty  # время завода — Алматы (UTC+5), не UTC раннера

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import LineChart, Reference
from openpyxl.chart.axis import ChartLines
from openpyxl.worksheet.table import Table, TableStyleInfo

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "план_повышения_цен.xlsx")

TOP = 20                 # сколько позиций берём
MONTHS = 3               # окно для выручки и цены
TARGET_PER_YEAR = 8.0    # ориентир роста цены за год, %
STEP_CAP = 8.0           # максимум за один шаг, %
MARGIN_DEFAULT = 51.0
ELASTICITY = -0.8        # сколько процентов объёма уходит на 1% цены

MO = {'01': 'янв', '02': 'фев', '03': 'мар', '04': 'апр', '05': 'май', '06': 'июн',
      '07': 'июл', '08': 'авг', '09': 'сен', '10': 'окт', '11': 'ноя', '12': 'дек'}

# ── палитра, та же что на дашбордах ───────────────────────────────────────
INK = "1F2937"
NAVY = "13233F"
GOLD = "B8860B"
GREY = "6B7280"
LINE = "D6DCE6"

thin = Side(style="thin", color=LINE)
BORD = Border(left=thin, right=thin, top=thin, bottom=thin)


def load(fn, var):
    txt = open(os.path.join(HERE, fn), encoding="utf-8").read()
    m = (re.search(r"window\." + var + r"\s*=\s*(\{.*?\});\s*\n", txt, re.S)
         or re.search(r"window\." + var + r"\s*=\s*(\{.*\});", txt, re.S))
    if not m:
        raise SystemExit(fn + " не разобрался")
    return json.loads(m.group(1))


def short(s):
    """Базовое имя позиции.

    «RP*» — та же позиция под другой карточкой iiko: под этим именем её берёт
    сеть АЗС. Считать карточки порознь нельзя: один товар распадается на две
    строки с разной историей цены, и в ТОП-20 попадают обе половинки. Сводим
    к базовому имени. «Сырая» и «готовая» — разные товары, регулярка их не
    трогает.
    """
    s = re.sub(r"^RP\*\s*", "", str(s or ""))
    s = re.sub(r"^Упак\s+", "", s, flags=re.I)
    s = re.sub(r"\s+готов(ый)?\s+(ФЗ\s+СМ|СМ|ФЗ)\s*", " ", s, flags=re.I)
    return re.sub(r"\s{2,}", " ", s).strip()


def key(s):
    return short(s).lower()


def median(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def collect():
    """Помесячно складываем позиции по всем клиентам: количество и сумма."""
    CTR = load("contractor_items.js", "CTR")
    MG = load("sku_margin.js", "SKU_MARGIN")
    months = sorted(k for k in CTR if re.match(r"^\d{4}-\d{2}$", k))
    full = months[:-1]          # последний месяц незакрытый, себестоимость не разнесена
    bym, cards = {}, {}
    for m in full:
        a = {}
        for c in CTR[m]:
            for it in c.get("items", []):
                q = abs(it.get("q") or 0)
                r = it.get("r") or 0
                if q <= 0 or r <= 0:
                    continue
                k = key(it["n"])
                t = a.setdefault(k, {"q": 0, "r": 0})
                t["q"] += q
                t["r"] += r
                cards.setdefault(k, {})
                cards[k][it["n"]] = cards[k].get(it["n"], 0) + r
        bym[m] = a
    # маржа приходит по карточкам — сводим её к базовым именам, взвешивая выручкой
    mgb = {}
    for n, g in MG.items():
        k = key(n)
        x = mgb.setdefault(k, {"r": 0.0, "vp": 0.0, "c": ""})
        x["r"] += g.get("r") or 0
        x["vp"] += (g.get("r") or 0) * (g.get("m") or 0) / 100.0
        if not x["c"] and g.get("c"):
            x["c"] = g["c"]
    for k, x in mgb.items():
        x["m"] = x["vp"] / x["r"] * 100 if x["r"] else MARGIN_DEFAULT
    return bym, full, mgb, cards


def build():
    bym, full, MG, cards = collect()
    per = full[-MONTHS:]
    agg = {}
    for m in per:
        for n, t in bym[m].items():
            s = agg.setdefault(n, {"q": 0, "r": 0})
            s["q"] += t["q"]
            s["r"] += t["r"]

    rows = []
    for n, t in sorted(agg.items(), key=lambda kv: -kv[1]["r"])[:TOP]:
        ser, qs = [], []
        for m in full:
            x = bym[m].get(n)
            ser.append(x["r"] / x["q"] if x and x["q"] > 0 else None)
            qs.append(x["q"] if x else 0)
        # Месяцы, где позицию брали единицами, из сравнения цен выбрасываем:
        # это пробные партии по розничной цене, они выглядели бы обвалом цены.
        qmed = median([q for q in qs if q > 0]) or 0
        known = [i for i, x in enumerate(ser) if x is not None and qs[i] >= qmed * 0.25]
        win = known[-9:]
        nh = max(1, min(3, len(win) // 2))
        p_new = median([ser[i] for i in win[-nh:]])
        p_old = median([ser[i] for i in win[:nh]])
        yoy = (p_new / p_old - 1) * 100 if (p_old and p_new and len(win) >= 4) else None
        s2 = sum(qs[-3:]) / 3.0
        s1 = sum(qs[-6:-3]) / 3.0
        trend = (s2 / s1 - 1) * 100 if s1 > 0 else None
        g = MG.get(n)
        vs = sorted(cards.get(n, {}).items(), key=lambda kv: -kv[1])
        rows.append({
            "n": n, "name": short(vs[0][0]) if vs else n, "cat": (g or {}).get("c", ""),
            "cards": [v[0] for v in vs],
            "rev": t["r"] / len(per), "qty": t["q"] / len(per), "price": t["r"] / t["q"],
            "ser": ser, "qs": qs, "yoy": yoy, "ym": len(win), "trend": trend,
            "mg": g["m"] if g else MARGIN_DEFAULT,
        })

    for r in rows:
        r["rec"], r["need"], r["why"] = recommend(r)
    return rows, full


def recommend(r):
    """Ориентир — рост цены на инфляцию. Отставание и есть база подъёма."""
    tgt = TARGET_PER_YEAR / 12 * (r["ym"] or 6)
    if r["yoy"] is not None and r["yoy"] >= tgt + 3:
        return 0.0, 0.0, "цену уже подняли на %.1f%% — этого хватает" % r["yoy"]
    v, why = 0.0, []
    if r["yoy"] is not None:
        v = min(10.0, max(0.0, tgt - r["yoy"]))
        if v > 0:
            why.append("за %d мес цена %s при ориентире %.1f%%"
                       % (r["ym"],
                          ("упала на %.1f%%" % -r["yoy"]) if r["yoy"] < 0
                          else ("выросла на %.1f%%" % r["yoy"]), tgt))
    if r["mg"] < 45:
        v += 3
        why.append("маржа %.0f%% — тоньше заводской" % r["mg"])
    if r["trend"] is not None and r["trend"] > 30:
        v += 1.5
        why.append("берут на %.0f%% больше" % r["trend"])
    if r["trend"] is not None and r["trend"] < -15:
        v = min(v, 2)
        why = ["объём падает на %.0f%% — только символический шаг" % -r["trend"]]
    need = min(15.0, round(v * 2) / 2)
    return min(STEP_CAP, need), need, "; ".join(why) or "признаков отставания цены нет"


# ── оформление ────────────────────────────────────────────────────────────
def title(ws, row, text, sub=""):
    ws.cell(row=row, column=1, value=text).font = Font(bold=True, size=15, color=NAVY)
    if sub:
        ws.cell(row=row + 1, column=1, value=sub).font = Font(size=10, color=GREY, italic=True)


def head_row(ws, row, cols):
    fill = PatternFill("solid", fgColor=NAVY)
    for i, (t, w) in enumerate(cols, start=1):
        c = ws.cell(row=row, column=i, value=t)
        c.font = Font(bold=True, size=9.5, color="FFFFFF")
        c.fill = fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORD
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 34


def waves(rows):
    """Очередь: сначала три позиции, где денег больше всего, потом остальные."""
    def eff(r):
        m, P = r["mg"] / 100.0, r["rec"] / 100.0
        k = max(0.0, 1 + ELASTICITY * P)
        return r["rev"] * k * (m + P) - r["rev"] * m
    live = sorted([r for r in rows if r["rec"] > 0], key=lambda r: -eff(r))
    for i, r in enumerate(live):
        r["wave"] = "1 — сейчас" if i < 3 else "2 — следом"
        if r["need"] > r["rec"]:
            r["wave"] += " + 2-й шаг"
        r["dvp"] = eff(r)
    for r in rows:
        if r["rec"] <= 0:
            r["wave"] = "— не трогать"
            r["dvp"] = 0.0


def sheet_plan(wb, rows, built):
    ws = wb.create_sheet("План")
    ws.sheet_view.showGridLines = False
    title(ws, 1, "План повышения цен · ТОП-%d позиций по выручке" % len(rows),
          "Собрано %s из данных iiko. Меняйте процент в жёлтой колонке — всё пересчитается." % built)

    # настройки, на которые ссылаются формулы
    ws["A4"] = "Реакция объёма на 1% цены"
    ws["A4"].font = Font(bold=True, size=10, color=NAVY)
    ws["D4"] = ELASTICITY
    ws["D4"].number_format = "0.0"
    ws["D4"].fill = PatternFill("solid", fgColor="FFF3CD")
    ws["D4"].border = BORD
    ws["E4"] = "% объёма уходит на каждый процент цены (минус — уходит)"
    ws["E4"].font = Font(size=9.5, color=GREY)

    ws["A5"] = "Ориентир роста цены за год"
    ws["A5"].font = Font(bold=True, size=10, color=NAVY)
    ws["D5"] = TARGET_PER_YEAR / 100
    ws["D5"].number_format = "0.0%"
    ws["D5"].fill = PatternFill("solid", fgColor="FFF3CD")
    ws["D5"].border = BORD
    ws["E5"] = "ниже этого цена отстаёт от подорожания сырья и зарплаты"
    ws["E5"].font = Font(size=9.5, color=GREY)

    H = 7
    cols = [("Позиция", 40), ("Категория", 13), ("Очередь", 13),
            ("Выручка, ₸/мес", 14), ("Объём, шт/мес", 12), ("Цена, ₸", 10),
            ("Цена ± за период", 12), ("Мес.", 6), ("Маржа", 8), ("Объём 3м/3м", 11),
            ("Рекомендуем", 11), ("ПОДНЯТЬ, %", 11), ("Новая цена, ₸", 12),
            ("Выручка, +₸/мес", 14), ("Вал. прибыль, +₸/мес", 16),
            ("Вал. прибыль, +₸/год", 16), ("Запас по объёму", 12),
            ("Ожидаем объём", 12), ("Обоснование", 58), ("Карточки в iiko", 46)]
    head_row(ws, H, cols)
    NC = len(cols)

    first = H + 1
    for i, r in enumerate(rows):
        row = first + i
        ws.cell(row=row, column=1, value=r["name"])
        ws.cell(row=row, column=2, value=r["cat"])
        ws.cell(row=row, column=3, value=r["wave"])
        ws.cell(row=row, column=4, value=round(r["rev"]))
        ws.cell(row=row, column=5, value=round(r["qty"]))
        ws.cell(row=row, column=6, value=round(r["price"]))
        ws.cell(row=row, column=7, value=None if r["yoy"] is None else r["yoy"] / 100)
        ws.cell(row=row, column=8, value=r["ym"])
        ws.cell(row=row, column=9, value=r["mg"] / 100)
        ws.cell(row=row, column=10, value=None if r["trend"] is None else r["trend"] / 100)
        ws.cell(row=row, column=11, value=r["rec"] / 100)
        p = ws.cell(row=row, column=12, value=r["rec"] / 100)   # то, что меняет пользователь
        p.fill = PatternFill("solid", fgColor="FFF3CD")
        p.font = Font(bold=True, size=10, color="7A5C00")

        # формулы: k = 1 + эластичность × процент
        k = "(1+$D$4*L{r})".format(r=row)
        ws.cell(row=row, column=13, value="=ROUND(F{r}*(1+L{r}),0)".format(r=row))
        ws.cell(row=row, column=14,
                value="=ROUND(D{r}*{k}*(1+L{r})-D{r},0)".format(r=row, k=k))
        ws.cell(row=row, column=15,
                value="=ROUND(D{r}*{k}*(I{r}+L{r})-D{r}*I{r},0)".format(r=row, k=k))
        ws.cell(row=row, column=16, value="=ROUND(O{r}*12,0)".format(r=row))
        ws.cell(row=row, column=17,
                value="=IF(L{r}=0,\"\",L{r}/(I{r}+L{r}))".format(r=row))
        ws.cell(row=row, column=18, value="=$D$4*L{r}".format(r=row))
        ws.cell(row=row, column=20, value=" · ".join(r.get("cards") or []))
        ws.cell(row=row, column=19, value=r["why"] + (
            ". Расчёт просит %.1f%% — остальное вторым шагом через квартал" % r["need"]
            if r["need"] > r["rec"] else ""))

        for c in range(1, NC + 1):
            cell = ws.cell(row=row, column=c)
            cell.border = BORD
            if c != 12:
                cell.font = Font(size=10, color=INK)
            if c in (4, 5, 6, 13, 14, 15, 16):
                cell.number_format = '#,##0'
            if c in (7, 9, 10, 11, 12, 17, 18):
                cell.number_format = '0.0%'
            if c in (1, 2, 3, 19, 20):
                cell.alignment = Alignment(vertical="center", wrap_text=(c in (19, 20)))
            else:
                cell.alignment = Alignment(horizontal="right", vertical="center")
        # очередь — цветом, чтобы список читался сверху вниз
        w = ws.cell(row=row, column=3)
        if r["wave"].startswith("1"):
            w.fill = PatternFill("solid", fgColor="DFF3E4")
            w.font = Font(size=9.5, bold=True, color="1B5E33")
        elif r["wave"].startswith("2"):
            w.fill = PatternFill("solid", fgColor="FFF1D6")
            w.font = Font(size=9.5, bold=True, color="7A5C00")
        else:
            w.font = Font(size=9.5, color=GREY)
        ws.row_dimensions[row].height = 26
        if i % 2:
            for c in range(1, NC + 1):
                if c not in (3, 12):
                    ws.cell(row=row, column=c).fill = PatternFill("solid", fgColor="F7F9FC")

    last = first + len(rows) - 1
    tot = last + 1
    ws.cell(row=tot, column=1, value="ИТОГО · %d позиций" % len(rows))
    ws.cell(row=tot, column=4, value="=SUM(D{a}:D{b})".format(a=first, b=last))
    ws.cell(row=tot, column=9,
            value="=SUMPRODUCT(D{a}:D{b},I{a}:I{b})/D{t}".format(a=first, b=last, t=tot))
    ws.cell(row=tot, column=12,
            value="=SUMPRODUCT(D{a}:D{b},L{a}:L{b})/D{t}".format(a=first, b=last, t=tot))
    ws.cell(row=tot, column=14, value="=SUM(N{a}:N{b})".format(a=first, b=last))
    ws.cell(row=tot, column=15, value="=SUM(O{a}:O{b})".format(a=first, b=last))
    ws.cell(row=tot, column=16, value="=SUM(P{a}:P{b})".format(a=first, b=last))
    ws.cell(row=tot, column=19,
            value="=\"Прирост к нынешней валовой прибыли этих позиций: \"&TEXT(O{t}/"
                  "SUMPRODUCT(D{a}:D{b},I{a}:I{b}),\"0.0%\")".format(a=first, b=last, t=tot))
    for c in range(1, NC + 1):
        cell = ws.cell(row=tot, column=c)
        cell.font = Font(bold=True, size=10.5, color=NAVY)
        cell.fill = PatternFill("solid", fgColor="E8EDF5")
        cell.border = BORD
        if c in (4, 5, 14, 15, 16):
            cell.number_format = '#,##0'
        if c in (9, 12):
            cell.number_format = '0.0%'
        cell.alignment = Alignment(horizontal="right" if c > 3 else "left", vertical="center")
    ws.row_dimensions[tot].height = 26

    ws.freeze_panes = "B" + str(first)
    ws.auto_filter.ref = "A{h}:{col}{b}".format(h=H, col=get_column_letter(NC), b=last)
    return ws


def sheet_prices(wb, rows, full):
    """Цена и количество по месяцам плюс отдельный график на каждую позицию."""
    ws = wb.create_sheet("Цены по месяцам")
    ws.sheet_view.showGridLines = False
    title(ws, 1, "Цена и количество по месяцам",
          "Цена = выручка ÷ количество по всем клиентам. График рядом с каждой позицией.")

    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 13
    for i in range(len(full)):
        ws.column_dimensions[get_column_letter(3 + i)].width = 10

    H = 4
    ws.cell(row=H, column=1, value="Позиция").font = Font(bold=True, size=9.5, color="FFFFFF")
    ws.cell(row=H, column=2, value="Показатель").font = Font(bold=True, size=9.5, color="FFFFFF")
    for i, m in enumerate(full):
        c = ws.cell(row=H, column=3 + i, value=MO[m[5:]] + "'" + m[2:4])
        c.font = Font(bold=True, size=9.5, color="FFFFFF")
        c.alignment = Alignment(horizontal="center")
    for c in range(1, 3 + len(full)):
        ws.cell(row=H, column=c).fill = PatternFill("solid", fgColor=NAVY)
        ws.cell(row=H, column=c).border = BORD

    # каждая позиция занимает блок в 16 строк: две строки данных и график
    BLOCK = 16
    row = H + 1
    for r in rows:
        pr, qr = row, row + 1
        ws.cell(row=pr, column=1, value=r["name"]).font = Font(bold=True, size=10.5, color=NAVY)
        ws.cell(row=pr, column=2, value="Цена, ₸").font = Font(size=10, color=GREY)
        ws.cell(row=qr, column=2, value="Количество, шт").font = Font(size=10, color=GREY)
        for i in range(len(full)):
            a = ws.cell(row=pr, column=3 + i, value=None if r["ser"][i] is None else round(r["ser"][i]))
            a.number_format = '#,##0'
            a.border = BORD
            b = ws.cell(row=qr, column=3 + i, value=round(r["qs"][i]))
            b.number_format = '#,##0'
            b.border = BORD
            b.font = Font(size=10, color=GREY)
        ws.cell(row=pr, column=1).border = BORD
        ws.cell(row=qr, column=1, value=r["cat"] + " · маржа %.0f%%" % r["mg"]).font = \
            Font(size=9.5, color=GREY, italic=True)

        ch = LineChart()
        ch.title = r["name"]
        ch.style = 2
        ch.height = 6.2
        ch.width = 15.5
        ch.y_axis.title = "₸ за штуку"
        ch.y_axis.majorGridlines = ChartLines()
        ch.legend = None
        data = Reference(ws, min_col=3, max_col=2 + len(full), min_row=pr, max_row=pr)
        cats = Reference(ws, min_col=3, max_col=2 + len(full), min_row=H, max_row=H)
        ch.add_data(data, titles_from_data=False, from_rows=True)
        ch.set_categories(cats)
        s = ch.series[0]
        s.smooth = False
        s.graphicalProperties.line.width = 22000
        s.graphicalProperties.line.solidFill = "7C3AED"
        s.marker.symbol = "circle"
        s.marker.size = 6
        ws.add_chart(ch, "B" + str(row + 3))

        row += BLOCK
    return ws


def sheet_method(wb, rows, built):
    ws = wb.create_sheet("Методика")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 118
    txt = [
        ("Как читать этот файл", "h"),
        ("Собрано %s из выгрузки iiko. В расчёт идут только закрытые месяцы: "
         "в текущем себестоимость ещё не разнесена, и маржа по нему завышена." % built, "p"),
        ("", "p"),
        ("Что можно менять", "h"),
        ("На листе «План» жёлтым выделены три вещи: реакция объёма на цену (ячейка C4), "
         "ориентир роста цены за год (C5) и колонка «Поднять, %» по каждой позиции. "
         "Всё остальное — формулы, они пересчитаются сами.", "p"),
        ("", "p"),
        ("Откуда берётся рекомендация", "h"),
        ("Сравнивать нашу цену не с чем — прайса конкурентов у нас нет. Поэтому смотрим на другое: "
         "насколько цена отстала от подорожания. Ориентир — %.0f%% в год. Считаем, сколько цена "
         "выросла за то время, что мы наблюдаем позицию, и разницу с ориентиром берём за базу подъёма."
         % TARGET_PER_YEAR, "p"),
        ("Дальше две надбавки и один стоп-кран: маржа ниже 45%% — плюс 3 пункта (на тонкой марже "
         "процент цены даёт максимальный прирост прибыли); объём растёт больше чем на 30%% — плюс "
         "1,5 пункта (спрос опережает, подъём проглотят); объём падает больше чем на 15%% — потолок "
         "2%%, такую позицию трогать нельзя. Позиции, которым цену уже подняли выше ориентира с "
         "запасом, не трогаем вовсе.", "p"),
        ("Разовый шаг ограничен %.0f%%: больше клиент за один раз не принимает. Где расчёт просит "
         "больше, в обосновании написано «вторым шагом через квартал»." % STEP_CAP, "p"),
        ("", "p"),
        ("Как считается эффект", "h"),
        ("Подъём цены не меняет себестоимость, поэтому весь прирост уходит в валовую прибыль — "
         "но часть объёма уходит вместе с ним. При выручке R, марже m, подъёме p и изменении объёма "
         "в k раз: новая выручка = R×k×(1+p), новая валовая прибыль = R×k×(m+p).", "p"),
        ("Отсюда «Запас по объёму» = p ÷ (m+p): настолько количество может упасть, прежде чем "
         "валовая прибыль вернётся к нынешней. Пока ожидаемое падение меньше запаса, подъём в плюсе.", "p"),
        ("", "p"),
        ("Почему позиций двадцать, а карточек в iiko больше", "h"),
        ("Часть позиций ведётся в iiko под двумя именами: обычным и с приставкой «RP*» — под ней ту же "
         "позицию берёт сеть АЗС. Это одно и то же изделие, поэтому в отчёте оно сведено в одну строку, "
         "а из каких карточек оно собрано, написано в последней колонке. Если считать карточки порознь, "
         "один товар распадается на две строки с разной историей цены, и в ТОП-20 попадают обе половинки. "
         "«Сырая» и «готовая» при этом остаются разными позициями.", "p"),
        ("", "p"),
        ("Как считается «Цена ±»", "h"),
        ("Медиана цены последних месяцев против медианы начала окна. Медиана, а не крайние точки, "
         "потому что первый месяц новой позиции — это пробная партия по розничной цене, и выход на "
         "опт выглядел бы обвалом. Месяцы, где позицию брали меньше четверти обычного объёма, из "
         "сравнения выброшены по той же причине.", "p"),
        ("Цена везде — выручка, делённая на количество, по всем клиентам сразу. Это фактическая цена "
         "отгрузки со всеми скидками, а не прайс.", "p"),
        ("", "p"),
        ("Система «Пульс» · Фуд Завод · Фуд Завод", "f"),
    ]
    r = 2
    for t, kind in txt:
        c = ws.cell(row=r, column=1, value=t)
        if kind == "h":
            c.font = Font(bold=True, size=12, color=NAVY)
            ws.row_dimensions[r].height = 24
        elif kind == "f":
            c.font = Font(size=9.5, color=GREY, italic=True)
        else:
            c.font = Font(size=10.5, color=INK)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = max(16, 14 * (len(t) // 108 + 1))
        r += 1
    return ws


def main():
    rows, full = build()
    waves(rows)
    built = almaty.now().strftime("%d.%m.%Y")
    wb = Workbook()
    wb.remove(wb.active)
    sheet_plan(wb, rows, built)
    sheet_prices(wb, rows, full)
    sheet_method(wb, rows, built)
    wb.properties.creator = "Фуд Завод"
    wb.properties.title = "План повышения цен"
    wb.save(OUT)
    rec = sum(r["rev"] * (1 + ELASTICITY * r["rec"] / 100) * (r["mg"] / 100 + r["rec"] / 100)
              - r["rev"] * r["mg"] / 100 for r in rows)
    n = len([r for r in rows if r["rec"] > 0])
    print("  → план_повышения_цен.xlsx: %d позиций, %d к подъёму (%d КБ)"
          % (len(rows), n, os.path.getsize(OUT) // 1024))
    print("     эффект по рекомендации: %s ₸ вал. прибыли в месяц"
          % f"{round(rec):,}".replace(",", " "))


if __name__ == "__main__":
    main()
