# -*- coding: utf-8 -*-
"""Собирает закуп.html из _шаблон_закуп.html + zakup.json."""
import os, json, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(HERE, "_шаблон_закуп.html"), encoding="utf-8").read()
data = json.load(open(os.path.join(HERE, "zakup.json"), encoding="utf-8"))
blob = "const D=" + json.dumps(data, ensure_ascii=False) + ";"
out = tpl.replace("/*__DATA__*/", blob)
open(os.path.join(HERE, "закуп.html"), "w", encoding="utf-8").write(out)
print("закуп.html собран: месяцев %d, недель %d, позиций(год) %d, поставщиков КЗ %d, размер %d КБ" % (
    len(data.get("months", [])), len(data.get("weeks", [])),
    len(data.get("ceny", {}).get("year", {}).get("products", [])),
    len(data.get("kz", {}).get("rows", [])),
    len(out) // 1024))
