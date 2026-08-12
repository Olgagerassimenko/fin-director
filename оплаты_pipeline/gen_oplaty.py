# -*- coding: utf-8 -*-
"""Пересобирает отчёт «Согласованные оплаты» из данных (≡-формат) на базе шаблона.
Данные: строки  Дата≡Тип≡Заявитель≡Город≡Сумма≡Статус≡Комментарий≡Файл
Меняет только блок <script id="raw"> и CFG={period,asof}. Весь вид/аналитика — из шаблона."""
import re, sys, datetime, os
HERE=os.path.dirname(os.path.abspath(__file__))
TPL=os.path.join(HERE,"оплаты_шаблон.html")
DATA=sys.argv[1] if len(sys.argv)>1 else os.path.join(HERE,"oplaty_data.txt")
OUT=sys.argv[2] if len(sys.argv)>2 else os.path.join(HERE,"bitrix_отчёт_оплаты.html")

def mm_key(d):
    m=re.match(r"(\d{2})\.(\d{2})",d.strip())
    if not m: return (99,99)
    return (int(m.group(2)),int(m.group(1)))  # (месяц,день)

raw=open(DATA,encoding="utf-8").read().strip("\n")
lines=[l for l in raw.split("\n") if l.strip()]
# период = от самой ранней до самой поздней даты
ds=[l.split("≡")[0].strip() for l in lines if "≡" in l]
ds=[d for d in ds if re.match(r"^\d{2}\.\d{2}$",d)]
ds_sorted=sorted(set(ds), key=mm_key)
now=datetime.datetime.utcnow()+datetime.timedelta(hours=5)  # Алматы
year=now.year
period=f"{ds_sorted[0]}.{year} – {ds_sorted[-1]}.{year}" if ds_sorted else ""
asof=f"{now:%d.%m.%Y}"

html=open(TPL,encoding="utf-8").read()
# 1) подменяем блок raw
new_raw='<script type="text/plain" id="raw">\n'+raw+'\n</script>'
html=re.sub(r'<script[^>]*id="raw"[^>]*>.*?</script>', lambda m:new_raw, html, count=1, flags=re.S)
# 2) подменяем CFG
html=re.sub(r'CFG=\{period:"[^"]*",\s*asof:"[^"]*"\}',
            f'CFG={{period:"{period}", asof:"{asof}"}}', html, count=1)
open(OUT,"w",encoding="utf-8").write(html)
print(f"OK · строк: {len(lines)} · период {period} · на {asof}")
print("out:",OUT)
