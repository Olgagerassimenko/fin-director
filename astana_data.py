# -*- coding: utf-8 -*-
"""Продажи астанинских точек Яндекс Лавки, помесячно.

Зачем отдельный файл. Отчёты «I Отчет ПРОДАЖИ MM.2026.xlsx», из которых
собирается дашборд, свёрнуты по контрагенту: все семнадцать лавок Яндекса
в них одна строка. Разрез по точкам есть только в айко, и воркер уже умеет
его отдавать (/sales_week?raw=1). Здесь мы ходим за ним помесячно и кладём
результат в astana_meta.js — страница продаж читает его так же, как
returns_meta.js.

Астанинскую точку отличаем по слову «Астана» в названии контрагента:
в айко оно проставлено у всех пяти и ни у одной алматинской.
"""
import json, os, re, sys, datetime
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import almaty

SITE = "https://lucky-river-eaf1.findirfoodzavod.workers.dev"
# Служебный токен приходит из секрета прогона; строка в коде осталась
# запасной, пока все прогоны не переведены на секрет.
import os
# Служебный токен — только из секрета прогона. Без него запрос честно
# получит «forbidden», и прогон покраснеет, а не соберёт тишину.
TOKEN = os.environ["PULSE_TOKEN"]
YEAR = 2026
LOG = open(os.path.join(HERE, "astana_log.txt"), "w", encoding="utf-8")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.write(s + "\n")


def month_rows(d1, d2):
    """CSV воркера: «имя,сумма». Имена содержат запятые и не закавычены,
    поэтому режем по последней запятой, а не csv-парсером."""
    r = requests.get(f"{SITE}/sales_week",
                     params={"from": d1, "to": d2, "raw": "1", "t": TOKEN},
                     timeout=300)
    r.raise_for_status()
    out = {}
    for line in r.text.splitlines():
        if not line or line.startswith("prefix") or line.startswith("ПЕРИОД"):
            continue
        i = line.rfind(",")
        if i < 0:
            continue
        name, val = line[:i].strip('"'), line[i + 1:]
        try:
            out[name] = int(float(val))
        except ValueError:
            pass
    return out


def yandex_margin():
    """Средневзвешенная маржа по номенклатуре, которую берёт Яндекс.
    Берём items контрагента 102 из contractor_items.js и ставки из
    sku_margin.js. Если файлов нет — возвращаем None, блок обойдётся."""
    try:
        ci = open(os.path.join(HERE, "contractor_items.js"), encoding="utf-8").read()
        sm = open(os.path.join(HERE, "sku_margin.js"), encoding="utf-8").read()
    except OSError:
        return None, None
    try:
        J = json.loads(ci.split("=", 1)[1].strip().rstrip(";"))
        dec = json.JSONDecoder()
        M, _ = dec.raw_decode(sm[sm.index("{"):])
    except Exception as e:
        log("  маржа: не разобрать файлы —", e)
        return None, None
    ctr = None
    for c in (J.get("year") or []):
        if str(c.get("num")) == "102":
            ctr = c
            break
    if not ctr:
        return None, None
    tot = matched = wsum = 0
    for it in ctr.get("items", []):
        r = it.get("r") or 0
        tot += r
        m = M.get(it.get("n"))
        if m:
            matched += r
            wsum += r * (m.get("m") or 0) / 100
    if matched <= 0:
        return None, None
    return round(wsum / matched * 100, 1), round(matched / tot * 100, 1)


def main():
    today = almaty.now().date()
    months, pts = [], {}
    for m in range(1, 13):
        d1 = datetime.date(YEAR, m, 1)
        if d1 > today:
            break
        nxt = datetime.date(YEAR + (m == 12), (m % 12) + 1, 1)
        d2 = min(nxt - datetime.timedelta(days=1), today)
        key = f"{YEAR}-{m:02d}"
        rows = month_rows(d1.isoformat(), d2.isoformat())
        if not rows:
            log(f"  {key}: пусто, пропускаю")
            continue
        months.append(key)
        for name, v in rows.items():
            if "Яндекс" not in name:
                continue
            pts.setdefault(name, {})[key] = v
        log(f"  {key}: точек Яндекса {sum(1 for n in rows if 'Яндекс' in n)}")

    def short(n):
        return re.sub(r"^\d+\s*-?\s*Яндекс\s+лавка\s*", "", n).replace(" Астана", "").strip()

    ast, alm = [], []
    for name, mv in pts.items():
        row = {"n": short(name), "full": name, "m": mv, "tot": sum(mv.values())}
        (ast if "Астана" in name else alm).append(row)
    ast.sort(key=lambda x: -x["tot"])
    alm.sort(key=lambda x: -x["tot"])

    margin, cover = yandex_margin()
    data = {
        "updated": almaty.now().strftime("%d.%m.%Y %H:%M"),
        "months": months,
        "astana": ast,
        "almaty": alm,
        "margin": margin,          # продуктовая маржа Яндекса, %
        "margin_cover": cover,     # доля выручки, по которой маржа известна
    }
    with open(os.path.join(HERE, "astana_meta.js"), "w", encoding="utf-8") as f:
        f.write("window.ASTANA=" + json.dumps(data, ensure_ascii=False) + ";\n")
    log(f"\nАстана: {len(ast)} точек, {sum(x['tot'] for x in ast):,} ₸".replace(",", " "))
    log(f"Алматы и Конаев: {len(alm)} точек, {sum(x['tot'] for x in alm):,} ₸".replace(",", " "))
    log(f"маржа Яндекса: {margin}% (покрытие {cover}%)")
    log("ГОТОВО -> astana_meta.js")
    LOG.close()
    print("OK")


if __name__ == "__main__":
    main()
