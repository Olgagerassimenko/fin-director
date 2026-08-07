# -*- coding: utf-8 -*-
"""Помесячные итоги КЗ и ДЗ (на конец месяца) из Google-таблицы «Баланс по поставщикам и дебиторам».
Пишет дз_кз_месяцы.json = {"2026-01":{"kz":..,"dz":..},...}. Только чтение."""
import sys,csv,io,json,re,datetime,requests,warnings
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8")
import os
HERE=os.path.dirname(os.path.abspath(__file__))
SHEET="13iFd16Hah1Yi5y2QptmyUrw51rSFfAmtnzhf0U2g_wc"; KZ_GID="2005257911"; DZ_GID="597090672"
LOG=open(os.path.join(HERE,"дз_кз_месяцы_LOG.txt"),"w",encoding="utf-8")
def log(*a):
    t=" ".join(str(x) for x in a);print(t);LOG.write(t+"\n");LOG.flush()
def fetch(gid):
    r=requests.get(f"https://docs.google.com/spreadsheets/d/{SHEET}/export?format=csv&gid={gid}",timeout=40)
    r.raise_for_status()
    try: txt=r.content.decode("utf-8-sig")
    except: txt=r.content.decode("cp1251",errors="replace")
    return list(csv.reader(io.StringIO(txt)))
def num(v):
    if v is None: return None
    v=str(v).replace(" ","").replace("\xa0","").replace(",",".").strip()
    try: return float(v)
    except: return None
def find_header(rows,pat,scan=15):
    rx=re.compile(pat,re.I|re.U)
    for i,row in enumerate(rows[:scan]):
        if any(rx.search(str(c)) for c in row): return i,row
    return None,None
def is_company(n):
    if not n or len(n.strip())<3: return False
    sk=["итого","всего","поставщик","кредит","ставят","стоп","нам должны","мы должны","дебитор","статус","---","коэфиц"]
    nl=n.lower();return not any(k in nl for k in sk)
def dated_cols(header,pat):
    out=[]
    for i,c in enumerate(header):
        c=str(c)
        if re.search(pat,c,re.I|re.U):
            m=re.search(r"(\d{1,2}\.\d{1,2}\.\d{2,4})",c)
            if m:
                d,mo,y=m.group(1).split(".")
                y="20"+y if len(y)==2 else y
                try: out.append((i,datetime.date(int(y),int(mo),int(d))))
                except: pass
    return out
def month_pick(cols):
    """для каждого месяца 2026 — колонка с последней датой в этом месяце"""
    res={}
    for i,dt in cols:
        if dt.year!=2026: continue
        k=f"2026-{dt.month:02d}"
        if k not in res or dt>res[k][1]: res[k]=(i,dt)
    return res
def main():
    log("=== ДЗ/КЗ помесячно из Google ===")
    kz=fetch(KZ_GID); dz=fetch(DZ_GID)
    log(f"КЗ строк {len(kz)}, ДЗ строк {len(dz)}")
    out={}
    # КЗ — по строке ИТОГО
    hi,h=find_header(kz,r"задолженность\s+на|кз\s+на")
    cols=dated_cols(h,r"задолженность\s+на|кз\s+на") if h else []
    itogo=None
    for row in kz[hi+1:] if hi is not None else []:
        if row and str(row[0]).strip().upper()=="ИТОГО": itogo=row;break
    kzm=month_pick(cols)
    log(f"КЗ: колонок {len(cols)}, ИТОГО {'есть' if itogo else 'нет'}, месяцев {len(kzm)}")
    for k,(i,dt) in sorted(kzm.items()):
        v=num(itogo[i]) if (itogo and i<len(itogo)) else None
        out.setdefault(k,{})["kz"]=round(abs(v)) if v else None
        out[k]["kz_date"]=dt.strftime("%d.%m.%Y")
    # ДЗ — сумма положительных по компаниям
    hi2,h2=find_header(dz,r"дз\s+на|д/з\s+на|д\.з\.\s*на|задолженность\s+на")
    cols2=dated_cols(h2,r"дз\s+на|д/з\s+на|д\.з\.\s*на|задолженность\s+на") if h2 else []
    dzm=month_pick(cols2)
    log(f"ДЗ: колонок {len(cols2)}, месяцев {len(dzm)}")
    for k,(i,dt) in sorted(dzm.items()):
        s=0.0
        for row in dz[hi2+1:]:
            if not is_company(row[0] if row else ""): continue
            v=num(row[i]) if i<len(row) else None
            if v and v>0: s+=v
        out.setdefault(k,{})["dz"]=round(s); out[k]["dz_date"]=dt.strftime("%d.%m.%Y")
    out["updated"]=datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    json.dump(out,open(os.path.join(HERE,"дз_кз_месяцы.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    log("\nПОМЕСЯЧНО:")
    for k in sorted(out):
        if k.startswith("2026"): log(f"   {k}: КЗ={out[k].get('kz'):>14,} ({out[k].get('kz_date')})   ДЗ={out[k].get('dz'):>14,} ({out[k].get('dz_date')})")
    log("ГОТОВО -> дз_кз_месяцы.json"); LOG.close(); print("OK")
def _rebuild_dz_kz_page():
    """Пересобрать страницу /дз_кз (dz_kz.js) из того же Google-файла — чтобы она
    обновлялась автоматически в пульсе, а не только локальным батом."""
    import subprocess
    p=os.path.join(HERE,"parse_dz_kz.py")
    if not os.path.exists(p):
        print("parse_dz_kz.py рядом не найден — пересборку страницы ДЗ/КЗ пропускаю")
        return
    try:
        subprocess.run([sys.executable,p],check=False,cwd=HERE)
        print("страница ДЗ/КЗ пересобрана (dz_kz.js)")
    except Exception as e:
        print("парсер ДЗ/КЗ пропущен:",e)

if __name__=="__main__":
    main()
    _rebuild_dz_kz_page()
