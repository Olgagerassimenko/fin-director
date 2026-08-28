# -*- coding: utf-8 -*-
"""gen_opiu_late.py — месяцы, которых ещё нет в бухгалтерском ОПиУ.

Бухгалтерия закрывает месяц с задержкой: в xlsx последний месяц — май,
а на дворе август. Этот скрипт достаёт недостающие месяцы прямо из iiko
постатейно (те же названия счетов, что и строки ОПиУ) и пишет opiu_late.js.

Такие месяцы НЕ равны закрытым: в незакрытом месяце обычно не проведены
зарплата, налоги и часть административных начислений — они проходят
в конце месяца и в начале следующего. Поэтому каждый месяц помечается
признаком closed и списком групп, где начисления явно не дошли,
а страница показывает их отдельно и с оговоркой.

Только чтение iiko. Запускается в GitHub Actions после opiu_full.py.
"""
import calendar, json, os, re, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import almaty  # время завода — Алматы (UTC+5), не UTC раннера
import opiu_full as OF          # переиспользуем авторизацию и выгрузку оборотов
import gen_opiu_audit as GA     # оттуда берём разбор xlsx


def norm(n):
    return OF.norm(n)


def main():
    months_x, labels_x, rows_x = GA.load()
    last_x = months_x[-1]
    print("в xlsx закрыто по %s" % last_x)

    # какие месяцы добираем: от следующего за последним в xlsx до текущего
    today = almaty.today()
    y, m = int(last_x[:4]), int(last_x[5:7])
    want = []
    while True:
        m += 1
        if m > 12:
            m = 1
            y += 1
        if (y, m) > (today.year, today.month):
            break
        want.append((y, m))
    if not want:
        print("добирать нечего — бухгалтерия догнала календарь")
        write({}, last_x)
        return
    print("добираем из iiko:", ", ".join("%d-%02d" % p for p in want))

    OF.TOK = OF.auth()
    last_full = today - timedelta(days=1)

    # названия строк ОПиУ из xlsx: по ним раскладываем счета iiko
    line_names = [r["n"] for r in rows_x if r["kind"] == "line"]
    by_norm = {}
    for n in line_names:
        by_norm.setdefault(norm(n), n)

    out, unknown = {}, {}
    for yy, mm in want:
        if yy != OF.YEAR:
            print("  %d-%02d: opiu_full настроен на %d год — пропускаю" % (yy, mm, OF.YEAR))
            continue
        d2 = min(date(yy, mm, calendar.monthrange(yy, mm)[1]), last_full)
        if d2 < date(yy, mm, 1):
            continue
        rows = OF.turnover(mm, last_full)
        if not rows:
            print("  %d-%02d: iiko не ответил — пропускаю" % (yy, mm))
            continue

        vals, rev = {}, 0.0
        for nm, r in rows.items():
            key = by_norm.get(norm(nm))
            if r["type"] == "INCOME" or norm(nm).startswith(("торговая выручка", "выручка")):
                rev += r["credit"]
                if key:
                    vals[key] = vals.get(key, 0.0) + r["credit"]
                continue
            if key:
                vals[key] = vals.get(key, 0.0) + r["debit"]
            elif abs(r["debit"]) >= 1:
                unknown[nm] = unknown.get(nm, 0.0) + r["debit"]

        # чего явно не хватает: начисления конца месяца
        gaps = []
        for grp, names in (("ФОТ производства", ["2.1.ЗП Производство", "2.5.Налоги Производство"]),
                           ("ФОТ АУП", ["3.1.1.ЗП АУП", "3.1.4. Налоги АУП"]),
                           ("аренда", ["3.1.Аренда (пр-во)"]),
                           ("НДС", ["3.3.2.Налоги НДС"])):
            got = sum(vals.get(n, 0) for n in names)
            base = _typical(rows_x, names)
            if base > 0 and got < base * 0.55:
                gaps.append("%s: %s вместо обычных %s" % (grp, GA.fmt(got), GA.fmt(base)))

        key = "%04d-%02d" % (yy, mm)
        full_month = d2.day == calendar.monthrange(yy, mm)[1]
        out[key] = {"rev": round(rev), "through": d2.isoformat(),
                    "fullMonth": full_month, "gaps": gaps,
                    "v": {k: round(v) for k, v in vals.items() if abs(v) >= 1}}
        print("  %s: выручка %s, статей %d, по %s%s"
              % (key, GA.fmt(rev), len(out[key]["v"]), d2.strftime("%d.%m"),
                 "" if not gaps else " | не проведено: " + "; ".join(gaps)))

    if unknown:
        top = sorted(unknown.items(), key=lambda x: -abs(x[1]))[:8]
        print("счета без строки в ОПиУ:", ", ".join("%s (%s)" % (n, GA.fmt(v)) for n, v in top))
    write(out, last_x)


def _typical(rows_x, names):
    """Обычный месячный размер группы по закрытым месяцам xlsx (медиана последних 6)."""
    import statistics
    tot = None
    for r in rows_x:
        if r["n"] in names:
            tot = r["v"] if tot is None else [a + b for a, b in zip(tot, r["v"])]
    if not tot:
        return 0
    tail = [x for x in tot[-6:] if x]
    return statistics.median(tail) if tail else 0


def write(months, last_x):
    data = {"updated": almaty.now().strftime("%d.%m.%Y %H:%M"),
            "afterXlsx": last_x, "months": months}
    open(os.path.join(HERE, "opiu_late.js"), "w", encoding="utf-8").write(
        "window.OPIU_LATE=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")
    print("записан opiu_late.js (%d мес.)" % len(months))


if __name__ == "__main__":
    main()
