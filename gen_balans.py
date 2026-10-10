# -*- coding: utf-8 -*-
"""
gen_balans.py — «Баланс по контрагентам» как в гугл-таблице, но прямо из айко.

Зачем. В книге «Баланс по поставщикам» колонки идут тройками: долг на начало
периода, приход товара за период, оплата за период, долг на конец. Заполняется
это руками и только по недельным срезам. В айко те же движения лежат на двух
счетах, и их можно сложить за любой отрезок:

    КЗ — «Задолженность перед поставщиками» (3.06): сколько должны мы;
    ДЗ — «5-Дебит.задолж.» (3.08):              сколько должны нам.

Что выгружаем. Не баланс на каждый день — это мегабайты, — а входящий остаток
на 1 января и движения только за те дни, когда они были, отдельно приходом и
оплатой. Страница складывает их сама и поэтому умеет любой период, а не только
недельный срез.

Знак. Для КЗ сальдо = расход − приход по счёту: плюс — мы должны поставщику,
минус — у него лежит наша переплата. Для ДЗ знак зеркальный и определяется
константой DZ_SIGN: проверяется по контрольной сумме в логе прогона.
"""
import sys, os, re, json, hashlib, warnings
from datetime import date, timedelta
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import almaty

OWN    = re.compile(r"^\d+\s*[-–]")   # «102-Яндекс лавка» — наша точка, не поставщик
BASE   = date(2026, 1, 1)        # точка отсчёта: всё, что раньше, — входящий остаток
OUTPUT = "balans.js"

# (ключ, счёт в айко, подпись, знак сальдо)
#   знак  1: сальдо = расход − приход   (растёт от расхода по счёту)
#   знак −1: сальдо = приход − расход
SIDES = [
    ("kz", "Задолженность перед поставщиками", "Кредиторка — сколько должны мы",  1),
    ("dz", "5-Дебит.задолж.",                  "Дебиторка — сколько должны нам", -1),
]

src   = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"',   src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"',  src).group(1)


def auth():
    s = requests.Session()
    tok = s.get(f"{URL}/resto/api/auth",
                params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
                verify=False, timeout=60).text.strip().strip('"')
    return s, {"Cookie": f"key={tok}", "Content-Type": "application/json"}


def olap(s, H, account, group, d_from, d_to_excl):
    """Проводки по одному счёту за полуинтервал [d_from, d_to_excl)."""
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": group,
            "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
            "filters": {
                "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                       "from": d_from.isoformat(), "to": d_to_excl.isoformat(),
                                       "includeLow": True, "includeHigh": False},
                "Account.Name": {"filterType": "IncludeValues", "values": [account]}}}
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers=H, data=json.dumps(body),
               verify=False, timeout=900)
    if r.status_code != 200:
        raise RuntimeError(f"OLAP {r.status_code}: {r.text[:300]}")
    return r.json().get("data", [])


def collect(s, H, account, sign, today):
    tomorrow = today + timedelta(days=1)

    opening = {}
    for x in olap(s, H, account, ["Counteragent.Name"], date(2015, 1, 1), BASE):
        n = (x.get("Counteragent.Name") or "").strip()
        if n:
            opening[n] = opening.get(n, 0.0) + sign * (
                (x.get("Sum.Outgoing") or 0.0) - (x.get("Sum.Incoming") or 0.0))

    # движения по дням: отдельно приход товара (рост долга) и оплата (гашение)
    mv = {}
    for x in olap(s, H, account, ["Counteragent.Name", "DateTime.DateTyped"], BASE, tomorrow):
        n = (x.get("Counteragent.Name") or "").strip()
        d = str(x.get("DateTime.DateTyped") or "")[:10]
        if not n or not d:
            continue
        out = x.get("Sum.Outgoing") or 0.0
        inc = x.get("Sum.Incoming") or 0.0
        up, down = (out, inc) if sign > 0 else (inc, out)   # up — долг растёт, down — гасится
        if abs(up) < 0.5 and abs(down) < 0.5:
            continue
        idx = (date.fromisoformat(d) - BASE).days
        if idx < 0:
            continue
        cell = mv.setdefault(n, {}).setdefault(idx, [0.0, 0.0])
        cell[0] += up
        cell[1] += down

    rows = []
    for n in sorted(set(list(opening) + list(mv)), key=lambda x: x.lower()):
        pts = sorted(mv.get(n, {}).items())
        op = round(opening.get(n, 0.0))
        if not pts and abs(op) < 1:
            continue
        r = {"n": n, "open": op,
             "mv": [[i, round(a), round(b)] for i, (a, b) in pts]}
        # На счёте 3.06 висят не только поставщики: там же наши точки и
        # покупатели — «4-Базилик 4 (закрыто)», «102-Яндекс лавка». В айко они
        # пронумерованы, поставщики — нет. Помечаем, чтобы страница по
        # умолчанию показывала кредиторку, а не внутренние обороты.
        if OWN.match(n):
            r["own"] = 1
        rows.append(r)
    return rows


def main():
    today = almaty.now().date()
    s, H = auth()

    data = {"updated": almaty.now().strftime("%d.%m.%Y %H:%M"),
            "base": BASE.isoformat(),
            "maxDay": (today - BASE).days,
            "sides": {}}

    for key, account, title, sign in SIDES:
        rows = collect(s, H, account, sign, today)
        tot = sum(r["open"] + sum(a - b for _, a, b in r["mv"]) for r in rows)
        data["sides"][key] = {"account": account, "title": title, "rows": rows}
        print(f"{key}: контрагентов {len(rows)}, итого на {today:%d.%m.%Y}: "
              f"{tot:,.0f} ₸".replace(",", " "))
        big = sorted(rows, key=lambda r: -(r["open"] + sum(a - b for _, a, b in r["mv"])))[:5]
        for r in big:
            v = r["open"] + sum(a - b for _, a, b in r["mv"])
            print(f"    {r['n'][:44]:44} {v:>15,.0f}".replace(",", " "))

    with open(os.path.join(HERE, OUTPUT), "w", encoding="utf-8") as f:
        f.write("window.BALANS = " + json.dumps(data, ensure_ascii=False,
                                                separators=(",", ":")) + ";\n")
    print(f"{OUTPUT}: {os.path.getsize(os.path.join(HERE, OUTPUT)):,} байт".replace(",", " "))


if __name__ == "__main__":
    main()
