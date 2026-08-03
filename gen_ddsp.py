# -*- coding: utf-8 -*-
"""Собирает дашборд_ддс_прямой.html из ддс_прямой.json (прямой метод ДДС по статьям, iiko)."""
import os,json
HERE=os.path.dirname(os.path.abspath(__file__))
D=json.load(open(os.path.join(HERE,"ддс_прямой.json"),encoding="utf-8"))
# Продуктовая себестоимость (COST_OF_GOODS_SOLD) из ОПиУ iiko, помесячно.
# Для метрики «оплата за сырьё vs себестоимость за 3 мес». ОБНОВЛЯТЬ при обновлении ОПиУ.
if D.get("cogs_auto"):
    D["cogs"]={k:abs(v) for k,v in D["cogs_auto"].items() if v}
else:
    D["cogs"]={"2026-01":117848638,"2026-02":117144520,"2026-03":130180091,
               "2026-04":129130459,"2026-05":127075660,"2026-06":131510739}
D["prov"]="прямой метод по статьям · живьём из iiko на "+D.get("through","")
html=open(os.path.join(HERE,"_шаблон_ддс_прямой.html"),encoding="utf-8").read()
html=html.replace("/*__DATA__*/","const D="+json.dumps(D,ensure_ascii=False)+";")
open(os.path.join(HERE,"дашборд_ддс_прямой.html"),"w",encoding="utf-8").write(html)
# мета-дата для плашки ДДС на главной (обновляется каждое утро)
meta={"updated":D.get("updated",""),"through":D.get("through","")}
open(os.path.join(HERE,"ddsp_meta.js"),"w",encoding="utf-8").write("window.DDSP_META="+json.dumps(meta,ensure_ascii=False)+";")
print("дашборд_ддс_прямой.html собран, месяцев:",len(D.get("months",{})),"дней:",len(D.get("days",{})))
