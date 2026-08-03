# -*- coding: utf-8 -*-
"""Собирает дашборд_ддс.html из ддс_данные.json (живые данные iiko) + прибыль из ОПиУ + ДЗ/КЗ с Google Диска."""
import os,json,datetime
HERE=os.path.dirname(os.path.abspath(__file__))
D=json.load(open(os.path.join(HERE,"ддс_данные.json"),encoding="utf-8"))
# чистая прибыль из управленческого ОПиУ (данные iiko); обновляется при обновлении ОПиУ
PROF={"2026-01":-16285007,"2026-02":-24441949,"2026-03":-21640638,"2026-04":-13509164,
      "2026-05":33957432,"2026-06":12147436,"2026-07":86500089}
# ДЗ и КЗ — с Google Диска (дз_кз_месяцы.json): в iiko они завышены внутренними счетами
DZKZ={}
_dz=os.path.join(HERE,"дз_кз_месяцы.json")
if os.path.exists(_dz):
    try: DZKZ=json.load(open(_dz,encoding="utf-8"))
    except Exception: DZKZ={}
RUM={1:"январь",2:"февраль",3:"март",4:"апрель",5:"май",6:"июнь",7:"июль",8:"август",9:"сентябрь",10:"октябрь",11:"ноябрь",12:"декабрь"}
MKS=sorted(D["months"].keys())
for idx,k in enumerate(MKS):
    m=D["months"][k]
    if k in PROF: m["prof"]=PROF[k]
    # ДЗ/КЗ из Google перекрывают завышенные значения iiko
    if k in DZKZ:
        if DZKZ[k].get("dz") is not None: m["assets"]["rec"]=DZKZ[k]["dz"]
        if DZKZ[k].get("kz") is not None: m["debts"]["pay"]=DZKZ[k]["kz"]
    # пересчёт изменения оборотки по уровням (косвенный метод: эффект = -Δактива, +Δпассива)
    if idx>0:
        pm=D["months"][MKS[idx-1]]
        m["dRec"]=-(m["assets"]["rec"]-pm["assets"]["rec"])
        m["dPay"]=(m["debts"]["pay"]-pm["debts"]["pay"])
    m["interimOp"]=m["prof"]+m["dInv"]+m["dRec"]+m["dPay"]
    m["nonCash"]=m["op"]-m["interimOp"]
    mi=int(k.split("-")[1]); m["ru"]=f"{RUM[mi]} 2026"
    tod=datetime.date.today()
    close_day=datetime.date(2026 if mi<12 else 2027, mi+1 if mi<12 else 1, 18)
    m["closed"]=tod>=close_day
    m["closeNote"]="" if m["closed"] else ("период не закрыт — данные предварительные, обновятся после 18 "+RUM[(mi%12)+1])
D["profNote"]="прибыль — из ОПиУ (iiko); деньги, остатки и запасы — живьём из iiko на "+D.get("through","")+"; ДЗ и КЗ — с Google Диска"
html=open(os.path.join(HERE,"_шаблон_ддс.html"),encoding="utf-8").read()
html=html.replace("/*__DATA__*/","window.DDS="+json.dumps(D,ensure_ascii=False)+";")
open(os.path.join(HERE,"дашборд_ддс.html"),"w",encoding="utf-8").write(html)
print("дашборд_ддс.html собран, месяцев:",len(D["months"]),"| ДЗ/КЗ из Google:",bool(DZKZ))
