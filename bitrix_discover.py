# -*- coding: utf-8 -*-
"""
Разведка структуры Битрикс24 через входящий вебхук (только чтение).
Находит: смарт-процессы, воронки (категории), стадии, поля, примеры элементов —
чтобы понять, где Алматы/Астана, где сумма, комментарий, дата, стадия «к оплате».
Пишет: bitrix_discover_out.json (полное) + bitrix_discover_log.txt (кратко).
"""
import os, json, warnings
warnings.filterwarnings("ignore")
import requests

WEBHOOK = os.environ["BITRIX_WEBHOOK"].strip().rstrip("/") + "/"
LOG = open("bitrix_discover_log.txt", "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

def call(method, **params):
    try:
        r = requests.post(WEBHOOK + method, json=params, timeout=90, verify=True)
        try:
            return r.json()
        except Exception:
            return {"__http__": r.status_code, "__text__": r.text[:500]}
    except Exception as e:
        return {"__error__": f"{type(e).__name__}: {e}"}

out = {}

# 0. Проверка вебхука
out["profile"] = call("profile")
p = out["profile"].get("result") if isinstance(out["profile"], dict) else None
if p:
    log("вебхук OK. Пользователь:", p.get("NAME"), p.get("LAST_NAME"), "| admin:", p.get("ADMIN"))
else:
    log("!! профиль не получен:", json.dumps(out["profile"], ensure_ascii=False)[:300])

# 1. Смарт-процессы (динамические типы)
out["crm.type.list"] = call("crm.type.list")
types = ((out["crm.type.list"].get("result") or {}).get("types")) or []
log(f"\nСмарт-процессов найдено: {len(types)}")
for t in types:
    log(f"  · {t.get('title')}  (entityTypeId={t.get('entityTypeId')}, id={t.get('id')})")

# 2. Воронки сделок (на случай, если оплаты — это сделки)
out["crm.dealcategory.list"] = call("crm.dealcategory.list")
dcats = (out["crm.dealcategory.list"].get("result")) or []
log(f"\nВоронки СДЕЛОК: {len(dcats)}")
for c in dcats:
    log(f"  · {c.get('NAME')}  (ID={c.get('ID')})")

# 3. Все стадии/статусы (чтобы найти «Согласовано/К оплате»)
out["crm.status.list"] = call("crm.status.list", order={"SORT":"ASC"}, filter={})
st = (out["crm.status.list"].get("result")) or []
log(f"\nСтатусов/стадий всего: {len(st)} (покажу связанные со стадиями):")
for s in st:
    ent = str(s.get("ENTITY_ID") or "")
    if "STAGE" in ent or "STATUS" in ent or ent.startswith("DYNAMIC"):
        log(f"  [{ent}] {s.get('STATUS_ID')} = {s.get('NAME')}")

# 4. По каждому смарт-процессу: воронки, поля, примеры
out["smart_processes"] = {}
for t in types:
    etid = t.get("entityTypeId")
    key = f"{t.get('title')}#{etid}"
    d = {}
    d["categories"] = call("crm.category.list", entityTypeId=etid)
    cats = ((d["categories"].get("result") or {}).get("categories")) or []
    log(f"\n=== Смарт-процесс «{t.get('title')}» (entityTypeId={etid}) ===")
    log(f"  Воронки: {len(cats)}")
    for c in cats:
        log(f"    · {c.get('name')} (id={c.get('id')})")
    d["fields"] = call("crm.item.fields", entityTypeId=etid)
    fields = ((d["fields"].get("result") or {}).get("fields")) or {}
    log(f"  Полей: {len(fields)} — список (код → название, тип):")
    for code, f in fields.items():
        log(f"    {code} → {f.get('title')} [{f.get('type')}]")
    # примеры элементов (первые несколько), все поля
    items_resp = call("crm.item.list", entityTypeId=etid, start=0, order={"id":"DESC"})
    items = ((items_resp.get("result") or {}).get("items")) or []
    d["sample_items"] = items[:5]
    log(f"  Элементов на первой странице: {len(items)}. Первые 3 (ключевые поля):")
    for it in items[:3]:
        log(f"    id={it.get('id')} cat={it.get('categoryId')} stage={it.get('stageId')} "
            f"opportunity={it.get('opportunity')} title={str(it.get('title'))[:40]}")
    out["smart_processes"][key] = d

# 5. Поля и примеры сделок (на всякий случай)
out["crm.deal.fields"] = call("crm.deal.fields")
out["crm.deal.list_sample"] = call("crm.deal.list", start=0, order={"ID":"DESC"},
                                   select=["ID","TITLE","CATEGORY_ID","STAGE_ID","OPPORTUNITY","COMMENTS","DATE_CREATE","CLOSEDATE"])
dsample = (out["crm.deal.list_sample"].get("result")) or []
log(f"\nПримеры сделок (первые 3):")
for dd in dsample[:3]:
    log(f"    ID={dd.get('ID')} cat={dd.get('CATEGORY_ID')} stage={dd.get('STAGE_ID')} "
        f"sum={dd.get('OPPORTUNITY')} title={str(dd.get('TITLE'))[:40]}")

json.dump(out, open("bitrix_discover_out.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
log("\nГОТОВО -> bitrix_discover_out.json")
LOG.close()
