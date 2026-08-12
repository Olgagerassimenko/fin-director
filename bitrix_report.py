# -*- coding: utf-8 -*-
"""
bitrix_report.py — робот «Битрикс · Оплаты» для системы Пульс (только чтение).

СОСТОЯНИЕ (12.08.2026): отчёт «Согласованные оплаты — ФудЗавод» (bitrix_отчёт_оплаты.html)
ведётся из выгрузки бизнес-процессов «Живой ленты» (Автоматизация → Мои процессы).
Вебхук их напрямую не отдаёт (bizproc = insufficient_scope; в списках только тестовые).
Поэтому этот робот СЕЙЧАС ничего не публикует — только пишет диагностику в bitrix_log.txt
и НИКОГДА не трогает bitrix_отчёт_оплаты.html (чтобы не затереть отчёт с 564 заявками).

Когда админ создаст CRM-смарт-процесс «Заявки на оплату» и туда попадут заявки —
включим чтение через crm.item.list и авто-сборку отчёта (см. функцию probe_smart()).
"""
import os, json, re, datetime, urllib.request, urllib.error

WH = (os.environ.get("BITRIX_WEBHOOK") or "").strip().rstrip("/")
if "/rest/" in WH:
    _base, _rest = WH.split("/rest/", 1)
    _parts = [x for x in _rest.split("/") if x]
    if len(_parts) >= 2:
        WH = _base + "/rest/" + _parts[0] + "/" + _parts[1]
HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "bitrix_отчёт_оплаты.html")
LOG = open(os.path.join(HERE, "bitrix_log.txt"), "w", encoding="utf-8")

def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

def call(method, params=None):
    if not WH:
        return None, "нет BITRIX_WEBHOOK"
    url = WH + "/" + method + ".json"
    body = json.dumps(params or {}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode("utf-8")); return None, j.get("error_description") or f"HTTP {e.code}"
        except Exception:
            return None, f"HTTP {e.code}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def probe_smart():
    """Ищет CRM-смарт-процесс с оплатами. Возвращает (entityTypeId, title) или None."""
    j, err = call("crm.type.list")
    if not j or "result" not in j:
        log("crm.type.list:", err); return None
    types = (j["result"] or {}).get("types", [])
    for t in types:
        title = t.get("title") or ""
        log(f"  смарт-процесс: entityTypeId={t.get('entityTypeId')} «{title}»")
        if re.search(r"оплат|заявк|платеж|счёт|счет", title, re.I):
            return t.get("entityTypeId"), title
    return None

def main():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5)  # Алматы UTC+5
    log(f"Битрикс · оплаты · {now:%d.%m.%Y %H:%M} (Алматы)")

    if not WH:
        log("[i] BITRIX_WEBHOOK не задан — робот в режиме ожидания. Отчёт не трогаю.")
        return

    j, err = call("profile")
    prof = j.get("result") if j else None
    if prof:
        log("profile: ok ·", prof.get("NAME"), prof.get("LAST_NAME"), "· admin=", prof.get("ADMIN"))
    else:
        log("profile: ошибка —", err)
    j, err = call("scope")
    scope = (j.get("result") if j else None) or []
    log("scope:", scope or err)

    # разведка: появился ли смарт-процесс с оплатами?
    sp = probe_smart()
    if sp:
        etid, title = sp
        jj, e2 = call("crm.item.list", {"entityTypeId": etid, "start": 0})
        items = (jj.get("result", {}) or {}).get("items", []) if jj else []
        log(f"[i] Найден смарт-процесс «{title}» (id={etid}), заявок: {len(items)}.")
        log("[i] Смарт-процесс есть — можно включать авто-сборку отчёта из него "
            "(обновить bitrix_report.py на версию-читалку).")
    else:
        log("[i] CRM-смарт-процесса с оплатами пока нет.")

    # ГЛАВНОЕ: не трогаем опубликованный отчёт (564 заявки — из выгрузки).
    log("[ok] Отчёт «Согласованные оплаты» ведётся вручную/через выгрузку — "
        "робот его НЕ перезаписывает (bitrix_отчёт_оплаты.html оставлен как есть).")

if __name__ == "__main__":
    main()
