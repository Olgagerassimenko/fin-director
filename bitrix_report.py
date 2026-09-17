# -*- coding: utf-8 -*-
"""
Пульс · Битрикс — отчёт по согласованным оплатам.
Тянет три смарт-процесса «Платежи» (Фуд завод, Астана/ФЗА, O-Live) через REST-вебхук
и пересобирает bitrix_отчёт_оплаты.html из шаблона oplaty_template.html.

Запускается на серверах GitHub Actions (ноутбук не нужен). Вебхук берётся из секрета
BITRIX_WEBHOOK. Ничего секретного в страницу не попадает — только собранные строки.
"""
import os, sys, json, time, datetime, urllib.request, urllib.parse

WEBHOOK = (os.environ.get("BITRIX_WEBHOOK") or "").strip().rstrip("/")
if not WEBHOOK:
    print("НЕТ секрета BITRIX_WEBHOOK — нечем ходить в Битрикс")
    sys.exit(1)

# entityTypeId -> конфигурация процесса
PROC = {
    1228: dict(div="ФЗ",     cat=89,  amt="ufCrm79_1785820299", typ="ufCrm79_1773041127", desc="ufCrm79_1773041072",
               types={"433": "Аванс", "435": "Счет на оплату", "437": "Оплата наличными", "439": "Оплата поставщикам"}),
    1270: dict(div="ФЗА",    cat=107, amt="ufCrm97_1785820335", typ="ufCrm97_1775475027", desc="ufCrm97_1775474996",
               types={"503": "Оплата наличными", "505": "Счет на оплату", "507": "Аванс", "509": "Оплата поставщикам"}),
    1246: dict(div="O-Live", cat=97,  amt="ufCrm87_1778480556", typ="ufCrm87_1773815922", desc="ufCrm87_1773815905",
               types={"467": "Оплата наличными", "469": "Счет на оплату", "471": "Аванс"}),
}

def api(method, params=None):
    """GET на REST-вебхук. Возвращает распарсенный JSON."""
    url = WEBHOOK + "/" + method + ".json"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pulse-oplaty/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            time.sleep(2 + attempt * 2)
    raise RuntimeError("Bitrix API %s: %s" % (method, last))

def stage_names(entity_id, cat):
    d = api("crm.status.list", {"filter[ENTITY_ID]": "DYNAMIC_%d_STAGE_%d" % (entity_id, cat)})
    out = {}
    for s in (d.get("result") or []):
        out[s["STATUS_ID"]] = s["NAME"]
    return out

def fetch_process(entity_id, cfg):
    sn = stage_names(entity_id, cfg["cat"])
    sel = ["id", "createdTime", "stageId", cfg["amt"], cfg["typ"], cfg["desc"]]
    rows, start = [], 0
    for _ in range(80):  # до 4000 записей
        d = api("crm.item.list", {
            "entityTypeId": entity_id,
            "order[id]": "asc",
            "start": start,
            "select[]": sel,
        })
        items = ((d.get("result") or {}).get("items")) or []
        if not items:
            break
        for x in items:
            amt_raw = str(x.get(cfg["amt"]) or "")
            try:
                amt = round(float(amt_raw.split("|")[0]))
            except Exception:
                amt = 0
            st = sn.get(x.get("stageId"), x.get("stageId") or "")
            ds = str(x.get(cfg["desc"]) or "")
            ds = " ".join(ds.split())[:90]
            rows.append({
                "d": (x.get("createdTime") or "")[:10],
                "dv": cfg["div"],
                "t": cfg["types"].get(str(x.get(cfg["typ"])), "—"),
                "a": amt,
                "st": st,
                "ds": ds,
            })
        if len(items) < 50:
            break
        start += 50
    return rows

def main():
    all_rows = []
    for eid, cfg in PROC.items():
        try:
            r = fetch_process(eid, cfg)
            print("%-7s %5d заявок" % (cfg["div"], len(r)))
            all_rows += r
        except Exception as e:
            print("ОШИБКА по %s (%d): %s" % (cfg["div"], eid, e))
            sys.exit(1)  # не деплоим частичные данные

    if not all_rows:
        print("Пусто — ничего не пришло, деплой пропускаем")
        sys.exit(1)

    # контроль: сумма одобренных
    appr = sum(x["a"] for x in all_rows if ("Одобрено" in x["st"] or "Успех" in x["st"]))
    print("Всего заявок: %d · одобрено: %s ₸" % (len(all_rows), "{:,}".format(appr).replace(",", " ")))

    asof = (datetime.datetime.utcnow() + datetime.timedelta(hours=5)).strftime("%d.%m.%Y")
    tpl = open("oplaty_template.html", encoding="utf-8").read()
    html = tpl.replace("__ROWS__", json.dumps(all_rows, ensure_ascii=False)).replace("__ASOF__", asof)
    with open("bitrix_отчёт_оплаты.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Отчёт собран на %s (%d байт)" % (asof, len(html.encode("utf-8"))))

if __name__ == "__main__":
    main()
