# -*- coding: utf-8 -*-
"""Собирает лёгкий закуп.html + сжатый zakup_data.js из _шаблон_закуп.html + zakup.json.

Данные больше НЕ встраиваются в закуп.html (иначе файл ~4 МБ и Cloudflare не публикует
его свежим). Вместо этого:
  • данные gzip-сжимаются и кодируются base64 в отдельный zakup_data.js (~1 МБ);
  • в закуп.html встраивается распаковщик pako (без внешних CDN) и подключается zakup_data.js;
  • при открытии страницы данные синхронно распаковываются в const D — остальной код не меняется.
"""
import os, json, sys, gzip, base64
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))

tpl  = open(os.path.join(HERE, "_шаблон_закуп.html"), encoding="utf-8").read()
data = json.load(open(os.path.join(HERE, "zakup.json"), encoding="utf-8"))
pako = open(os.path.join(HERE, "pako.min.js"), encoding="utf-8").read()

# 1) данные -> gzip -> base64 -> отдельный лёгкий файл
blob = json.dumps(data, ensure_ascii=False)
gz   = gzip.compress(blob.encode("utf-8"), 9)
b64  = base64.b64encode(gz).decode("ascii")
open(os.path.join(HERE, "zakup_data.js"), "w", encoding="utf-8").write(
    "window.__ZG=" + json.dumps(b64) + ";\n")

# версия для сброса кэша браузера (меняется при каждом обновлении)
ver = ((data.get("updatedFull") or data.get("updated") or "")
       .replace(".", "").replace(":", "").replace(" ", "")) or "1"

# 2) распаковщик pako встраиваем прямо в страницу + подключаем данные
inject = ("<script>" + pako + "</script>\n"
          "<script src=\"/zakup_data.js?v=" + ver + "\"></script>\n")
decode = ("const D=JSON.parse(pako.ungzip("
          "Uint8Array.from(atob(window.__ZG),function(c){return c.charCodeAt(0);}),"
          "{to:'string'}));")

out = tpl.replace("</head>", inject + "</head>", 1).replace("/*__DATA__*/", decode)
open(os.path.join(HERE, "закуп.html"), "w", encoding="utf-8").write(out)

print("закуп.html %d КБ (лёгкий) + zakup_data.js %d КБ (сжатые данные) · месяцев %d, недель %d, позиций(год) %d, поставщиков КЗ %d" % (
    len(out) // 1024, (len(b64) + 15) // 1024,
    len(data.get("months", [])), len(data.get("weeks", [])),
    len(data.get("ceny", {}).get("year", {}).get("products", [])),
    len(data.get("kz", {}).get("rows", []))))
