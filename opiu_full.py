# -*- coding: utf-8 -*-
"""opiu_full.py — тянет из iiko структуру затрат ОПиУ помесячно и пишет opiu_full.json.

Зачем: файл «Отчёт о прибылях и убытках.xlsx» обновляется вручную и отстаёт,
а дашбордам нужны свежие доли затрат (продукты, накладные, ФОТ, аренда, реализация, АУП).
Скрипт берёт те же счета, что и ОПиУ, прямо из iiko и раскладывает по группам.

Защита от ошибки: месяцы, которые есть в xlsx (эталон), пересчитываются заново
и сверяются с ним. Если расхождение больше допуска — файл помечается как непроверенный
и дашборды его игнорируют, продолжая работать на данных из xlsx.

Только чтение, iiko не меняет. Запускается в GitHub Actions.
"""
import os, re, json, time, hashlib, calendar, warnings
from datetime import date, timedelta
warnings.filterwarnings("ignore")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"',   src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"',  src).group(1)
YEAR = 2026
FZ_DEPT = "Фуд завод"
TOLERANCE = 3.0          # допустимое расхождение с эталоном, процентных пунктов

GROUPS = {
"food": [
"1.1.Себестоимость продуктовая",
"1.31.Масло фритюрное"
],
"prod": [
"1.2.Производ.расходы прочие",
"1.3.Недостача инвентаризации",
"1.4.Излишки инвентаризации",
"1.5.Расходный материал производство",
"1.7.Истек срок хранения (порча)",
"1.8.Пробы",
"1.9.Ремонт/Обслуживание производ.оборудования",
"1.11.Списание сломанных ТМЗ",
"1.12.Спецодежда",
"1.13.Коррекция отрицательных остатков на складе",
"1.14.Ремонт помещений",
"1.16.Мусор",
"1.18.Электроэнергия",
"1.19.Вредные условия труда",
"1.20.Расходный материал тех.отдела",
"1.24.Бракераж",
"1.25.Проработка блюд (текущих)",
"1.26.За счет МОЛ",
"1.27.Нарушение тех.процесса",
"1.28.Брак",
"1.30.Возвраты от дистрибьютеров"
],
"fot": [
"2.1.ЗП Производство",
"2.3.Аренда квартир д/сотрудников (пр-во)",
"2.4.Питание персонала",
"2.5.Налоги Производство"
],
"ar": [
"3.1.Аренда (пр-во)",
"3.2.Аренда КомУсл Пр-во"
],
"com": [
"2.4.Маркетинг",
"2.5.1.Расходы по реализации Прочие",
"2.5.5.Проработка новых блюд",
"2.5.8.Расходы по Доставке",
"2.5.9.Продвижение товара",
"Логистика доставка"
],
"adm": [
"3.1.1.ЗП АУП",
"3.1.2.Аренда квартир д/сотрудников (АУП)",
"3.1.4. Налоги АУП",
"3.3.1.Админ.расходы ПРОЧИЕ",
"3.3.2.Налоги НДС",
"3.3.3.Услуги охраны",
"3.3.4. IT- обслуживание",
"3.3.5.Услуги банка",
"3.3.6.Интернет,телефония,хостинг",
"3.3.7.Ремонт комп.оборудования (смартфоны,оргтехника,компы)",
"3.3.9.Расходы по ТОО",
"3.3.13.Ремонт прочего оборудования",
"3.3.15.Видеонаблюдение,пожарная сигнализация",
"3.3.15.Командировки",
"3.3.16.Регистрация нерезидентов",
"3.3.17.Вакансии размещение",
"3.3. РазныеАдмРасходы, прочие"
]
}

VARFIX = {"var": ["1.1.Себестоимость продуктовая", "1.31.Масло фритюрное", "1.5.Расходный материал производство", "1.30.Возвраты от дистрибьютеров", "1.7.Истек срок хранения (порча)", "1.28.Брак", "1.24.Бракераж", "1.3.Недостача инвентаризации", "1.4.Излишки инвентаризации", "1.13.Коррекция отрицательных остатков на складе", "1.27.Нарушение тех.процесса", "1.26.За счет МОЛ", "1.16.Мусор", "1.18.Электроэнергия", "Логистика доставка"], "fix": ["2.1.ЗП Производство", "2.3.Аренда квартир д/сотрудников (пр-во)", "2.4.Питание персонала", "2.5.Налоги Производство", "3.1.Аренда (пр-во)", "3.2.Аренда КомУсл Пр-во", "3.1.1.ЗП АУП", "3.1.2.Аренда квартир д/сотрудников (АУП)", "3.1.4. Налоги АУП", "3.3.1.Админ.расходы ПРОЧИЕ", "3.3.2.Налоги НДС", "3.3.3.Услуги охраны", "3.3.4. IT- обслуживание", "3.3.5.Услуги банка", "3.3.6.Интернет,телефония,хостинг", "3.3.7.Ремонт комп.оборудования (смартфоны,оргтехника,компы)", "3.3.9.Расходы по ТОО", "3.3.13.Ремонт прочего оборудования", "3.3.15.Видеонаблюдение,пожарная сигнализация", "3.3.15.Командировки", "3.3.16.Регистрация нерезидентов", "3.3.17.Вакансии размещение", "3.3. РазныеАдмРасходы, прочие", "2.4.Маркетинг", "2.5.1.Расходы по реализации Прочие", "2.5.5.Проработка новых блюд", "2.5.9.Продвижение товара", "1.2.Производ.расходы прочие", "1.9.Ремонт/Обслуживание производ.оборудования", "1.14.Ремонт помещений", "1.12.Спецодежда", "1.11.Списание сломанных ТМЗ", "1.20.Расходный материал тех.отдела", "1.25.Проработка блюд (текущих)", "Расходы по вознаграждениям", "Зарплата", "3.Расходы АДМ, прочие", "1.8.Пробы", "1.19.Вредные условия труда"]}

REFERENCE = {
"2026-01": {
"food": 0.5004,
"prod": 0.06879,
"fot": 0.26064,
"ar": 0.03105,
"com": 0.04601,
"adm": 0.17631
},
"2026-02": {
"food": 0.51888,
"prod": 0.06725,
"fot": 0.27792,
"ar": 0.03217,
"com": 0.04779,
"adm": 0.17916
},
"2026-03": {
"food": 0.50547,
"prod": 0.0651,
"fot": 0.25429,
"ar": 0.03114,
"com": 0.07399,
"adm": 0.16299
},
"2026-04": {
"food": 0.4968,
"prod": 0.06002,
"fot": 0.26593,
"ar": 0.03022,
"com": 0.05435,
"adm": 0.15641
},
"2026-05": {
"food": 0.49077,
"prod": 0.06899,
"fot": 0.22907,
"ar": 0.02891,
"com": 0.04993,
"adm": 0.15151
}
}

s = requests.Session()


def norm(n):
    """убираем нумерацию и регистр: «1.1.Себестоимость продуктовая» → «себестоимость продуктовая»"""
    n = re.sub(r"^[\d.\s]+", "", str(n or "")).strip().lower()
    return re.sub(r"\s+", " ", n)


NAME2GROUP = {}
for g, names in GROUPS.items():
    for n in names:
        NAME2GROUP[norm(n)] = g

NAME2VF = {}
for kind, names in VARFIX.items():
    for n in names:
        NAME2VF[norm(n)] = kind


def auth():
    r = s.get(URL + "/resto/api/auth",
              params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
              verify=False, timeout=60)
    r.raise_for_status()
    return r.text.strip().strip('"')


def olap(body, tries=4):
    last = None
    for i in range(tries):
        try:
            r = s.post(URL + "/resto/api/v2/reports/olap",
                       headers={"Cookie": "key=" + TOK, "Content-Type": "application/json"},
                       data=json.dumps(body), verify=False, timeout=300)
            if r.status_code == 200:
                return r.json().get("data", [])
            last = "HTTP %s: %s" % (r.status_code, r.text[:200])
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
        time.sleep(3 * (i + 1))
    print("[!] OLAP не ответил:", last)
    return None


def turnover(mi, last_full):
    """Один запрос на месяц: обороты по всем счетам с их типами.
    Тип счёта не фильтруем — в разных версиях iiko набор констант отличается,
    поэтому раскладываем по названиям счетов (они совпадают со строками ОПиУ)."""
    d1 = date(YEAR, mi, 1)
    d2 = min(date(YEAR, mi, calendar.monthrange(YEAR, mi)[1]), last_full)
    body = {
        "reportType": "TRANSACTIONS", "buildSummary": "true",
        "groupByRowFields": ["Account.Name", "Account.Type"],
        "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
        "filters": {
            "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                   "from": d1.isoformat(),
                                   "to": (d2 + timedelta(days=1)).isoformat(),
                                   "includeLow": True, "includeHigh": True},
            "Department": {"filterType": "IncludeValues", "values": [FZ_DEPT]},
        },
    }
    data = olap(body)
    if data is None:
        return None
    rows = {}
    for row in data:
        nm = (row.get("Account.Name") or "—").strip()
        tp = (row.get("Account.Type") or "").strip()
        inc = row.get("Sum.Incoming") or 0
        outg = row.get("Sum.Outgoing") or 0
        r = rows.setdefault(nm, {"debit": 0.0, "credit": 0.0, "type": tp})
        r["debit"] += inc - outg           # расход (дебетовый оборот)
        r["credit"] += outg - inc          # доход (кредитовый оборот)
    return rows


def main():
    global TOK
    TOK = auth()
    last_full = date.today() - timedelta(days=1)
    print("iiko ok, структура затрат по %s" % last_full.strftime("%d.%m.%Y"))

    months, unknown, types = {}, {}, {}
    today = date.today()
    for mi in range(1, 13):
        if date(YEAR, mi, 1) > last_full:
            break
        # берём только закрытые месяцы: месяц считается закрытым к 18-му числу следующего.
        # незакрытый месяц занижает ФОТ и администрацию — начисления проходят в конце месяца.
        nxt = date(YEAR + (1 if mi == 12 else 0), 1 if mi == 12 else mi + 1, 18)
        if today < nxt:
            print("  %02d: месяц ещё не закрыт (закрытие с %s) — пропускаю" % (mi, nxt.strftime("%d.%m")))
            continue
        rows = turnover(mi, last_full)
        if not rows:
            continue
        for nm, r in rows.items():
            types[r["type"]] = types.get(r["type"], 0) + 1
        rev = sum(r["credit"] for r in rows.values() if r["type"] == "INCOME")
        if rev <= 0:
            # запасной вариант: выручка по названию счёта
            rev = sum(r["credit"] for nm, r in rows.items()
                      if norm(nm).startswith(("торговая выручка", "выручка")))
        if rev <= 0:
            print("  %d: выручка не найдена, месяц пропущен" % mi)
            continue
        g = {k: 0.0 for k in GROUPS}
        vf = {"var": 0.0, "fix": 0.0}
        for nm, r in rows.items():
            val = r["debit"]
            if abs(val) < 0.5:
                continue
            key = NAME2GROUP.get(norm(nm))
            if key:
                g[key] += val
            elif r["type"] != "INCOME":
                unknown[nm] = unknown.get(nm, 0.0) + val
            kind = NAME2VF.get(norm(nm))
            if kind:
                vf[kind] += val
        key = "%d-%02d" % (YEAR, mi)
        months[key] = {"rev": round(rev),
                       "abs": {k: round(v) for k, v in g.items()},
                       "ratios": {k: round(v / rev, 5) for k, v in g.items()},
                       "full": round(sum(g.values()) / rev, 5),
                       "var": round(vf["var"]), "fix": round(vf["fix"]),
                       "days": min(date(YEAR, mi, calendar.monthrange(YEAR, mi)[1]), last_full).isoformat()}
        # проверка правдоподобия: незакрытые начисления видно по провалу ФОТ и АУП
        r = months[key]["ratios"]
        why = []
        if r["food"] < 0.35 or r["food"] > 0.65: why.append("продуктовая %.0f%%" % (r["food"] * 100))
        if r["fot"] < 0.15: why.append("ФОТ всего %.1f%% — зарплата ещё не начислена" % (r["fot"] * 100))
        if r["adm"] < 0.08: why.append("АУП всего %.1f%%" % (r["adm"] * 100))
        if months[key]["full"] < 0.90 or months[key]["full"] > 1.35: why.append("итог %.0f%%" % (months[key]["full"] * 100))
        ref_avg = {k: sum(REFERENCE[m][k] for m in REFERENCE) / len(REFERENCE) for k in GROUPS}
        for k in ("adm", "fot", "food"):
            if abs(r[k] - ref_avg[k]) > 0.06:
                why.append("%s %.1f%% против обычных %.1f%%" % (k, r[k] * 100, ref_avg[k] * 100))
        gaps = []
        ref_avg2 = {k: sum(REFERENCE[m][k] for m in REFERENCE) / len(REFERENCE) for k in GROUPS}
        for k in ("fot", "adm"):
            if r[k] < ref_avg2[k] * 0.55:
                gaps.append(k)
        months[key]["ok"] = not why
        months[key]["why"] = "; ".join(why)
        months[key]["gaps"] = gaps          # группы, где начисления ещё не проведены
        months[key]["ref"] = {k: round(v, 5) for k, v in ref_avg2.items()}
        print("  %s: выручка %s, полная себестоимость %.1f%% %s"
              % (key, f"{round(rev):,}".replace(",", " "), months[key]["full"] * 100,
                 "✓" if not why else "— НЕ БЕРЁМ: " + months[key]["why"]))
    print("типы счетов в выгрузке:", ", ".join("%s×%d" % (t or "—", n) for t, n in sorted(types.items())))

    # ── сверка с эталоном из xlsx ────────────────────────────────
    worst, checked = 0.0, []
    for m, ref in REFERENCE.items():
        if m not in months or not months[m].get("ok", True):
            continue
        got = months[m]["ratios"]
        dev = max(abs(got.get(k, 0) - ref[k]) * 100 for k in ref)
        checked.append({"m": m, "dev": round(dev, 2)})
        worst = max(worst, dev)
    ok = bool(checked) and worst <= TOLERANCE
    print("сверка с xlsx: месяцев %d, худшее расхождение %.2f п.п. → %s"
          % (len(checked), worst, "принято" if ok else "ОТКЛОНЕНО"))
    if unknown:
        top = sorted(unknown.items(), key=lambda x: -abs(x[1]))[:10]
        print("счета вне групп:", ", ".join("%s (%.0f)" % (n, v) for n, v in top))

    out = {"months": months, "check": {"ok": ok, "worst_dev": round(worst, 2), "months": checked,
                                       "tolerance": TOLERANCE},
           "unknown": {n: round(v) for n, v in sorted(unknown.items(), key=lambda x: -abs(x[1]))[:20]},
           "types": types,
           "_pulled": date.today().strftime("%d.%m.%Y"), "_through": last_full.isoformat()}
    with open(os.path.join(HERE, "opiu_full.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print("записан opiu_full.json (%d мес.)" % len(months))


if __name__ == "__main__":
    main()
