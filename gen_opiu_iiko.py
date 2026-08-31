# -*- coding: utf-8 -*-
"""gen_opiu_iiko.py — весь ОПиУ постатейно прямо из iiko, помесячно.

Зачем: бухгалтерский xlsx обновляется руками и отстаёт на два месяца,
поэтому аудит на нём всегда смотрит в прошлое. Здесь тот же отчёт строится
из оборотов по счетам iiko — названия счетов совпадают со строками ОПиУ.
xlsx остаётся только для двух вещей: он задаёт порядок и иерархию строк
и служит эталоном для сверки.

Три вещи, из-за которых наивная выгрузка врёт, и как они решены:

  1. Знак. У доходных строк («Торговая выручка», «Удержания из ЗП»,
     «Доходы прочие») нужен кредитовый оборот, у расходных — дебетовый.
     Тип счёта в iiko для этого недостаточно надёжен, поэтому берём
     принадлежность строки к блоку доходов из самого ОПиУ.

  2. Незакрытый месяц. Зарплата, налоги, аренда и НДС проводятся в конце
     месяца, поэтому текущий месяц выглядит сказочно прибыльным.
     Считаем досчёт: регулярные статьи дополняем медианой закрытых
     месяцев, урезанной по доле прошедших дней, и честно помечаем,
     что это оценка.

  3. Время. Тянуть 20 месяцев каждый прогон долго и незачем: закрытые
     месяцы не меняются. Файл ведётся накопительно, заново тянутся
     только последние три месяца и те, которых ещё нет.

Только чтение iiko. Запускается в GitHub Actions.
"""
import calendar, json, os, re, statistics, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import almaty
import opiu_full as OF
import gen_opiu_audit as GA

OUT = os.path.join(HERE, "opiu_iiko.js")
FIRST = "2025-01"          # с какого месяца ведём историю
REFRESH_TAIL = 3           # сколько последних месяцев перетягиваем каждый раз
# поля, без которых запись кэша считается устаревшей и тянется заново
CACHE_FIELDS = ("rev", "through", "closed", "fullMonth", "share", "v", "est")

# ── Счета, обороты по которым НЕ равны строке ОПиУ ───────────────────────
# «Зарплата» в iiko — расчётный счёт с персоналом: на нём и начисления,
# и их закрытие/выплата. Оборот по такому счёту не равен строке отчёта:
# сверка с самим ОПиУ iiko за 2026 год дала расхождение ровно на эту строку —
# в июне оборот показал +32.4 млн ₸, а отчёт по той же строке −0.7 млн ₸,
# и «Итого Расходы» разъезжались ровно на эту разницу (33.1 млн ₸).
# В бухгалтерском xlsx строка «Зарплата» тоже стоит нулём во всех месяцах.
# Поэтому счёт из подмешивания исключаем: строка остаётся такой, какой её
# даёт бухгалтерия, а фантомные 33 млн ₸ расходов в июне исчезают.
SKIP_ACCOUNTS = {"Зарплата"}

# группы, по которым видно, что начисления конца месяца ещё не прошли
GAP_GROUPS = (
    ("ФОТ производства", ["2.1.ЗП Производство", "2.5.Налоги Производство"]),
    ("ФОТ АУП", ["3.1.1.ЗП АУП", "3.1.4. Налоги АУП"]),
    ("аренда", ["3.1.Аренда (пр-во)", "3.2.Аренда КомУсл Пр-во"]),
    ("НДС", ["3.3.2.Налоги НДС"]),
    ("логистика", ["Логистика доставка"]),
)


def turnover(y, m, last_full):
    """Обороты по счетам за месяц. В отличие от opiu_full.turnover год не зашит."""
    d1 = date(y, m, 1)
    d2 = min(date(y, m, calendar.monthrange(y, m)[1]), last_full)
    if d2 < d1:
        return None, None
    body = {
        "reportType": "TRANSACTIONS", "buildSummary": "true",
        "groupByRowFields": ["Account.Name", "Account.Type"],
        "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
        "filters": {
            "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                   "from": d1.isoformat(),
                                   "to": (d2 + timedelta(days=1)).isoformat(),
                                   "includeLow": True, "includeHigh": True},
            "Department": {"filterType": "IncludeValues", "values": [OF.FZ_DEPT]},
        },
    }
    data = OF.olap(body)
    if data is None:
        return None, None
    rows = {}
    for row in data:
        nm = (row.get("Account.Name") or "—").strip()
        inc = row.get("Sum.Incoming") or 0
        outg = row.get("Sum.Outgoing") or 0
        r = rows.setdefault(nm, {"debit": 0.0, "credit": 0.0,
                                 "type": (row.get("Account.Type") or "").strip()})
        r["debit"] += inc - outg
        r["credit"] += outg - inc
    return rows, d2


def month_keys(first, today):
    y, m = int(first[:4]), int(first[5:7])
    out = []
    while (y, m) <= (today.year, today.month):
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def load_cache():
    if not os.path.exists(OUT):
        return {}
    try:
        s = open(OUT, encoding="utf-8").read()
        got = json.loads(s[s.index("=") + 1:].rstrip().rstrip(";")).get("months", {})
        # записи старого формата перетягиваем: набор полей менялся
        got = {k: v for k, v in got.items() if all(f in v for f in CACHE_FIELDS)}
        # из уже сохранённых месяцев вычищаем исключённые счета, иначе закрытые
        # месяцы так и остались бы с ошибкой: заново тянутся только последние
        for rec in got.values():
            for nm in SKIP_ACCOUNTS:
                if isinstance(rec.get("v"), dict):
                    rec["v"].pop(nm, None)
                if isinstance(rec.get("est"), dict):
                    rec["est"].pop(nm, None)
        return got
    except Exception as e:
        print("кэш не прочитался (%s) — тяну заново" % e)
        return {}


def main():
    months_x, labels_x, rows_x = GA.load()
    lines = [r for r in rows_x if r["kind"] == "line"]
    by_norm, is_inc = {}, {}
    for r in lines:
        by_norm.setdefault(OF.norm(r["n"]), r["n"])
        is_inc[r["n"]] = bool(r["inc"])
    print("строк ОПиУ: %d (доходных %d)" % (len(lines), sum(is_inc.values())))

    today = almaty.today()
    last_full = today - timedelta(days=1)
    want = month_keys(FIRST, today)
    cache = load_cache()
    tail = set(want[-REFRESH_TAIL:])
    todo = [k for k in want if k not in cache or k in tail]
    print("месяцев всего %d, в кэше %d, тянем %d: %s"
          % (len(want), len(cache), len(todo), ", ".join(todo)))

    if todo:
        OF.TOK = OF.auth()

    unknown = {}
    for k in todo:
        y, m = int(k[:4]), int(k[5:7])
        rows, d2 = turnover(y, m, last_full)
        if not rows:
            print("  %s: iiko не ответил — оставляю как было" % k)
            continue
        vals = {}
        for nm, r in rows.items():
            key = by_norm.get(OF.norm(nm))
            if key in SKIP_ACCOUNTS:      # оборот по расчётному счёту ≠ строка ОПиУ
                continue
            if key is None:
                if abs(r["debit"]) >= 1:
                    unknown[nm] = unknown.get(nm, 0.0) + r["debit"]
                continue
            # знак берём из самого ОПиУ, а не из типа счёта в iiko:
            # «Удержания из ЗП» и «Доходы прочие» типом INCOME не помечены,
            # и по дебету они приходили с обратным знаком
            vals[key] = vals.get(key, 0.0) + (r["credit"] if is_inc[key] else r["debit"])

        dim = calendar.monthrange(y, m)[1]
        share = d2.day / float(dim)
        rev = sum(vals.get(n, 0) for n in ("Торговая выручка", "Выручка"))

        # Месяц, закрытый бухгалтерией, берём как есть: там всё проведено,
        # а «нормой» служат другие месяцы, и досчёт только испортил бы историю
        # (в начале 2025 логистики не было вовсе — это факт, а не пропуск).
        closed = k <= months_x[-1]

        gaps = []
        if not closed:
            for grp, names in GAP_GROUPS:
                got = sum(vals.get(n, 0) for n in names)
                typ = _typical(lines, names)
                if typ > 0 and got < typ * share * 0.55:
                    gaps.append("%s: %s вместо ожидаемых %s" % (grp, GA.fmt(got), GA.fmt(typ * share)))

        est, est_of = dict(vals), []
        if not closed:
            for r in lines:
                n = r["n"]
                if n in ("Торговая выручка", "Выручка") or is_inc[n] or n in SKIP_ACCOUNTS:
                    continue
                nz = [x for x in r["v"][-6:] if x]
                if len(nz) < 5:                   # досчитываем только регулярные статьи
                    continue
                typ = statistics.median(nz) * share
                got = vals.get(n, 0)
                if typ > 0 and got < typ * 0.4:
                    est[n] = round(typ)
                    est_of.append({"n": n, "was": round(got), "est": round(typ)})
        est_of.sort(key=lambda x: -(x["est"] - x["was"]))
        add = sum(x["est"] - x["was"] for x in est_of)

        cache[k] = {"rev": round(rev), "through": d2.isoformat(), "closed": closed,
                    "fullMonth": d2.day == dim, "share": round(share, 3),
                    "gaps": gaps, "estOf": est_of[:30], "estAdd": round(add),
                    "v": {a: round(b) for a, b in vals.items() if abs(b) >= 1},
                    "est": {a: round(b) for a, b in est.items() if abs(b) >= 1}}
        print("  %s: выручка %s, статей %d, по %s (%.0f%%)%s%s"
              % (k, GA.fmt(rev), len(cache[k]["v"]), d2.strftime("%d.%m"), share * 100,
                 "" if not gaps else " | не проведено: " + "; ".join(gaps),
                 "" if not est_of else " | досчёт %d статей на %s" % (len(est_of), GA.fmt(add))))

    if unknown:
        top = sorted(unknown.items(), key=lambda x: -abs(x[1]))[:10]
        print("счета без строки в ОПиУ:", ", ".join("%s (%s)" % (n, GA.fmt(v)) for n, v in top))

    # ── сверка с бухгалтерским xlsx там, где есть оба источника
    diff = []
    for k in months_x:
        if k not in cache:
            continue
        i = months_x.index(k)
        for r in lines:
            a = r["v"][i]
            b = cache[k]["v"].get(r["n"], 0)
            if abs(a - b) >= 500000:
                diff.append({"m": k, "n": r["n"], "x": a, "i": b, "d": b - a})
    diff.sort(key=lambda r: -abs(r["d"]))
    print("расхождений xlsx vs iiko (от 500 тыс): %d" % len(diff))
    for r in diff[:8]:
        print("   %s %-40s xlsx %-12s iiko %-12s %s"
              % (r["m"], r["n"][:40], GA.fmt(r["x"]), GA.fmt(r["i"]), GA.fmt(r["d"])))

    data = {"updated": almaty.now().strftime("%d.%m.%Y %H:%M"),
            "through": last_full.isoformat(),
            "xlsxThrough": months_x[-1],
            "months": {k: cache[k] for k in want if k in cache},
            "diff": diff[:200]}
    open(OUT, "w", encoding="utf-8").write(
        "window.OPIU_IIKO=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")
    print("записан opiu_iiko.js (%d мес., расхождений в списке %d)"
          % (len(data["months"]), len(data["diff"])))


def _typical(lines, names):
    tot = None
    for r in lines:
        if r["n"] in names:
            tot = r["v"] if tot is None else [a + b for a, b in zip(tot, r["v"])]
    if not tot:
        return 0
    tail = [x for x in tot[-6:] if x]
    return statistics.median(tail) if tail else 0


if __name__ == "__main__":
    main()
