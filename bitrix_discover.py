# -*- coding: utf-8 -*-
"""Поиск смарт-процесса «заявки на оплату» и воронок Алматы/Астана в Битрикс24."""
import os, json, re, warnings
warnings.filterwarnings("ignore")
import requests

_raw = os.environ["BITRIX_WEBHOOK"].strip()
_m = re.match(r'^(https?://[^/]+/rest/\d+/[A-Za-z0-9]+/)', _raw)
WEBHOOK = _m.group(1) if _m else (_raw.rstrip("/") + "/")

LOG = open("bitrix_discover_log.txt", "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

def call(method, **params):
    try:
        r = requests.post(WEBHOOK + method, json=params, timeout=90)
        return r.json()
    except Exception as e:
        return {"__error__": f"{type(e).__name__}: {e}"}

# 1. Собираем entityTypeId из стадий (DYNAMIC_<id>_STAGE) + сделки(2) + счёт(31)
st = (call("crm.status.list", order={"SORT":"ASC"}, filter={}).get("result")) or []
etids = set()
for s in st:
    m = re.match(r'DYNAMIC_(\d+)_STAGE', str(s.get("ENTITY_ID") or ""))
    if m: etids.add(int(m.group(1)))
etids = sorted(etids) + [2, 31]
log(f"Найдено смарт-процессов (entityTypeId): {len(etids)}\n")

# 2. По каждому — название типа и воронки (категории)
out = {"processes": {}}
for etid in etids:
    tp = call("crm.type.get", id=etid)
    title = ((tp.get("result") or {}).get("type") or {}).get("title") if isinstance(tp, dict) else None
    cats_resp = call("crm.category.list", entityTypeId=etid)
    cats = ((cats_resp.get("result") or {}).get("categories")) or []
    catnames = [(c.get("id"), c.get("name")) for c in cats]
    out["processes"][etid] = {"title": title, "categories": catnames}
    flag = ""
    joined = " ".join(str(n) for _, n in catnames) + " " + str(title or "")
    if re.search(r'Алмат|Астан|оплат|Оплат|платеж|Платеж|заявк', joined, re.I):
        flag = "   <<< ВОЗМОЖНО ОПЛАТЫ"
    log(f"[{etid}] {title!r}  воронки: {catnames}{flag}")

json.dump(out, open("bitrix_discover_out.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
log("\nГОТОВО")
LOG.close()
