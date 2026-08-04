# -*- coding: utf-8 -*-
"""
bitrix_report.py — робот по оплатам из Битрикс24 (только чтение).
Запускается в пайплайне; вебхук берётся из секрета BITRIX_WEBHOOK.

Задача: за день собрать согласованные к оплате заявки, по возможности разбить
Алматы/Астана, посчитать суммы, вытащить комментарии. Так как оплаты могут быть
бизнес-процессами (плохо читаются через REST), робот сперва РАЗВЕДЫВАЕТ, что вообще
доступно, и пишет:
    bitrix_log.txt              — что нашёл (это прислать Claude)
    bitrix_отчёт_оплаты.html    — отчёт (что удалось собрать)
"""
import os, json, urllib.request, urllib.error, datetime, re, sys

WH = (os.environ.get("BITRIX_WEBHOOK") or "").strip().rstrip("/")
LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitrix_log.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

def call(method, params=None):
    """REST-вызов вебхука. Возвращает (result, error)."""
    if not WH:
        return None, "нет BITRIX_WEBHOOK"
    url = WH + "/" + method + ".json"
    body = json.dumps(params or {}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.loads(r.read().decode("utf-8"))
            return j.get("result"), j.get("error_description") or j.get("error")
    except urllib.error.HTTPError as e:
        try: j = json.loads(e.read().decode("utf-8")); return None, j.get("error_description") or f"HTTP {e.code}"
        except Exception: return None, f"HTTP {e.code}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def main():
    today = datetime.date.today()
    log(f"Битрикс-робот · {today:%d.%m.%Y}")
    if not WH:
        log("[!] Секрет BITRIX_WEBHOOK не задан — робот не может подключиться."); return
    log(f"портал: {WH.split('/rest/')[0] if '/rest/' in WH else '—'}")

    # 0) диагностика структуры URL вебхука (без раскрытия токена)
    seg = WH.split("/rest/")
    log("URL содержит '/rest/':", len(seg) == 2)
    if len(seg) == 2:
        tail = [x for x in seg[1].strip("/").split("/") if x]
        log(f"  сегментов после /rest/: {len(tail)} | userId: {tail[0] if tail else '—'} | "
            f"длина токена: {len(tail[1]) if len(tail) > 1 else 0}")
        if len(tail) > 2:
            log(f"  [!] лишние сегменты в URL: {tail[2:]} — вебхук должен заканчиваться на userId/token/")
    # сырой ответ на profile (GET и POST, с .json и без) — чтобы увидеть реальную причину
    import urllib.request as _u
    for variant in (WH + "/profile.json", WH + "/profile"):
        try:
            with _u.urlopen(variant, timeout=30) as r:
                body = r.read().decode("utf-8", "replace")[:200]
            log(f"  GET {variant.split('/rest/')[0]}/rest/.../profile{'.json' if '.json' in variant else ''} → {body}")
        except Exception as e:
            log(f"  GET .../profile → {type(e).__name__}: {str(e)[:120]}")
    log("")

    # 1) авторизация / права
    prof, err = call("profile")
    log("profile:", "ok" if prof else f"ошибка — {err}")
    scope, err = call("scope")
    log("scope (права вебхука):", scope if scope else f"ошибка — {err}", "\n")

    found = {}

    # 2) смарт-процессы (лучший источник, если заявки как смарт-процесс)
    types, err = call("crm.type.list")
    if types and isinstance(types, dict) and types.get("types"):
        log("Смарт-процессы CRM:")
        for t in types["types"]:
            log(f"   entityTypeId={t.get('entityTypeId')}  «{t.get('title')}»")
            items, e2 = call("crm.item.list", {"entityTypeId": t.get("entityTypeId"),
                             "filter": {">=createdTime": today.isoformat()}, "start": 0})
            n = len(items.get("items", [])) if isinstance(items, dict) else 0
            log(f"      элементов за сегодня: {n}" + (f"  (ошибка: {e2})" if e2 else ""))
            if n: found.setdefault("Смарт-процесс «%s»" % t.get("title"), items["items"])
    else:
        log("Смарт-процессы: нет / нет доступа —", err)

    # 3) универсальные списки и списки бизнес-процессов
    for ibt in ("lists", "bitrix_processes"):
        lists, err = call("lists.get", {"IBLOCK_TYPE_ID": ibt})
        if lists and isinstance(lists, list):
            log(f"\nСписки ({ibt}):")
            for L in lists:
                log(f"   IBLOCK_ID={L.get('ID')}  «{L.get('NAME')}»")
        elif err:
            log(f"lists.get({ibt}): {err}")

    # 4) задачи за сегодня (оплаты могут быть задачами)
    tasks, err = call("tasks.task.list", {"filter": {">=CREATED_DATE": today.isoformat()},
                                          "select": ["ID", "TITLE", "CREATED_BY", "STATUS"]})
    if tasks and isinstance(tasks, dict) and tasks.get("tasks"):
        log(f"\nЗадачи за сегодня: {len(tasks['tasks'])}")
        for t in tasks["tasks"][:20]:
            log(f"   #{t.get('id')} {t.get('title')}")
    elif err:
        log("tasks.task.list:", err)

    # 5) сделки за сегодня
    deals, err = call("crm.deal.list", {"filter": {">=DATE_CREATE": today.isoformat()},
                                        "select": ["ID", "TITLE", "OPPORTUNITY", "STAGE_ID", "CATEGORY_ID"]})
    if deals and isinstance(deals, list):
        log(f"\nСделки за сегодня: {len(deals)}")
        for d in deals[:20]:
            log(f"   #{d.get('ID')} {d.get('TITLE')} · {d.get('OPPORTUNITY')} · стадия {d.get('STAGE_ID')}")
        if deals: found["Сделки (за сегодня)"] = deals
    elif err:
        log("crm.deal.list:", err)

    # 6) шаблоны бизнес-процессов (чтобы увидеть согласование оплат)
    tpl, err = call("bizproc.workflow.template.list")
    if tpl and isinstance(tpl, list):
        log(f"\nШаблоны бизнес-процессов: {len(tpl)}")
        for t in tpl[:30]:
            log(f"   {t.get('NAME')}  (DOCUMENT_TYPE={t.get('DOCUMENT_TYPE')})")
    elif err:
        log("bizproc.workflow.template.list:", err)

    # --- отчёт ---
    html = build_html(today, found)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitrix_отчёт_оплаты.html"),
              "w", encoding="utf-8") as f:
        f.write(html)
    log("\nГотово. Файлы: bitrix_log.txt, bitrix_отчёт_оплаты.html")

def build_html(today, found):
    rows = ""
    if not found:
        rows = '<p style="color:#94a3b8">За сегодня структурированных заявок на оплату не найдено. См. bitrix_log.txt — там видно, что доступно вебхуку. Скорее всего, оплаты оформлены как бизнес-процессы (их REST не читает) — тогда нужен смарт-процесс «Заявки на оплату» с полями Сумма/Город.</p>'
    else:
        for src, items in found.items():
            rows += f'<h2 style="font-size:15px;margin:18px 0 8px">{src}: {len(items)}</h2><pre style="white-space:pre-wrap;background:#0f172a;padding:12px;border-radius:8px;font-size:11.5px;color:#cbd5e1">{json.dumps(items, ensure_ascii=False, indent=2)[:6000]}</pre>'
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Оплаты Битрикс · {today:%d.%m.%Y}</title>
<style>body{{font-family:-apple-system,Segoe UI,Arial,sans-serif;background:#0b1220;color:#e5edf7;max-width:960px;margin:0 auto;padding:24px}}h1{{font-size:20px}}</style></head>
<body><h1>💳 Оплаты из Битрикс24 · {today:%d.%m.%Y}</h1>{rows}
<p style="color:#64748b;font-size:11.5px;margin-top:24px">Система «Пульс» · робот по оплатам (только чтение)</p></body></html>'''

if __name__ == "__main__":
    main()
