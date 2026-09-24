# -*- coding: utf-8 -*-
"""Крупнейший покупатель — маленький файл для плашки на главной.

contractor_items.js весит полтора мегабайта: тянуть его на главную ради двух
строк нельзя. Здесь вытаскиваем лидера последнего месяца и лидера года.
"""
import os, sys, json, re
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
t = open(os.path.join(HERE, "contractor_items.js"), encoding="utf-8").read()
D = json.loads(t.split("=", 1)[1].rstrip().rstrip(";"))

MES = ["", "январь", "февраль", "март", "апрель", "май", "июнь", "июль",
       "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]

def pick(rows):
    if not rows: return None
    r = max(rows, key=lambda x: x.get("rev") or 0)
    it = (r.get("items") or [])
    top = max(it, key=lambda x: x.get("r") or 0) if it else None
    return {"n": re.sub(r"^\d+-", "", str(r.get("name") or "")).strip(),
            "full": r.get("name") or "", "rev": round(r.get("rev") or 0),
            "pct": r.get("pct"), "points": r.get("points"),
            "item": (re.sub(r"^[А-ЯA-Z]{1,3}\*\s*", "", str(top["n"])).strip() if top else ""),
            "itemRev": round(top["r"]) if top else 0}

months = sorted(k for k in D if re.match(r"^\d{4}-\d{2}$", k))
last = months[-1] if months else None
out = {
    "month": last,
    "monthLabel": (MES[int(last[5:7])] if last else ""),
    "top": pick(D.get(last) or []),
    "year": pick(D.get("year") or []),
    "n": len(D.get(last) or []),
}
open(os.path.join(HERE, "buyer_top.js"), "w", encoding="utf-8").write(
    "window.BUYER_TOP=" + json.dumps(out, ensure_ascii=False) + ";")
print("buyer_top.js: %s — %s, %s ₸" % (out["monthLabel"], (out["top"] or {}).get("n"),
      format((out["top"] or {}).get("rev", 0), ",").replace(",", " ")))
