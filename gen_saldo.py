# -*- coding: utf-8 -*-
"""
gen_saldo.py — баланс по контрагентам из листа КЗ на любую дату, прямо из айко.

Зачем. В гугл-таблице баланс стоит только на недельные срезы, и колонку
заполняют руками. В айко тот же остаток есть на любой день: счёт
«Задолженность перед поставщиками» (3.06). Сверено на 25.09.2026 — Витамин+,
Глобал Фуд, Handy Yummy, Adolar, KazBeef, Элита-Трейд сошлись до тенге.

Знак. Сальдо = расход − приход по счёту: больше нуля — мы должны поставщику,
меньше нуля — у него лежит наша переплата.

Список контрагентов берём из листа КЗ: на счёте 3.06 висят ещё и покупатели,
и закрытые точки, и они в кредиторку не входят.

Формат выгрузки. Чтобы файл не распух, отдаём не баланс на каждый день, а
входящий остаток на 1 января и движения только по тем дням, когда они были.
Страница складывает их сама.
"""
import sys, os, re, json, csv, io, hashlib, warnings
from datetime import date, timedelta
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import almaty
from parse_dz_kz import fetch_csv, is_company, find_header_row, KZ_GID

ACCOUNT = "Задолженность перед поставщиками"
BASE    = date(2026, 1, 1)          # точка отсчёта: до неё — входящий остаток
OUTPUT  = "saldo.js"

src   = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"', src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"', src).group(1)


def norm(s):
    """Для сверки имён: регистр, пробелы и кавычки в таблице и в айко гуляют."""
    s = re.sub(r"[«»\"'`]", "", str(s or "")).lower()
    return re.sub(r"\s+", " ", s).strip()


FORM = re.compile(r"^(.*?\b(?:тоо|ип|ао|жшс|llp|ltd|кх)\b)", re.I | re.U)


def core(s):
    """Имя без хвоста-пояснения. В таблице пишут «Кристалл полимер ТОО хоз
    товары», в айко — «Кристалл полимер ТОО»: обрезаем по форме собственности.
    Если формы нет, берём первые два слова — этого хватает, чтобы поймать
    «ЕСИК ЕТ МЯСОКОМБИНАТ» против «Есик Ет»."""
    n = norm(s)
    m = FORM.match(n)
    if m:
        return m.group(1).strip()
    return " ".join(n.split()[:2])


def kz_names():
    rows = fetch_csv(KZ_GID)
    if not rows:
        sys.exit("лист КЗ не прочитался")
    hi, _ = find_header_row(rows, r"кз\s+на|задолженность\s+на")
    out, seen = [], set()
    for row in rows[(hi or 3) + 1:]:
        n = (row[0] if row else "").strip()
        if not is_company(n) or norm(n) in seen:
            continue
        seen.add(norm(n)); out.append(n)
    return out


def auth():
    s = requests.Session()
    tok = s.get(f"{URL}/resto/api/auth",
                params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
                verify=False, timeout=60).text.strip().strip('"')
    return s, {"Cookie": f"key={tok}", "Content-Type": "application/json"}


def olap(s, H, group, d_from, d_to_excl, names=None):
    flt = {"DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                  "from": d_from.isoformat(), "to": d_to_excl.isoformat(),
                                  "includeLow": True, "includeHigh": False},
           "Account.Name": {"filterType": "IncludeValues", "values": [ACCOUNT]}}
    if names:
        flt["Counteragent.Name"] = {"filterType": "IncludeValues", "values": names}
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": group,
            "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
            "filters": flt}
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers=H, data=json.dumps(body),
               verify=False, timeout=900)
    if r.status_code != 200:
        raise RuntimeError(f"OLAP {r.status_code}: {r.text[:300]}")
    return r.json().get("data", [])


def main():
    today = almaty.now().date()
    tomorrow = today + timedelta(days=1)

    sheet = kz_names()
    print(f"контрагентов в листе КЗ: {len(sheet)}")

    s, H = auth()

    # какие имена вообще есть на счёте — сверяем по нормализованному виду
    allc = olap(s, H, ["Counteragent.Name"], date(2015, 1, 1), tomorrow)
    iiko_names = {}
    for x in allc:
        n = (x.get("Counteragent.Name") or "").strip()
        if n:
            iiko_names.setdefault(norm(n), n)

    # по «ядру» имени — только там, где кандидат ровно один, иначе легко
    # склеить двух разных поставщиков
    by_core = {}
    for k, v in iiko_names.items():
        by_core.setdefault(core(v), []).append(v)

    matched, missing, fuzzy = [], [], []
    for n in sheet:
        hit = iiko_names.get(norm(n))
        if not hit:
            cand = by_core.get(core(n)) or []
            if len(cand) == 1:
                hit, _ = cand[0], fuzzy.append((n, cand[0]))
        (matched.append(hit) if hit else missing.append(n))
    matched = sorted(set(matched))
    print(f"нашлись в айко: {len(matched)}, не нашлись: {len(missing)}")
    if fuzzy:
        print(f"  сведены по ядру имени ({len(fuzzy)}):")
        for a, b in fuzzy:
            print(f"    «{a}» → «{b}»")
    if missing:
        print("  нет на счёте 3.06: " + ", ".join(missing[:20])
              + (" …" if len(missing) > 20 else ""))

    # входящий остаток на 1 января
    opening = {}
    for x in olap(s, H, ["Counteragent.Name"], date(2015, 1, 1), BASE, matched):
        n = (x.get("Counteragent.Name") or "").strip()
        if n:
            opening[n] = (x.get("Sum.Outgoing") or 0.0) - (x.get("Sum.Incoming") or 0.0)

    # движения по дням
    mv = {}
    for x in olap(s, H, ["Counteragent.Name", "DateTime.DateTyped"], BASE, tomorrow, matched):
        n = (x.get("Counteragent.Name") or "").strip()
        d = str(x.get("DateTime.DateTyped") or "")[:10]
        if not n or not d:
            continue
        delta = (x.get("Sum.Outgoing") or 0.0) - (x.get("Sum.Incoming") or 0.0)
        if abs(delta) < 0.5:
            continue
        idx = (date.fromisoformat(d) - BASE).days
        if idx < 0:
            continue
        mv.setdefault(n, {})
        mv[n][idx] = mv[n].get(idx, 0.0) + delta

    rows = []
    for n in matched:
        pts = sorted(mv.get(n, {}).items())
        op = round(opening.get(n, 0.0))
        if not pts and abs(op) < 1:
            continue                      # ни остатка, ни движений — не показываем
        rows.append({"name": n, "open": op,
                     "mv": [[i, round(v)] for i, v in pts]})
    rows.sort(key=lambda r: r["name"].lower())

    data = {"updated": almaty.now().strftime("%d.%m.%Y %H:%M"),
            "account": ACCOUNT,
            "base": BASE.isoformat(),
            "maxDay": (today - BASE).days,
            "note": "сальдо = расход − приход по счёту 3.06: плюс — мы должны, "
                    "минус — у поставщика наша переплата",
            "missing": missing,
            "rows": rows}

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("window.SALDO = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")

    tot = sum(r["open"] + sum(v for _, v in r["mv"]) for r in rows)
    print(f"строк {len(rows)}, итого на {today:%d.%m.%Y}: {tot:,.0f} ₸".replace(",", " "))
    print(f"{OUTPUT}: {os.path.getsize(OUTPUT):,} байт".replace(",", " "))


if __name__ == "__main__":
    main()
