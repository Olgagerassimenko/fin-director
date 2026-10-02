# -*- coding: utf-8 -*-
"""
Пульс · Реализация — сколько дохода внесено в 1С, помесячно.

Зачем. Отгрузка идёт в iiko день в день, а в бухгалтерскую базу реализация
попадает позже и не всегда целиком. Пока месяц не внесён полностью, любой
отчёт из 1С — налоги, баланс, ОПиУ для банка — показывает заниженный доход.
Эта страница отвечает на один вопрос: на какую сумму реализация уже внесена
и сколько ещё не внесено по сравнению с айко.

Источник. 1С «Uchet.Бухгалтерия» по OData, регистр бухгалтерии «Типовой»,
счета доходов 6010/6020/6030:
    внесено = кредитовый оборот 6010 − дебетовый 6020 (возвраты) − 6030 (скидки).
Эталон — помесячная выручка из айко, файл opiu_iiko.js (его собирает
gen_opiu_iiko.py тем же ночным прогоном).

Логин/пароль 1С — из секретов ODATA_USER / ODATA_PASS. Только чтение.
"""
import os, sys, json, re, time, base64, datetime, urllib.request, urllib.parse

BASE = "https://buh.uchet.kz/R5verbrarsal8204/odata/standard.odata/"
ORG_BIN = "210340021859"          # ТОО Фудзавод
REG = "AccountingRegister_Типовой"
HERE = os.path.dirname(os.path.abspath(__file__))

USER = (os.environ.get("ODATA_USER") or "").strip()
PASS = (os.environ.get("ODATA_PASS") or "").strip()
if not USER or not PASS:
    print("НЕТ секретов ODATA_USER / ODATA_PASS"); sys.exit(1)
AUTH = "Basic " + base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode("ascii")

# счета доходов: код -> (как показываем, знак в «внесено»)
REVENUE = {"6010": ("Доход от реализации", +1),
           "6020": ("Возвраты проданной продукции", -1),
           "6030": ("Скидки с цены и продаж", -1)}

def get(path, params):
    p = urllib.parse.quote(path, safe="/()',:=.-")
    qs = "&".join("%s=%s" % (urllib.parse.quote(k, safe="$"), urllib.parse.quote(str(v), safe=""))
                  for k, v in params)
    url = BASE + p + ("?" + qs if qs else "")
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={
                "Authorization": AUTH, "Accept": "application/json",
                "User-Agent": "pulse-realizaciya/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try: body = e.read().decode("utf-8", "replace")[:160]
            except Exception: pass
            last = "HTTP %s %s" % (e.code, body)
            if e.code in (400, 401, 403, 404): break
            time.sleep(2 + attempt * 2)
        except Exception as e:
            last = str(e); time.sleep(2 + attempt * 2)
    raise RuntimeError("OData %s: %s" % (path, last))

val = lambda d: (d or {}).get("value") or []
dt = lambda y, m, d=1: "%04d-%02d-%02dT00:00:00" % (y, m, d)

def all_orgs():
    """Все организации базы. Выручка группы разнесена по нескольким юрлицам
    (ТОО и ИП), и по одному ТОО сумма всегда будет меньше айко — поэтому
    считаем по каждой и показываем разрез."""
    rows = val(get("Catalog_Организации", [
        ("$format", "json"),
        ("$select", "Ref_Key,ИдентификационныйНомер,Description,DeletionMark")]))
    out = []
    for r in rows:
        if r.get("DeletionMark"): continue
        out.append({"key": r["Ref_Key"], "bin": r.get("ИдентификационныйНомер") or "",
                    "name": (r.get("Description") or "").strip() or "без названия"})
    return out

def accounts():
    out = {}
    for a in val(get("ChartOfAccounts_Типовой", [("$format", "json"), ("$select", "Ref_Key,Code,Description")])):
        out[str(a.get("Code"))] = (a["Ref_Key"], a.get("Description") or "")
    return out

def turnovers_by_org(acc, start, end):
    """Один запрос на счёт и месяц, с разрезом по организациям."""
    path = "%s/Turnovers(StartPeriod=datetime'%s',EndPeriod=datetime'%s')" % (REG, start, end)
    d = get(path, [("$format", "json"),
                   ("$select", "Организация_Key,СуммаTurnoverDr,СуммаTurnoverCr"),
                   ("$filter", "Account_Key eq guid'%s'" % acc)])
    out = {}
    for x in val(d):
        k = x.get("Организация_Key") or "-"
        a, b = out.get(k, (0.0, 0.0))
        out[k] = (a + float(x.get("СуммаTurnoverDr") or 0),
                  b + float(x.get("СуммаTurnoverCr") or 0))
    return out

def iiko_months():
    """Помесячная выручка из айко — эталон, с чем сверяем 1С."""
    p = os.path.join(HERE, "opiu_iiko.js")
    if not os.path.exists(p):
        print("opiu_iiko.js рядом не лежит — сверять не с чем"); return {}
    t = open(p, encoding="utf-8").read()
    m = re.search(r"=\s*(\{.*\})\s*;?\s*$", t, re.S)
    if not m: return {}
    d = json.loads(m.group(1))
    out = {}
    for k, v in (d.get("months") or {}).items():
        r = (v.get("v") or {}).get("Торговая выручка")
        if r is None: r = v.get("rev")
        if r is not None: out[k] = round(r)
    return out

def main():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5)   # Алматы
    year, cur_m = now.year, now.month
    end_bound = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")

    orgs = all_orgs()
    onames = {o["key"]: o["name"] for o in orgs}
    accs = accounts()
    print("Организаций в базе: %d" % len(orgs))
    for o in orgs: print("   %-40s БИН %s" % (o["name"][:40], o["bin"]))

    # что вообще есть на 60-х счетах — чтобы не гадать о плане счетов
    print("Счета доходов в плане счетов:")
    for code in sorted(c for c in accs if c.startswith("60")):
        print("   %-6s %s" % (code, accs[code][1][:60]))

    rows = {}
    byorg = {}                       # org_key -> [по месяцам]
    for code, (label, sign) in REVENUE.items():
        if code not in accs:
            print("  счёт %s не найден — пропуск" % code); continue
        key = accs[code][0]
        per = []
        for m in range(1, cur_m + 1):
            start = dt(year, m, 1)
            end = end_bound if m == cur_m else (dt(year, m + 1, 1) if m < 12 else dt(year + 1, 1, 1))
            t = turnovers_by_org(key, start, end)
            dr = sum(v[0] for v in t.values()); cr = sum(v[1] for v in t.values())
            per.append({"m": m, "dr": round(dr), "cr": round(cr)})
            for ok, (d_, c_) in t.items():
                arr = byorg.setdefault(ok, [0] * cur_m)
                arr[m - 1] += round(c_ if sign > 0 else -d_)
        rows[code] = {"code": code, "name": accs[code][1] or label, "sign": sign, "months": per}
        print("  %-6s %-40s Кт %15s  Дт %15s" % (
            code, (accs[code][1] or label)[:40],
            "{:,}".format(sum(x["cr"] for x in per)).replace(",", " "),
            "{:,}".format(sum(x["dr"] for x in per)).replace(",", " ")))

    iiko = iiko_months()
    months = []
    for m in range(1, cur_m + 1):
        v1c = 0
        for code, r in rows.items():
            x = r["months"][m - 1]
            v1c += (x["cr"] if r["sign"] > 0 else -x["dr"])
        key = "%04d-%02d" % (year, m)
        ii = iiko.get(key)
        months.append({"m": m, "v1c": round(v1c), "iiko": ii,
                       "diff": (round(v1c) - ii) if ii is not None else None,
                       "pct": (round(v1c) / ii) if ii else None})

    orgrows = []
    for k, arr in byorg.items():
        tot = sum(arr)
        if not tot: continue
        orgrows.append({"name": onames.get(k, "неизвестная организация"), "months": arr, "total": tot})
    orgrows.sort(key=lambda x: -x["total"])
    print("\nПо организациям за год:")
    for o in orgrows:
        print("   %-44s %18s" % (o["name"][:44], "{:,}".format(o["total"]).replace(",", " ")))

    D = {"org": "группа Фуд Завод", "bin": ORG_BIN, "year": year,
         "asof": now.strftime("%d.%m.%Y %H:%M"), "curMonth": cur_m,
         "months": months, "accounts": list(rows.values()), "orgs": orgrows}
    with open(os.path.join(HERE, "realizaciya.js"), "w", encoding="utf-8") as f:
        f.write("window.REALIZACIYA = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";\n")

    tpl = open(os.path.join(HERE, "realizaciya_template.html"), encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(D, ensure_ascii=False)).replace("__ASOF__", D["asof"])
    with open(os.path.join(HERE, "реализация.html"), "w", encoding="utf-8") as f:
        f.write(html)

    f2 = lambda x: "{:,}".format(int(x)).replace(",", " ") if x is not None else "—"
    print("\nПо месяцам: 1С / айко / разница")
    for x in months:
        print("  %02d  %15s %15s %15s %s" % (x["m"], f2(x["v1c"]), f2(x["iiko"]), f2(x["diff"]),
              ("%.0f%%" % (x["pct"] * 100)) if x["pct"] else ""))
    print("\nrealizaciya.js и реализация.html собраны (%d байт)" % len(html.encode("utf-8")))

if __name__ == "__main__":
    main()
