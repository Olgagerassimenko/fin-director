# -*- coding: utf-8 -*-
import json, datetime

def weeks_of(year, month):
    """5 недель Пн-Пт, пересекающих месяц; ярлык дат dd.mm–dd.mm."""
    d = datetime.date(year, month, 1)
    # первый понедельник на/до 1-го числа
    mon = d - datetime.timedelta(days=d.weekday())
    res=[]
    for i in range(6):
        s = mon + datetime.timedelta(days=i*7)
        e = s + datetime.timedelta(days=4)  # пятница
        # включаем неделю, если она пересекает месяц
        if s.month==month or e.month==month or (s<d and e>=d):
            res.append(f"{s.day:02d}.{s.month:02d}–{e.day:02d}.{e.month:02d}")
        if len(res)>=5: break
    return res[:5]

jul_w = weeks_of(2026,7)
aug_w = weeks_of(2026,8)

# ---- Июль (из «Неделя ОПЛАТ») ----
jul_inc=[53250000,53750000,71715000,49520000,52520000]
jul_exp=[46649942,70437800,59807564,48801360,56803929]
# ---- Август (план, из xlsx seed) ----
aug_inc=[53250000,55650000,72665000,50040000,53040000]
aug_exp=[44149942,70437800,59807564,48801360,56803929]

def month_obj(label, wlabels, inc, exp, status):
    weeks=[{"d":wlabels[i],"inc":inc[i],"exp":exp[i]} for i in range(len(wlabels))]
    return {"label":label,"status":status,"weeks":weeks}

# май/июнь — факт из iiko (недельно), посчитано отдельно
mj=json.load(open("/tmp/mayjun.json",encoding="utf-8"))

MONTHS=[
 ("2026-01","Январь",None),("2026-02","Февраль",None),("2026-03","Март",None),
 ("2026-04","Апрель",None),("2026-05","Май","факт"),("2026-06","Июнь","факт"),
 ("2026-07","Июль","план"),("2026-08","Август","план"),
 ("2026-09","Сентябрь",None),("2026-10","Октябрь",None),
 ("2026-11","Ноябрь",None),("2026-12","Декабрь",None),
]
YEAR={}
for key,label,st in MONTHS:
    if key=="2026-07": YEAR[key]=month_obj(label,jul_w,jul_inc,jul_exp,st)
    elif key=="2026-08": YEAR[key]=month_obj(label,aug_w,aug_inc,aug_exp,st)
    elif key in mj: YEAR[key]=month_obj(label,mj[key]["labels"],mj[key]["inc"],mj[key]["exp"],st)
    else: YEAR[key]={"label":label,"status":None,"weeks":[]}

DATA={"year":2026,"updated":"04.08.2026","months":YEAR,"order":[m[0] for m in MONTHS]}
json.dump(DATA, open("/tmp/god.json","w"), ensure_ascii=False)
print("июль недели:", jul_w)
print("август недели:", aug_w)
print("июль доход/мес:", sum(jul_inc), "расход:", sum(jul_exp))
print("август доход/мес:", sum(aug_inc), "расход:", sum(aug_exp))
