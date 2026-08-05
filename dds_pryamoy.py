# -*- coding: utf-8 -*-
"""
ДДС ПРЯМОЙ МЕТОД из iiko — по статьям и ПО КАЖДОМУ СЧЁТУ (как отчёт ДДС в iiko).
Колонки = 9 активных счетов + Итого. Строки = Остаток на начало, статьи (Приход/Расход),
Остаток на конец. Плюс разбивка Выручки по контрагентам (от кого), отсортировано.
Разрезы: год (закрытые месяцы), месяцы 2026, последние дни. Только чтение.
Пишет ддс_прямой.json + ддс_прямой_LOG.txt.
"""
import sys,os,re,json,hashlib,warnings,datetime
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import requests
import concurrent.futures as _cf
_POOL=8   # параллельные запросы к iiko (логика та же, ускоряется только время прогона)
HERE=os.path.dirname(os.path.abspath(__file__))
src=open(os.path.join(HERE,"iiko_export.py"),encoding="utf-8").read()
URL=re.search(r'URL\s*=\s*"([^"]+)"',src).group(1);LOGIN=re.search(r'LOGIN\s*=\s*"([^"]+)"',src).group(1);PASS=re.search(r'PASS\s*=\s*"([^"]+)"',src).group(1)
YEAR=2026; FZ="2aafb9a8-7c62-499f-80b7-c3935348b891"
ACTIVE=["99Главная касса","Касса Взаиморасчеты","ФЗ Айдана каспи","ФЗ Жусан Банк","ФЗ Каспи","ФЗ Каспи копилка","ФЗ РБК Каламкас","Цой Д.Л.Каспи"]
SHORT={"99Главная касса":"Гл. касса","Касса Взаиморасчеты":"Взаиморасчёты","ФЗ Айдана каспи":"Айдана","ФЗ Жусан Банк":"Жусан","ФЗ Каспи":"Каспи","ФЗ Каспи копилка":"Каспи копилка","ФЗ РБК Каламкас":"РБК Каламкас","Цой Д.Л.Каспи":"Цой Д.Л."}
_ACT=set(ACTIVE); REVCAT="1.Выручка"
_NORM={a.replace(" ","").lower():a for a in ACTIVE}
def _canon(nm): return _NORM.get((nm or "").replace(" ","").lower())
LOG=open(os.path.join(HERE,"ддс_прямой_LOG.txt"),"w",encoding="utf-8")
def log(*a):
    t=" ".join(str(x) for x in a); print(t); LOG.write(t+"\n"); LOG.flush()
s=requests.Session()
tok=s.get(f"{URL}/resto/api/auth",params={"login":LOGIN,"pass":hashlib.sha1(PASS.encode()).hexdigest()},verify=False,timeout=60).text.strip().strip('"')
log("iiko: авторизация ok")
ACC={a["id"]:(a.get("name") or "",a.get("type") or "") for a in s.get(f"{URL}/resto/api/v2/entities/accounts/list",params={"key":tok},verify=False,timeout=120).json()}

def _olap(body):
    r=s.post(f"{URL}/resto/api/v2/reports/olap",headers={"Cookie":f"key={tok}","Content-Type":"application/json"},data=json.dumps(body),verify=False,timeout=180)
    return r.json().get("data",[]) if r.status_code==200 else []

# ---- остатки по каждому счёту на дату ----
def cash_by_acc(d):
    js=s.get(f"{URL}/resto/api/v2/reports/balance/counteragents",params={"key":tok,"timestamp":d.strftime("%Y-%m-%dT00:00:00")},verify=False,timeout=180).json()
    res={a:0.0 for a in ACTIVE}
    for r in js:
        if r.get("department")!=FZ: continue
        nm,tp=ACC.get(r.get("account"),("",""))
        c=_canon(nm)
        if tp=="CASH" and c: res[c]+=(r.get("sum") or 0)
    return {k:round(v) for k,v in res.items()}

# ---- статьи по счетам за период [d1,d2) ----
def articles(d1,d2):
    body={"reportType":"TRANSACTIONS","buildSummary":"true",
          "groupByRowFields":["CashFlowCategory.Type","CashFlowCategory","Account.Name"],
          "aggregateFields":["Sum.Incoming","Sum.Outgoing"],
          "filters":{"DateTime.DateTyped":{"filterType":"DateRange","periodType":"CUSTOM","from":d1.isoformat(),"to":d2.isoformat(),"includeLow":True,"includeHigh":False},
                     "Department":{"filterType":"IncludeValues","values":["Фуд завод"]},
                     "Account.Name":{"filterType":"IncludeValues","values":ACTIVE}}}
    agg={}
    for row in _olap(body):
        cat=row.get("CashFlowCategory")
        if cat is None: continue
        acc=_canon(row.get("Account.Name"))
        if not acc: continue
        inc=round(row.get("Sum.Incoming") or 0); o=round(row.get("Sum.Outgoing") or 0)
        if inc==0 and o==0: continue
        key=(row.get("CashFlowCategory.Type") or "OTHER",cat)
        e=agg.setdefault(key,{"type":key[0],"cat":cat,"in":0,"out":0,"net":0,"byAcc":{}})
        e["in"]+=inc; e["out"]+=o; e["net"]+=inc-o
        b=e["byAcc"].setdefault(acc,{"in":0,"out":0})
        b["in"]+=inc; b["out"]+=o
    out=list(agg.values()); out.sort(key=lambda x:-abs(x["net"]))
    return out

# ---- выручка по контрагентам (от кого) ----
def revenue_by_contr(d1,d2):
    body={"reportType":"TRANSACTIONS","buildSummary":"true",
          "groupByRowFields":["Counteragent.Name"],
          "aggregateFields":["Sum.Incoming","Sum.Outgoing"],
          "filters":{"DateTime.DateTyped":{"filterType":"DateRange","periodType":"CUSTOM","from":d1.isoformat(),"to":d2.isoformat(),"includeLow":True,"includeHigh":False},
                     "Department":{"filterType":"IncludeValues","values":["Фуд завод"]},
                     "Account.Name":{"filterType":"IncludeValues","values":ACTIVE},
                     "CashFlowCategory":{"filterType":"IncludeValues","values":[REVCAT]}}}
    out=[]
    for row in _olap(body):
        nm=row.get("Counteragent.Name") or "— без контрагента"
        inc=round(row.get("Sum.Incoming") or 0); o=round(row.get("Sum.Outgoing") or 0)
        net=inc-o
        if net==0: continue
        out.append({"name":nm,"net":net})
    out.sort(key=lambda x:-x["net"])
    return out

# ---- дневная детализация за весь период (для произвольного выбора дат) ----
def daily_all(d1,d2):
    body={"reportType":"TRANSACTIONS","buildSummary":"true",
          "groupByRowFields":["DateTime.DateTyped","CashFlowCategory.Type","CashFlowCategory","Account.Name"],
          "aggregateFields":["Sum.Incoming","Sum.Outgoing"],
          "filters":{"DateTime.DateTyped":{"filterType":"DateRange","periodType":"CUSTOM","from":d1.isoformat(),"to":d2.isoformat(),"includeLow":True,"includeHigh":False},
                     "Department":{"filterType":"IncludeValues","values":["Фуд завод"]},
                     "Account.Name":{"filterType":"IncludeValues","values":ACTIVE}}}
    byDay={}
    for row in _olap(body):
        cat=row.get("CashFlowCategory")
        if cat is None: continue
        acc=_canon(row.get("Account.Name"))
        if not acc: continue
        dt=str(row.get("DateTime.DateTyped") or "")[:10]
        if len(dt)!=10: continue
        net=round(row.get("Sum.Incoming") or 0)-round(row.get("Sum.Outgoing") or 0)
        if net==0: continue
        day=byDay.setdefault(dt,{})
        key=(row.get("CashFlowCategory.Type") or "OTHER")+"|"+cat
        e=day.setdefault(key,{"t":row.get("CashFlowCategory.Type") or "OTHER","c":cat,"a":{}})
        idx=ACTIVE.index(acc); e["a"][idx]=e["a"].get(idx,0)+net
    return {d:list(v.values()) for d,v in byDay.items()}
def daily_rev(d1,d2):
    body={"reportType":"TRANSACTIONS","buildSummary":"true",
          "groupByRowFields":["DateTime.DateTyped","Counteragent.Name"],
          "aggregateFields":["Sum.Incoming","Sum.Outgoing"],
          "filters":{"DateTime.DateTyped":{"filterType":"DateRange","periodType":"CUSTOM","from":d1.isoformat(),"to":d2.isoformat(),"includeLow":True,"includeHigh":False},
                     "Department":{"filterType":"IncludeValues","values":["Фуд завод"]},
                     "Account.Name":{"filterType":"IncludeValues","values":ACTIVE},
                     "CashFlowCategory":{"filterType":"IncludeValues","values":[REVCAT]}}}
    byDay={}
    for row in _olap(body):
        dt=str(row.get("DateTime.DateTyped") or "")[:10]
        if len(dt)!=10: continue
        net=round(row.get("Sum.Incoming") or 0)-round(row.get("Sum.Outgoing") or 0)
        if net==0: continue
        nm=row.get("Counteragent.Name") or "— без контрагента"
        byDay.setdefault(dt,[]).append({"n":nm,"v":net})
    return byDay
def daily_net_acc(d1,d2):
    # дневное движение по КАЖДОМУ счёту, БЕЗ фильтра статьи — ловит все движения (для точных остатков)
    body={"reportType":"TRANSACTIONS","buildSummary":"true",
          "groupByRowFields":["DateTime.DateTyped","Account.Name"],
          "aggregateFields":["Sum.Incoming","Sum.Outgoing"],
          "filters":{"DateTime.DateTyped":{"filterType":"DateRange","periodType":"CUSTOM","from":d1.isoformat(),"to":d2.isoformat(),"includeLow":True,"includeHigh":False},
                     "Department":{"filterType":"IncludeValues","values":["Фуд завод"]},
                     "Account.Name":{"filterType":"IncludeValues","values":ACTIVE}}}
    dn={}
    for row in _olap(body):
        dt=str(row.get("DateTime.DateTyped") or "")[:10]
        if len(dt)!=10: continue
        acc=_canon(row.get("Account.Name"))
        if not acc: continue
        net=round(row.get("Sum.Incoming") or 0)-round(row.get("Sum.Outgoing") or 0)
        dn.setdefault(dt,{}); dn[dt][acc]=dn[dt].get(acc,0)+net
    return dn

today=datetime.date.today(); last_full=today-datetime.timedelta(days=1); lastm=last_full.month
def eom(mi): return datetime.date(YEAR,mi+1,1) if mi<lastm else last_full+datetime.timedelta(days=1)
def bom(mi): return datetime.date(YEAR,mi,1)

# балансы на границах месяцев (кэш)
_balcache={}
def bal(d):
    k=d.isoformat()
    if k not in _balcache: _balcache[k]=cash_by_acc(d)
    return _balcache[k]

# ---- Продуктовая себестоимость из ОПиУ (счёт «Себестоимость продуктовая»), оборот по месяцам ----
def cogs_month(mi):
    d1=bom(mi); d2=eom(mi)
    body={"reportType":"TRANSACTIONS","buildSummary":"true",
          "groupByRowFields":["Account.Name"],
          "aggregateFields":["Sum.Incoming","Sum.Outgoing"],
          "filters":{"DateTime.DateTyped":{"filterType":"DateRange","periodType":"CUSTOM","from":d1.isoformat(),"to":d2.isoformat(),"includeLow":True,"includeHigh":False},
                     "Department":{"filterType":"IncludeValues","values":["Фуд завод"]}}}
    tot=0.0; matched=[]
    for row in _olap(body):
        nm=row.get("Account.Name") or ""
        if re.search(r"себестоимост.*продукт|продуктов.*себестоимост",nm,re.I):
            v=(row.get("Sum.Outgoing") or 0)-(row.get("Sum.Incoming") or 0)
            tot+=v; matched.append((nm,round(v)))
    return round(tot),matched

cogs_auto={}
log("  Продуктовая себестоимость (счёт ОПиУ) по месяцам — СВЕРКА:")
_mis=list(range(1,lastm+1))
with _cf.ThreadPoolExecutor(max_workers=_POOL) as _ex:
    _cres=list(_ex.map(cogs_month,_mis))
for mi,(v,matched) in zip(_mis,_cres):
    cogs_auto[f"{YEAR}-{mi:02d}"]=v
    log(f"    {YEAR}-{mi:02d}: {v:>15,.0f}   [{'; '.join(f'{n}={x:,.0f}' for n,x in matched) if matched else 'нет совпадений по имени счёта'}]")

months={}
def _month_fetch(mi):
    d1=bom(mi); d2=eom(mi)
    return (mi,d1,d2,articles(d1,d2),cash_by_acc(d1),cash_by_acc(d2),revenue_by_contr(d1,d2))
with _cf.ThreadPoolExecutor(max_workers=_POOL) as _ex:
    _mres=list(_ex.map(_month_fetch,range(1,lastm+1)))
for mi,d1,d2,arts,st,en,rev in _mres:
    _balcache[d1.isoformat()]=st; _balcache[d2.isoformat()]=en   # переиспользуем для года и дневных остатков
    sIn=sum(a["in"] for a in arts if not re.search(r"внутрен|внутригрупп",a["cat"],re.I))
    sOut=sum(a["out"] for a in arts if not re.search(r"внутрен|внутригрупп",a["cat"],re.I))
    stTot=sum(st.values()); enTot=sum(en.values())
    months[f"{YEAR}-{mi:02d}"]={"startByAcc":st,"endByAcc":en,"start":stTot,"end":enTot,"net":enTot-stTot,
        "articles":arts,"revByContr":rev}
    log(f"  {YEAR}-{mi:02d}: старт {stTot:,.0f} -> конец {enTot:,.0f} | статей {len(arts)} | контрагентов выручки {len(rev)}")

# последние дни (по счетам, без разбивки выручки)
days={}
_dds=[last_full-datetime.timedelta(days=k-1) for k in range(14,0,-1)]
def _day_fetch(d): return (d,articles(d,d+datetime.timedelta(days=1)))
with _cf.ThreadPoolExecutor(max_workers=_POOL) as _ex:
    for d,arts in _ex.map(_day_fetch,_dds):
        if arts:
            days[d.isoformat()]={"net":round(sum(a["net"] for a in arts)),"articles":arts}

# год: агрегируем закрытые месяцы (закрыт если сегодня >= 18 след.месяца)
def closed(mi):
    cd=datetime.date(YEAR if mi<12 else YEAR+1, mi+1 if mi<12 else 1, 18); return today>=cd
ymonths=[mi for mi in range(1,lastm+1) if closed(mi)]
year={"from":"","to":"","startByAcc":{},"endByAcc":{},"start":0,"end":0,"net":0,"articles":[],"revByContr":[]}
if ymonths:
    d1=bom(ymonths[0]); d2=eom(ymonths[-1])
    yst=bal(d1); yen=bal(d2)
    yarts=articles(d1,d2); yrev=revenue_by_contr(d1,d2)
    year={"from":f"{YEAR}-{ymonths[0]:02d}","to":f"{YEAR}-{ymonths[-1]:02d}",
          "startByAcc":yst,"endByAcc":yen,"start":sum(yst.values()),"end":sum(yen.values()),
          "net":sum(yen.values())-sum(yst.values()),"articles":yarts,"revByContr":yrev}
    log(f"  ГОД {year['from']}..{year['to']}: старт {year['start']:,.0f} -> конец {year['end']:,.0f} | статей {len(yarts)} | контрагентов {len(yrev)}")

log("  дневная детализация для произвольного периода...")
allD1=datetime.date(YEAR,1,1); allD2=last_full+datetime.timedelta(days=1)
with _cf.ThreadPoolExecutor(max_workers=2) as _ex:
    _fa=_ex.submit(daily_all,allD1,allD2); _fr=_ex.submit(daily_rev,allD1,allD2)
    byDay=_fa.result(); byDayRev=_fr.result()
log("  дней с движением: %d"%len(byDay))
# дневные остатки по счетам — ТОЧНЫЕ снимки баланса (balance на каждый день с движением)
balByDay={}; cur=datetime.date(YEAR,1,1); endcur=last_full+datetime.timedelta(days=1)
# заранее параллельно тянем нужные снимки баланса: Jan1 + (день+1) для каждого дня с движением
_need=[cur]; _c=cur
while _c<=endcur:
    if _c.isoformat() in byDay: _need.append(_c+datetime.timedelta(days=1))
    _c+=datetime.timedelta(days=1)
_todo=[d for d in _need if d.isoformat() not in _balcache]
with _cf.ThreadPoolExecutor(max_workers=_POOL) as _ex:
    for d,res in zip(_todo,_ex.map(cash_by_acc,_todo)):
        _balcache[d.isoformat()]=res
_calls=len(_todo)
snap=bal(cur)  # точный остаток на начало Jan1 (из кэша)
while cur<=endcur:
    k=cur.isoformat(); balByDay[k]=snap
    if k in byDay:  # был день движения -> берём точный остаток на начало следующего дня
        snap=bal(cur+datetime.timedelta(days=1))
    cur+=datetime.timedelta(days=1)
_chk=sum(balByDay.get(f"{YEAR}-02-01",{}).values())
log("  дневные остатки: снимков баланса %d; сверка на 01.02: %d (эталон 34 391 753, Δ %d)"%(_calls,_chk,_chk-34391753))

RUM={1:"январь",2:"февраль",3:"март",4:"апрель",5:"май",6:"июнь",7:"июль",8:"август",9:"сентябрь",10:"октябрь",11:"ноябрь",12:"декабрь"}
mmeta={f"{YEAR}-{mi:02d}":{"ru":f"{RUM[mi]} {YEAR}","closed":closed(mi)} for mi in range(1,lastm+1)}
data={"updated":today.strftime("%d.%m.%Y"),"updatedFull":today.strftime("%d.%m.%Y ")+datetime.datetime.now().strftime("%H:%M"),
      "through":last_full.strftime("%d.%m.%Y"),
      "accounts":ACTIVE,"short":SHORT,"months":months,"mmeta":mmeta,"days":days,"year":year,"cogs_auto":cogs_auto,
      "byDay":byDay,"byDayRev":byDayRev,"balByDay":balByDay,
      "dayMin":(min(byDay) if byDay else ""),"dayMax":(max(byDay) if byDay else "")}
json.dump(data,open(os.path.join(HERE,"ддс_прямой.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
log("ГОТОВО -> ддс_прямой.json  (месяцев %d, дней %d)"%(len(months),len(days)))
LOG.close(); print("OK")
