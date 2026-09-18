# -*- coding: utf-8 -*-
"""
Пульс · Битрикс — отчёт по согласованным оплатам.
Тянет три смарт-процесса «Платежи» (Фуд завод 1228, Астана/ФЗА 1270, O-Live 1246)
через REST-вебхук и пересобирает bitrix_отчёт_оплаты.html из oplaty_template.html.

Запуск — на серверах GitHub Actions (ноутбук не нужен). Вебхук из секрета BITRIX_WEBHOOK.
Названия стадий зашиты в код (без сетевого crm.status.list — он лишний и ненадёжный).
"""
import os, sys, json, time, datetime, urllib.request, urllib.parse

WEBHOOK = (os.environ.get("BITRIX_WEBHOOK") or "").strip().rstrip("/")
if not WEBHOOK:
    print("НЕТ секрета BITRIX_WEBHOOK — нечем ходить в Битрикс")
    sys.exit(1)

# Названия стадий по каждому процессу: суффикс stageId -> человекочитаемое имя
STAGES = {
    1228: {"NEW": "Черновик", "PREPARATION": "Согласование: Руководитель",
           "CLIENT": "Согласование: Фин. Директор", "UC_J2H4CP": "Ознакомление: Финансовый отдел",
           "UC_C8ORYB": "Касса", "UC_1MFIW8": "Одобрено", "UC_NSP3VJ": "Отклонено",
           "SUCCESS": "Успех", "FAIL": "Провал"},
    1246: {"NEW": "Черновик", "PREPARATION": "Согласование: Операционный директор",
           "CLIENT": "Согласование: Управляющий директор", "UC_P4HN2Y": "Бухгалтерия",
           "UC_O4RX3V": "Одобрено", "UC_WSZ0RF": "Отклонено", "SUCCESS": "Успех", "FAIL": "Провал"},
    1270: {"NEW": "Черновик", "PREPARATION": "Согласование: Руководитель",
           "CLIENT": "Согласование: Директор", "UC_ZBNZ39": "Ознакомление: Финансовый отдел",
           "UC_3VU6BV": "Касса", "UC_LW6NMZ": "Одобрено", "UC_BN21CK": "Отклонено",
           "SUCCESS": "Успех", "FAIL": "Провал"},
}

# Карта авторов заявок (assignedById -> ФИО). Снята разово из Битрикса.
# Новых сотрудников тут может не быть — они покажутся как «—», карту можно обновить.
AUTHORS = {
    "77": "Есжанова Гюзяль", "85": "Маньшева Олеся", "8061": "Джасымбекова Перизат",
    "8067": "Тобулова Динара", "8069": "Нуспекова Индира", "8079": "Шегай Юрий",
    "8083": "Заиров Расулжан", "8085": "Мукашева Мейрамгуль", "8087": "Амиржанова Акерке",
    "8089": "Ермагамбет Каламкас", "8091": "Малышев Александр", "8095": "Вон Сергей",
    "8099": "Баратова Мадина", "8105": "Сон Сергей", "8107": "Дубницкий Роман",
    "8111": "Азимова Санам", "8115": "Шишерина Мария", "8121": "Дюсембин Руслан",
    "8135": "Болотбеков Даулет", "8139": "Амувакиров Адиль", "8147": "Толтай Айдана",
    "8163": "Пак Андрей", "8267": "Сейтхан Диана", "8273": "Маханов Марат",
    "8363": "Турыш Одильжон", "8443": "Фатыкова Аяжан", "8463": "Тен Николай",
    "8621": "Худобаева Зарифа", "8667": "Ойшынов Жансултан", "8717": "Нуримбетова Жазира",
    "8851": "Казазаев Алексей", "9287": "Чжен Игорь", "9611": "Рустам",
    "9781": "Герасименко Ольга", "9851": "Абитов Руслан", "10171": "Коковкин Владимир",
    "10215": "Советханов Елдос", "10567": "Сыздыков Бауыржан", "10583": "Укертаев Санжар",
    "10675": "Скакова Жанна", "10973": "Айнабекова Куралай", "11593": "Алина",
    "12223": "Эринбетова Жибек", "12697": "Кабиев Ельдар", "13383": "Абдижаббарова Жанар",
    "14581": "Абызбаева Айнур", "15947": "Баскамбаева Аида", "15989": "Балаганова Динара",
    "16459": "Горбачев Александр", "16851": "Зырянов Николай", "16855": "Ти Ирина",
    "17131": "Яковлев Александр", "17691": "Абирова Сауле", "17709": "Нуржан",
    "18353": "Калиева Бакыт",
}

PROC = {
    1228: dict(div="ФЗ",     amt="ufCrm79_1785820299", typ="ufCrm79_1773041127", desc="ufCrm79_1773041072",
               files=["ufCrm79_1773041083", "ufCrm79_1773290279"],
               types={"433": "Аванс", "435": "Счет на оплату", "437": "Оплата наличными", "439": "Оплата поставщикам"}),
    1270: dict(div="ФЗА",    amt="ufCrm97_1785820335", typ="ufCrm97_1775475027", desc="ufCrm97_1775474996",
               files=["ufCrm97_1775475017"],
               types={"503": "Оплата наличными", "505": "Счет на оплату", "507": "Аванс", "509": "Оплата поставщикам"}),
    1246: dict(div="O-Live", amt="ufCrm87_1778480556", typ="ufCrm87_1773815922", desc="ufCrm87_1773815905",
               files=["ufCrm87_1773815914"],
               types={"467": "Оплата наличными", "469": "Счет на оплату", "471": "Аванс"}),
}

def api(method, query=""):
    """GET на вебхук. query — уже готовая строка с СЫРЫМИ скобками (как в браузере)."""
    url = WEBHOOK + "/" + method + ".json"
    if query:
        url += "?" + query
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pulse-oplaty/1.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            last = "HTTP %s %s" % (e.code, body)
            if e.code in (400, 401, 403, 404):  # смысла ретраить нет
                break
            time.sleep(2 + attempt * 2)
        except Exception as e:
            last = str(e)
            time.sleep(2 + attempt * 2)
    raise RuntimeError("Bitrix %s: %s" % (method, last))

def q(pairs):
    """Строит query со СЫРЫМИ скобками в ключах, кодируя только значения."""
    out = []
    for k, v in pairs:
        out.append("%s=%s" % (k, urllib.parse.quote(str(v), safe="")))
    return "&".join(out)

def fetch_process(entity_id, cfg):
    smap = STAGES[entity_id]
    files = cfg.get("files", [])
    fields = ["id", "createdTime", "movedTime", "stageId", "assignedById", cfg["amt"], cfg["typ"], cfg["desc"]] + files
    base = [("entityTypeId", entity_id), ("order[id]", "asc")]
    sel = [("select[]", x) for x in fields]
    rows, start = [], 0
    for _ in range(80):
        query = q(base + [("start", start)] + sel)
        d = api("crm.item.list", query)
        items = ((d.get("result") or {}).get("items")) or []
        if not items:
            break
        for x in items:
            amt_raw = str(x.get(cfg["amt"]) or "")
            try:
                amt = round(float(amt_raw.split("|")[0]))
            except Exception:
                amt = 0
            suffix = str(x.get("stageId") or "").split(":")[-1]
            st = smap.get(suffix, x.get("stageId") or "")
            ds = " ".join(str(x.get(cfg["desc"]) or "").split())[:90]
            # есть ли вложение (сам файл/ссылку с токеном НЕ выгружаем — только факт)
            has_file = 0
            for ff in files:
                v = x.get(ff)
                if v and (len(v) if isinstance(v, list) else 1):
                    has_file = 1
                    break
            rows.append({
                "d": (x.get("createdTime") or "")[:10],
                "dv": cfg["div"],
                "t": cfg["types"].get(str(x.get(cfg["typ"])), "—"),
                "a": amt, "st": st, "ds": ds,
                "id": x.get("id"), "f": has_file,
                "mv": (x.get("movedTime") or "")[:10],
                "au": AUTHORS.get(str(x.get("assignedById")), ""),
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
            sys.exit(1)

    if not all_rows:
        print("Пусто — деплой пропускаем")
        sys.exit(1)

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
