# -*- coding: utf-8 -*-
"""
ДДС из iiko — ФИНАЛ. Всё из iiko живьём: остатки по счетам на конец каждого месяца
через /resto/api/v2/reports/balance/counteragents (подразделение «Фуд завод»).
Считает ДДС (прибыль→деньги, косвенный метод) помесячно за 2026 и «где деньги» по счетам.
Пишет: ддс_данные.json + ддс_данные_LOG.txt (со сверкой июня). Только чтение.
"""
import sys,os,re,json,hashlib,warnings,calendar,datetime
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import requests
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import almaty  # время завода — Алматы (UTC+5), не UTC раннера
HERE=os.path.dirname(os.path.abspath(__file__))
src=open(os.path.join(HERE,"iiko_export.py"),encoding="utf-8").read()
URL=re.search(r'URL\s*=\s*"([^"]+)"',src).group(1); LOGIN=re.search(r'LOGIN\s*=\s*"([^"]+)"',src).group(1); PASS=re.search(r'PASS\s*=\s*"([^"]+)"',src).group(1)
YEAR=2026; FZ="2aafb9a8-7c62-499f-80b7-c3935348b891"
LOG=open(os.path.join(HERE,"ддс_данные_LOG.txt"),"w",encoding="utf-8")
def log(*a):
    t=" ".join(str(x) for x in a); print(t); LOG.write(t+"\n"); LOG.flush()
s=requests.Session()
tok=s.get(f"{URL}/resto/api/auth",params={"login":LOGIN,"pass":hashlib.sha1(PASS.encode()).hexdigest()},verify=False,timeout=60).text.strip().strip('"')
log("iiko: авторизация ok")
def get(path,**p):
    p["key"]=tok; return s.get(f"{URL}{path}",params=p,verify=False,timeout=180)
ACC={a["id"]:(a.get("name") or "",a.get("type") or "") for a in get("/resto/api/v2/entities/accounts/list").json()}

PL={"INCOME","COST_OF_GOODS_SOLD","EXPENSES","OTHER_EXPENSES"}

today=almaty.today(); last_full=today-datetime.timedelta(days=1); lastm=last_full.month
# timestamp конца месяца mi (0=дек2025..lastm). конец месяца = 00:00 первого дня следующего.
def ts_of(mi):
    if mi==0: return datetime.date(YEAR,1,1)
    if mi<lastm: return datetime.date(YEAR,mi+1,1)
    return last_full+datetime.timedelta(days=1)  # текущий месяц: по последний полный день
def snapshot(d):
    """{acc_id: {'name','type','signed','api'}} остатки ФЗ на дату d (00:00)."""
    js=get("/resto/api/v2/reports/balance/counteragents",timestamp=d.strftime("%Y-%m-%dT00:00:00")).json()
    out={}
    for r in js:
        if r.get("department")!=FZ: continue
        a=r.get("account"); out[a]=out.get(a,0.0)+(r.get("sum") or 0)
    res={}
    for a,v in out.items():
        nm,tp=ACC.get(a,("",""))
        res[a]={"name":nm,"type":tp,"api":v}
    return res
SNAP={mi:snapshot(ts_of(mi)) for mi in range(0,lastm+1)}
log("снимки остатков получены:", ", ".join(f"m{mi}={ts_of(mi)}" for mi in range(0,lastm+1)))

def accs(mi): return SNAP[mi]
def bytype(mi,types): return sum(d["api"] for d in accs(mi).values() if d["type"] in types)
def byname(mi,subs):
    tot=0
    for d in accs(mi).values():
        n=d["name"].replace(" ","")
        if any(x.replace(" ","")[:12] in n for x in subs): tot+=d["api"]
    return tot
def cash_accounts(mi): return {d["name"]:round(d["api"]) for d in accs(mi).values() if _is_active(d["name"]) and abs(d["api"])>0.5}
PLTYPES={"INCOME","COST_OF_GOODS_SOLD","EXPENSES","OTHER_EXPENSES","OTHER_INCOME"}
def month_pl(mi):
    """Чистая прибыль за месяц mi через ОБОРОТ P&L-счетов из проводок ФЗ (надёжно)."""
    import calendar as _cal, datetime as _dt
    d1=_dt.date(YEAR,mi,1)
    eom=_dt.date(YEAR,mi,_cal.monthrange(YEAR,mi)[1]); d2=min(eom,last_full)
    body={"reportType":"TRANSACTIONS","buildSummary":"true",
          "groupByRowFields":["Account.Type"],"aggregateFields":["Sum.Incoming","Sum.Outgoing"],
          "filters":{"DateTime.DateTyped":{"filterType":"DateRange","periodType":"CUSTOM",
                     "from":d1.isoformat(),"to":(d2+_dt.timedelta(days=1)).isoformat(),"includeLow":True,"includeHigh":True},
                     "Department":{"filterType":"IncludeValues","values":["Фуд завод"]}}}
    r=s.post(f"{URL}/resto/api/v2/reports/olap",headers={"Cookie":f"key={tok}","Content-Type":"application/json"},data=json.dumps(body),verify=False,timeout=180)
    prof=0; _brk={}
    if r.status_code==200:
        for row in r.json().get("data",[]):
            t=row.get("Account.Type"); nt=-((row.get("Sum.Incoming") or 0)-(row.get("Sum.Outgoing") or 0))
            _brk[t]=_brk.get(t,0)+nt
            if t in PLTYPES: prof+=nt
    try:
        _p=", ".join("{}:{:,.0f}".format(k,v) for k,v in sorted(_brk.items(),key=lambda x:-abs(x[1])))
        log("  [P&L {:02d}] {}  => прибыль {:,.0f}".format(mi,_p,prof))
    except Exception: pass
    return prof

REC=["4-Подотчет","Авансы выданные","5-Дебит.задолж","Расчеты с гостями"]
PAY=["Текущие расчеты с сотрудниками","Задолженность перед поставщиками","Бонусы РасчетыС Поставщик"]
FIN=["3050 ВФП","Кредиты полученные"]
OSN=["7- Основные средства"]

ACTIVE_CASH=["99Главная касса","Касса Взаиморасчеты","ФЗ Айдана каспи","ФЗ ДЕПОЗИТ каспи","ФЗ Ермагамбет отдел продаж","ФЗ Жусан Банк","ФЗ Каспи","ФЗ Каспи копилка","ФЗ РБК Каламкас","Цой Д.Л.Каспи"]
_ACTN=set(a.replace(" ","").lower() for a in ACTIVE_CASH)
def _is_active(nm): return (nm or "").replace(" ","").lower() in _ACTN
# Фильтра по типу счёта здесь больше нет: депозитный счёт заведён в iiko не
# типом «Денежные средства», и вместе с типом из «денег» выпадали 7,3 млн ₸.
# Список ACTIVE_CASH ведём руками — имя счёта и есть решение.
def cash(mi): return sum(d["api"] for d in accs(mi).values() if _is_active(d["name"]))
def inv_total(mi): return bytype(mi,{"INVENTORY_ASSETS","STORES","STORE"})
def inv_stores(mi):
    out={}
    for d in accs(mi).values():
        if d["type"] in {"INVENTORY_ASSETS","STORES","STORE"}:
            out[d["name"]]=out.get(d["name"],0.0)+d["api"]
    return out
SYR="склад (сырье)"   # «Основной склад (сырье) ФЗ» — реальный товар/сырьё
def inv(mi):  return sum(v for n,v in inv_stores(mi).items() if SYR in (n or "").lower())

# Денежные счета iiko, которых нет в ACTIVE_CASH: чтобы новый счёт больше не
# появлялся незаметно для ДДС. Пишем в лог, в отчёт это не попадает.
_miss=sorted({d["name"] for d in accs(lastm).values()
              if d["type"]=="CASH" and not _is_active(d["name"])})
if _miss: log("ВНИМАНИЕ: денежные счета iiko вне списка ДДС: "+"; ".join(_miss))
log("счетов в ДДС: %d" % len(ACTIVE_CASH))

months={}
for mi in range(1,lastm+1):
    start=cash(mi-1); end=cash(mi)
    dInv=-(inv(mi)-inv(mi-1))                     # -(Δ склад): снижение запасов -> +деньги
    dRec=-(byname(mi,REC)-byname(mi-1,REC))       # -(Δ дебиторка)
    dPay=-(byname(mi,PAY)-byname(mi-1,PAY))       # -(Δ кредиторка, api<0 -> рост долга даёт +деньги)
    invf=-(byname(mi,OSN)-byname(mi-1,OSN))       # -(Δ ОС)
    finf=-(byname(mi,FIN)-byname(mi-1,FIN))       # -(Δ ВФП+кредиты)
    prof=month_pl(mi)
    interimOp=prof+dInv+dRec+dPay
    net=end-start; op=net-invf-finf; nonCash=op-interimOp
    months[f"{YEAR}-{mi:02d}"]={"label":f"{YEAR}-{mi:02d}","start":round(start),"end":round(end),
        "prof":round(prof),"amort":0,"dInv":round(dInv),"dRec":round(dRec),"dPay":round(dPay),
        "interimOp":round(interimOp),"nonCash":round(nonCash),"op":round(op),"inv":round(invf),
        "fin":round(finf),"cashByAccount":cash_accounts(mi),
        "assets":{"cash":round(cash(mi)),"inv":round(inv(mi)),"rec":round(byname(mi,REC)),"os":round(byname(mi,OSN))},
        "debts":{"pay":round(-byname(mi,PAY)),"fin":round(-byname(mi,FIN))}}

data={"updated":today.strftime("%d.%m.%Y"),"through":last_full.strftime("%d.%m.%Y"),"months":months,
      "cashNow":cash_accounts(lastm),
      "cashHistory":{f"{YEAR}-{mi:02d}":cash_accounts(mi) for mi in range(1,lastm+1)},
      "invStores":{f"{YEAR}-{mi:02d}":{n:round(v) for n,v in inv_stores(mi).items()} for mi in range(1,lastm+1)}}
json.dump(data,open(os.path.join(HERE,"ддс_данные.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)

# ---- сверка июня ----
log("\n===== СВЕРКА ИЮНЯ (из iiko) vs эталон =====")
T={"start":13877183,"end":12467163,"prof":12147436,"dInv":14514335,"dRec":-24218570,"dPay":6661476,"inv":-1202056,"fin":-2763821}
m6=months.get(f"{YEAR}-06",{})
for k,tg in T.items():
    g=m6.get(k,0); d=g-tg; mk="OK" if abs(d)<abs(tg)*0.01+1 else ("~" if abs(d)<abs(tg)*0.05+1 else "!!!")
    log(f"   {k:6}: {g:>15,.0f}  эталон {tg:>15,.0f}  Δ {d:>+12,.0f}  {mk}")
log("\nОстаток денег по месяцам:")
for mi in range(1,lastm+1): log(f"   {YEAR}-{mi:02d}: старт {cash(mi-1):>14,.0f} -> конец {cash(mi):>14,.0f}   прибыль {month_pl(mi):>14,.0f}")
log("\nЗапасы по месяцам (сырьё / все склады):")
for mi in range(0,lastm+1): log(f"   m{mi} ({ts_of(mi)}): сырьё {inv(mi):>15,.0f}   все склады {inv_total(mi):>15,.0f}")
log("\nГОТОВО -> ддс_данные.json"); LOG.close(); print("OK")
