# -*- coding: utf-8 -*-
"""gen_opiu_detail.py — расшифровка каждой строки ОПиУ изнутри, из iiko.

Зачем это нужно. Аудит ОПиУ отвечает на вопрос «какая статья дала разницу»,
но на следующий вопрос — «за счёт кого именно» — ответить нечем: в отчёте
статья это одна цифра за месяц. Чтобы понять, почему ЗП АУП выросла на три
миллиона, а ремонт оборудования на полтора, приходится идти в айко руками.

Здесь тот же оборот по счёту разбирается на составляющие: кто контрагент,
какая номенклатура, каким типом документа проведено. Дальше страница аудита
раскрывает любую статью и показывает, что изменилось между двумя месяцами
построчно — появилось, исчезло, выросло.

Три вещи, из-за которых наивная выгрузка врёт, и как они решены:

  1. Размер. Группировка «счёт × контрагент × номенклатура» по всем счетам
     даёт десятки тысяч строк в месяц — файл станет неподъёмным для браузера.
     Поэтому разрезов два независимых (по контрагентам и по номенклатуре),
     а внутри статьи хранится верхушка по модулю суммы, остальное сворачивается
     в строку «прочее». Сумма разреза всегда равна обороту статьи.

  2. Знак. У доходных строк оборот кредитовый, у расходных дебетовый — ровно
     как в gen_opiu_iiko.py. Считаем обе стороны и берём ту же величину
     debit = приход − расход, чтобы расшифровка сходилась со строкой отчёта.

  3. Время. Закрытые месяцы не меняются, тянуть их каждый прогон незачем.
     Файл накопительный: заново тянутся только последние три месяца и те,
     которых ещё нет.

Только чтение iiko. Запускается в GitHub Actions после gen_opiu_iiko.py.
"""
import calendar, json, os, sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import almaty
import opiu_full as OF

OUT = os.path.join(HERE, "opiu_detail.js")
DIAG = os.path.join(HERE, "opiu_detail_fields.json")
FIRST = "2025-01"        # с какого месяца ведём историю
REFRESH_TAIL = 3         # сколько последних месяцев перетягиваем каждый раз
TOP = 40                 # сколько строк храним внутри статьи, остальное — «прочее»
MIN_KEEP = 1000          # мелочь меньше этой суммы в хвост не выносим отдельной строкой

# Счёт «Зарплата» исключён по той же причине, что и в gen_opiu_iiko.py:
# это расчётный счёт с персоналом, на нём и начисления, и их закрытие,
# оборот по нему не равен строке отчёта.
SKIP_ACCOUNTS = {"Зарплата"}

# Разрезы. Каждый — отдельный запрос: так строк на порядок меньше, чем при
# перекрёстной группировке, и любой из них можно потерять, не потеряв остальные.
CUTS = [
    ("ctr",  ["Account.Name", "Counteragent.Name"],                "по контрагентам"),
    ("prod", ["Account.Name", "Product.Name"],                     "по номенклатуре"),
    ("type", ["Account.Name", "TransactionType"],                  "по типу документа"),
    ("dep",  ["Account.Name", "Store.Name"],                       "по складам"),
]

# ── Документы ────────────────────────────────────────────────────────────
# Аудит нужен, чтобы найти неверно разнесённый документ, а сумма по
# контрагенту его не показывает. Поэтому отдельным разрезом тянем сами
# проводки: дата, документ, контрагент, сумма — по ним видно и разовый
# всплеск, и расход, попавший не в свой месяц, и чужой счёт.
#
# Имена полей в OLAP у разных сборок iiko отличаются, а угадывать вслепую
# нельзя: неверное поле роняет весь запрос. Поэтому спрашиваем у сервера
# список доступных колонок и берём первое подходящее из кандидатов.
DOC_CANDS = ["DocumentNumber", "Document.Number", "Document", "TransactionDoc",
             "DocumentType", "OperationType"]
DATE_CANDS = ["DateTime.DateTyped", "DateTime.Typed", "DateTime"]
DOCS_MONTHS = 6      # за сколько последних месяцев храним документы
DOCS_TOP = 30        # сколько документов на статью


def olap_columns():
    """Какие поля OLAP отдаёт эта сборка iiko. Пустой словарь — не беда:
    тогда документы просто не тянем, остальные разрезы работают."""
    try:
        r = OF.s.get(OF.URL + "/resto/api/v2/reports/olap/columns",
                     params={"reportType": "TRANSACTIONS"},
                     headers={"Cookie": "key=" + OF.TOK},
                     verify=False, timeout=120)
        if r.status_code != 200:
            print("[!] список колонок OLAP: HTTP", r.status_code)
            return {}
        js = r.json()
        return js if isinstance(js, dict) else {}
    except Exception as e:
        print("[!] список колонок OLAP не получен:", e)
        return {}


def pick(cands, cols):
    for c in cands:
        if c in cols:
            return c
    return None


def docs(y, m, last_full, date_f, doc_f):
    """Проводки месяца: дата, документ, контрагент, сумма — по счетам."""
    d1 = date(y, m, 1)
    d2 = min(date(y, m, calendar.monthrange(y, m)[1]), last_full)
    if d2 < d1:
        return None
    fields = ["Account.Name", date_f, doc_f, "Counteragent.Name"]
    body = {
        "reportType": "TRANSACTIONS", "buildSummary": "true",
        "groupByRowFields": fields,
        "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
        "filters": {
            "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                   "from": d1.isoformat(),
                                   "to": (d2 + timedelta(days=1)).isoformat(),
                                   "includeLow": True, "includeHigh": True},
            "Department": {"filterType": "IncludeValues", "values": [OF.FZ_DEPT]},
        },
    }
    data = OF.olap(body)
    if data is None:
        return None
    acc = {}
    for row in data:
        an = (row.get("Account.Name") or "—").strip()
        if an in SKIP_ACCOUNTS:
            continue
        v = (row.get("Sum.Incoming") or 0) - (row.get("Sum.Outgoing") or 0)
        if abs(v) < 0.5:
            continue
        dt = str(row.get(date_f) or "")[:10]
        dc = str(row.get(doc_f) or "—").strip() or "—"
        ct = str(row.get("Counteragent.Name") or "—").strip() or "—"
        acc.setdefault(an, []).append([dt, dc, ct, round(v)])
    out = {}
    for an, rows in acc.items():
        rows.sort(key=lambda x: -abs(x[3]))
        out[an] = rows[:DOCS_TOP]
    return out


def month_keys(first, today):
    y, m = int(first[:4]), int(first[5:7])
    out = []
    while (y, m) <= (today.year, today.month):
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def cut(y, m, last_full, fields):
    """Один разрез оборота за месяц. None — если айко не ответил."""
    d1 = date(y, m, 1)
    d2 = min(date(y, m, calendar.monthrange(y, m)[1]), last_full)
    if d2 < d1:
        return None
    body = {
        "reportType": "TRANSACTIONS", "buildSummary": "true",
        "groupByRowFields": fields,
        "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
        "filters": {
            "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                   "from": d1.isoformat(),
                                   "to": (d2 + timedelta(days=1)).isoformat(),
                                   "includeLow": True, "includeHigh": True},
            "Department": {"filterType": "IncludeValues", "values": [OF.FZ_DEPT]},
        },
    }
    return OF.olap(body)


def fold(data, key_field):
    """Сырые строки айко → {счёт: [[имя, сумма], …]}, суммы уже свёрнуты.

    debit = приход − расход: та же величина, что gen_opiu_iiko.py кладёт
    в строку отчёта, поэтому расшифровка сходится со статьёй до тенге."""
    acc = {}
    for row in data or []:
        an = (row.get("Account.Name") or "—").strip()
        if an in SKIP_ACCOUNTS:
            continue
        nm = (row.get(key_field) or "—")
        nm = str(nm).strip() or "—"
        v = (row.get("Sum.Incoming") or 0) - (row.get("Sum.Outgoing") or 0)
        d = acc.setdefault(an, {})
        d[nm] = d.get(nm, 0.0) + v
    out = {}
    for an, d in acc.items():
        rows = [[k, round(v)] for k, v in d.items() if abs(v) >= 0.5]
        if not rows:
            continue
        rows.sort(key=lambda x: -abs(x[1]))
        if len(rows) > TOP:
            tail = rows[TOP:]
            rest = sum(x[1] for x in tail)
            rows = rows[:TOP]
            # Хвост показываем одной строкой: сколько денег и из скольких позиций,
            # иначе не видно, потеряли мы копейки или треть статьи.
            if abs(rest) >= MIN_KEEP:
                rows.append(["прочее · %d позиц." % len(tail), round(rest)])
        out[an] = rows
    return out


def build():
    today = almaty.today()
    last_full = today - timedelta(days=1)
    OF.TOK = OF.auth()

    old = {}
    if os.path.exists(OUT):
        try:
            txt = open(OUT, encoding="utf-8").read()
            i, j = txt.index("{"), txt.rindex("}")
            old = json.loads(txt[i:j + 1]).get("m", {})
        except Exception as e:
            print("[!] старый opiu_detail.js не прочитан:", e)

    cols = olap_columns()
    date_f = pick(DATE_CANDS, cols) if cols else None
    doc_f = pick(DOC_CANDS, cols) if cols else None
    print("поля OLAP: всего %d, дата=%s, документ=%s"
          % (len(cols), date_f, doc_f))

    keys = month_keys(FIRST, today)
    tail = set(keys[-REFRESH_TAIL:])
    docs_from = set(keys[-DOCS_MONTHS:])
    data = {}
    fields_ok, fields_bad = [], []

    for ym in keys:
        y, m = int(ym[:4]), int(ym[5:7])
        cached = ym in old and ym not in tail
        if cached:
            # Месяц закрыт и уже посчитан — разрезы не перетягиваем. Но если
            # документов в нём ещё нет (разрез появился позже кэша), доберём
            # только их: иначе первичка за прошлые месяцы никогда не подтянется.
            data[ym] = old[ym]
            need_docs = (date_f and doc_f and ym in docs_from
                         and not any("doc" in v for v in old[ym].values()))
            if not need_docs:
                continue
            dd = docs(y, m, last_full, date_f, doc_f)
            if dd:
                for an, rows in dd.items():
                    data[ym].setdefault(an, {})["doc"] = rows
                print("%s: добраны документы по %d счетам" % (ym, len(dd)))
            continue
        month = {}
        for code, fields, _title in CUTS:
            raw = cut(y, m, last_full, fields)
            if raw is None:
                # разрез не получен — не роняем месяц, просто его не будет
                if fields[-1] not in fields_bad:
                    fields_bad.append(fields[-1])
                continue
            if fields[-1] not in fields_ok:
                fields_ok.append(fields[-1])
            folded = fold(raw, fields[-1])
            for an, rows in folded.items():
                month.setdefault(an, {})[code] = rows
        if date_f and doc_f and ym in docs_from:
            dd = docs(y, m, last_full, date_f, doc_f)
            if dd:
                for an, rows in dd.items():
                    month.setdefault(an, {})["doc"] = rows
        if month:
            data[ym] = month
            print("%s: счетов %d" % (ym, len(month)))
        elif ym in old:
            data[ym] = old[ym]

    meta = {
        "built": almaty.now().strftime("%Y-%m-%d %H:%M"),
        "dept": OF.FZ_DEPT,
        "top": TOP,
        "cuts": [{"code": c, "title": t} for c, _f, t in CUTS]
                + ([{"code": "doc", "title": "документы"}] if (date_f and doc_f) else []),
        "docsTop": DOCS_TOP, "docsMonths": DOCS_MONTHS,
        "dateField": date_f, "docField": doc_f,
        "columns": sorted(cols.keys()) if cols else [],
        "fieldsOk": fields_ok, "fieldsBad": fields_bad,
    }
    payload = {"meta": meta, "m": data}
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.OPIU_DETAIL=")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    json.dump(meta, open(DIAG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("opiu_detail.js: месяцев %d, размер %.0f КБ"
          % (len(data), os.path.getsize(OUT) / 1024))
    if fields_bad:
        print("[!] не отдались разрезы:", ", ".join(fields_bad))


if __name__ == "__main__":
    build()
