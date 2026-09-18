# -*- coding: utf-8 -*-
"""
Пульс · Налоги — дашборд расчётов с бюджетом из 1С (ТОО Фудзавод).

Тянет данные напрямую из 1С «Uchet.Бухгалтерия» по протоколу OData (HTTP Basic auth)
и пересобирает nalogi_отчёт.html из nalogi_template.html.

Источник — регистр бухгалтерии «Типовой», счета расчётов с бюджетом 3100/3200.
По каждому виду налога считаются помесячно: начислено (кредитовый оборот),
уплачено (дебетовый оборот) и входящее сальдо на начало года — этого достаточно,
чтобы на странице показать любой период (год / квартал / месяц) и сальдо.

Аггрегация делается на стороне 1С через виртуальные таблицы Turnovers/Balance —
поэтому даже по «тяжёлым» счетам (НДС, сотни тысяч проводок) один запрос ~0.5 сек.

Запуск — на серверах GitHub Actions (компьютер Ольги не нужен).
Логин/пароль 1С — из секретов ODATA_USER / ODATA_PASS.
"""
import os, sys, json, time, base64, datetime, urllib.request, urllib.parse

BASE = "https://buh.uchet.kz/R5verbrarsal8204/odata/standard.odata/"
ORG_BIN = "210340021859"          # ТОО Фудзавод
REG = "AccountingRegister_Типовой"

USER = (os.environ.get("ODATA_USER") or "").strip()
PASS = (os.environ.get("ODATA_PASS") or "").strip()
if not USER or not PASS:
    print("НЕТ секретов ODATA_USER / ODATA_PASS — нечем авторизоваться в 1С")
    sys.exit(1)
AUTH = "Basic " + base64.b64encode(("%s:%s" % (USER, PASS)).encode("utf-8")).decode("ascii")

# Виды налогов и платежей: счёт -> (короткое имя, полное, группа)
META = [
    ("3110", "КПН", "Корпоративный подоходный налог", "Налоги"),
    ("3131", "НДС", "Налог на добавленную стоимость", "Налоги"),
    ("3120", "ИПН", "Индивидуальный подоходный налог", "Налоги"),
    ("3150", "Соцналог", "Социальный налог", "Налоги"),
    ("3140", "Акцизы", "Акцизы", "Налоги"),
    ("3160", "Земельный", "Земельный налог", "Налоги"),
    ("3170", "Транспорт", "Налог на транспортные средства", "Налоги"),
    ("3180", "Имущество", "Налог на имущество", "Налоги"),
    ("3190", "Прочие налоги", "Прочие налоги", "Налоги"),
    ("3220", "ОПВ", "Обязательные пенсионные взносы", "Соцплатежи"),
    ("3250", "ОПВР", "Обязательные пенсионные взносы работодателя", "Соцплатежи"),
    ("3211", "СО", "Социальные отчисления", "Соцплатежи"),
    ("3213", "ОСМС", "Отчисления на ОСМС", "Соцплатежи"),
    ("3212", "ВОСМС", "Взносы на ОСМС", "Соцплатежи"),
    ("3231", "Единый платёж", "Единый платёж", "Соцплатежи"),
]

def get(path, params):
    """GET к OData. path — сегмент пути (может содержать кириллицу),
    params — список (ключ, значение) для query. Всё корректно кодируется."""
    p = urllib.parse.quote(path, safe="/()',:=.-")
    # $-имена опций (＄format/＄filter/…) оставляем как есть — 1С не любит %24;
    # значения кодируем полностью.
    qs = "&".join("%s=%s" % (urllib.parse.quote(k, safe="$"), urllib.parse.quote(str(v), safe=""))
                  for k, v in params)
    url = BASE + p + ("?" + qs if qs else "")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={
                "Authorization": AUTH, "Accept": "application/json",
                "User-Agent": "pulse-nalogi/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try: body = e.read().decode("utf-8", "replace")[:160]
            except Exception: pass
            last = "HTTP %s %s" % (e.code, body)
            if e.code in (400, 401, 403, 404):
                break
            time.sleep(2 + attempt * 2)
        except Exception as e:
            last = str(e); time.sleep(2 + attempt * 2)
    raise RuntimeError("OData %s: %s" % (path, last))

def val(d):
    return (d or {}).get("value") or []

def resolve_org():
    d = get("Catalog_Организации", [
        ("$format", "json"), ("$select", "Ref_Key,ИдентификационныйНомер,Description"),
        ("$filter", "ИдентификационныйНомер eq '%s'" % ORG_BIN)])
    rows = val(d)
    if not rows:
        raise RuntimeError("Организация с БИН %s не найдена" % ORG_BIN)
    return rows[0]["Ref_Key"], rows[0].get("Description", "ТОО Фудзавод")

def resolve_accounts():
    d = get("ChartOfAccounts_Типовой", [("$format", "json"), ("$select", "Ref_Key,Code")])
    by_code = {}
    for a in val(d):
        by_code[str(a.get("Code"))] = a["Ref_Key"]
    return by_code

def dt(y, m, day=1):
    return "%04d-%02d-%02dT00:00:00" % (y, m, day)

def turnovers(org_key, acc_key, start, end):
    path = "%s/Turnovers(StartPeriod=datetime'%s',EndPeriod=datetime'%s')" % (REG, start, end)
    d = get(path, [("$format", "json"), ("$select", "СуммаTurnoverDr,СуммаTurnoverCr"),
                   ("$filter", "Account_Key eq guid'%s' and Организация_Key eq guid'%s'" % (acc_key, org_key))])
    dr = cr = 0.0
    for x in val(d):
        dr += float(x.get("СуммаTurnoverDr") or 0); cr += float(x.get("СуммаTurnoverCr") or 0)
    return dr, cr

def balance(org_key, acc_key, period):
    path = "%s/Balance(Period=datetime'%s')" % (REG, period)
    d = get(path, [("$format", "json"), ("$select", "СуммаBalanceDr,СуммаBalanceCr"),
                   ("$filter", "Account_Key eq guid'%s' and Организация_Key eq guid'%s'" % (acc_key, org_key))])
    dr = cr = 0.0
    for x in val(d):
        dr += float(x.get("СуммаBalanceDr") or 0); cr += float(x.get("СуммаBalanceCr") or 0)
    return cr - dr   # >0 — кредитовое (долг), <0 — дебетовое (переплата)

def main():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5)  # Алматы UTC+5
    year = now.year
    cur_m = now.month
    end_bound = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")  # включая сегодня

    org_key, org_name = resolve_org()
    accs = resolve_accounts()
    print("Организация: %s · %s" % (org_name, org_key))

    taxes = []
    for code, name, full, grp in META:
        key = accs.get(code)
        if not key:
            print("  счёт %s не найден в плане счетов — пропуск" % code); continue
        opening = balance(org_key, key, dt(year, 1, 1))
        months = []
        for m in range(1, cur_m + 1):
            start = dt(year, m, 1)
            end = dt(year, m + 1, 1) if m < 12 else dt(year + 1, 1, 1)
            if m == cur_m:
                end = end_bound
            dr, cr = turnovers(org_key, key, start, end)
            months.append({"m": m, "nach": round(cr), "upl": round(dr)})
        nach = sum(x["nach"] for x in months)
        upl = sum(x["upl"] for x in months)
        close = round(opening) + nach - upl
        active = bool(nach or upl or round(opening) or close)
        print("  %-4s %-14s начислено %13s уплачено %13s сальдо %13s" % (
            code, name, "{:,}".format(nach), "{:,}".format(upl), "{:,}".format(close)))
        if active:
            taxes.append({"code": code, "name": name, "full": full, "grp": grp,
                          "open": round(opening), "months": months,
                          "nach": nach, "upl": upl, "close": close, "active": True})

    if not taxes:
        print("Пусто — деплой пропускаем"); sys.exit(1)

    asof = now.strftime("%d.%m.%Y")
    D = {"org": org_name if "Фуд" in org_name else "ТОО Фудзавод",
         "bin": ORG_BIN, "year": year, "asof": asof, "taxes": taxes}

    tpl = open("nalogi_template.html", encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(D, ensure_ascii=False)).replace("__ASOF__", asof)
    with open("nalogi_отчёт.html", "w", encoding="utf-8") as f:
        f.write(html)
    debt = sum(t["close"] for t in taxes if t["close"] > 0)
    print("Отчёт собран на %s · видов: %d · долг перед бюджетом: %s ₸ (%d байт)" % (
        asof, len(taxes), "{:,}".format(debt).replace(",", " "), len(html.encode("utf-8"))))

if __name__ == "__main__":
    main()
