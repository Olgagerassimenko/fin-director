# -*- coding: utf-8 -*-
"""Собирает скрытую страницу склады.html с диаграммами по складам.
Источник остатков (invStores) — ддс_данные.json (живьём из iiko при прогоне),
а если его нет локально — вытаскиваем те же данные из уже собранного дашборд_ддс.html.
Данные вшиваются в _шаблон_склады.html вместо /*__DATA__*/."""
import os, json, re, datetime
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import almaty  # время завода — Алматы (UTC+5), не UTC раннера

HERE = os.path.dirname(os.path.abspath(__file__))

def load_from_json():
    p = os.path.join(HERE, "ддс_данные.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    if not d.get("invStores"):
        return None
    return {"invStores": d["invStores"], "through": d.get("through", ""),
            "updated": d.get("updated", ""), "updatedFull": d.get("updatedFull", "")}

def load_from_html():
    p = os.path.join(HERE, "дашборд_ддс.html")
    html = open(p, encoding="utf-8").read()
    # invStores — вырезаем по балансу скобок
    key = '"invStores"'
    i = html.index(key)
    b = html.index("{", i + len(key))
    depth = 0
    for k in range(b, len(html)):
        c = html[k]
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = k; break
    inv = json.loads(html[b:end + 1])
    def grab(name):
        m = re.search(r'"%s":\s*"([^"]*)"' % name, html)
        return m.group(1) if m else ""
    return {"invStores": inv, "through": grab("through"),
            "updated": grab("updated"), "updatedFull": grab("updatedFull")}

data = load_from_json() or load_from_html()
if not data.get("updatedFull"):
    data["updatedFull"] = almaty.now().strftime("%d.%m.%Y %H:%M")

tpl = open(os.path.join(HERE, "_шаблон_склады.html"), encoding="utf-8").read()
out = tpl.replace("/*__DATA__*/", "const DATA=" + json.dumps(data, ensure_ascii=False) + ";")
open(os.path.join(HERE, "склады.html"), "w", encoding="utf-8").write(out)
mcount = len(data["invStores"])
print("склады.html собран, месяцев:", mcount, "| складов:",
      len({n for m in data["invStores"].values() for n in m}))
