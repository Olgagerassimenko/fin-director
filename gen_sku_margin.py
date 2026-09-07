# -*- coding: utf-8 -*-
"""
gen_sku_margin.py — маленький справочник маржи по позициям для раздела
«Повышение цен» на дашборде «Продажи».

Зачем отдельный файл. Раздел считает, кому из клиентов можно поднять цену, и
для этого ему нужна маржа: подъём цены целиком уходит в валовую прибыль, но
чтобы понять, сколько объёма мы можем при этом потерять и не проиграть, надо
знать текущую маржу того ассортимента, который берёт клиент.

Полные данные по SKU лежат в sku_live.js — это больше мегабайта, тянуть их на
страницу продаж ради одного числа на позицию незачем. Здесь из них остаётся
только имя позиции, маржа в процентах и выручка за последние закрытые месяцы:
получается файл на пару десятков килобайт.

Маржу берём за последние ПОЛНЫЕ месяцы: в незакрытом месяце себестоимость ещё
не разнесена, и маржа по нему выходит завышенной.

Запускается в пайплайне после SKU_iiko/generate.py, который пишет sku_live.js.
"""
import os, re, json, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import almaty  # время завода — Алматы (UTC+5), не UTC раннера

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sku_live.js")
OUT = os.path.join(HERE, "sku_margin.js")

MONTHS = 3          # сколько последних полных месяцев берём
MIN_REV = 50_000    # позиции мельче этого в справочник не попадают


def load():
    txt = open(SRC, encoding="utf-8").read()
    m = re.search(r"window\.SKU_DATA_LIVE\s*=\s*(\{.*?\});\s*\n\s*window\.SKU_LIVE_META", txt, re.S)
    if not m:
        m = re.search(r"window\.SKU_DATA_LIVE\s*=\s*(\{.*\});", txt, re.S)
    if not m:
        raise SystemExit("sku_live.js не разобрался")
    return json.loads(m.group(1))


def main():
    d = load()
    labels = d.get("mo_labels") or []
    skus = d.get("skus") or []
    if not labels or not skus:
        raise SystemExit("в sku_live.js нет данных")

    # Последний месяц в файле — текущий и незакрытый: он идёт последним столбцом
    # и по нему себестоимость ещё не разнесена. Берём месяцы до него.
    n = len(labels)
    end = n - 1
    idx = list(range(max(0, end - MONTHS), end))
    if not idx:
        idx = [max(0, n - 1)]

    out = {}
    for s in skus:
        rev = sum((s.get("monthly_rev") or [0] * n)[i] or 0 for i in idx)
        vp = sum((s.get("monthly_vp") or [0] * n)[i] or 0 for i in idx)
        qty = sum(abs((s.get("monthly_qty") or [0] * n)[i] or 0) for i in idx)
        if rev < MIN_REV:
            continue
        mg = round(vp / rev * 100, 1) if rev else 0.0
        # Маржа выше 95% или ниже −50% — это не маржа, а не разнесённая
        # себестоимость или возврат прошлого месяца. Такие позиции пропускаем,
        # чтобы расчёт эффекта не опирался на мусор.
        if mg > 95 or mg < -50:
            continue
        out[s["name"]] = {"m": mg, "r": round(rev), "q": round(qty)}

    meta = {
        "months": [labels[i] for i in idx],
        "built": almaty.now().strftime("%d.%m.%Y %H:%M"),
        "skus": len(out),
    }
    js = ("window.SKU_MARGIN=" + json.dumps(out, ensure_ascii=False, separators=(",", ":"))
          + ";\nwindow.SKU_MARGIN_META=" + json.dumps(meta, ensure_ascii=False) + ";\n")
    open(OUT, "w", encoding="utf-8").write(js)
    tot_r = sum(v["r"] for v in out.values())
    tot_vp = sum(v["r"] * v["m"] / 100 for v in out.values())
    print("  → sku_margin.js: %d позиций за %s (%d КБ)"
          % (len(out), ", ".join(meta["months"]), os.path.getsize(OUT) // 1024))
    print("     выручка %s ₸, средняя маржа %.1f%%"
          % (f"{tot_r:,}".replace(",", " "), tot_vp / tot_r * 100 if tot_r else 0))


if __name__ == "__main__":
    main()
