# -*- coding: utf-8 -*-
"""
gen_balans.py — «Баланс по контрагентам» как в книге, но собранный из айко.

Как считаем. Ровно тем же отчётом, которым пользуется Ольга, — «приход и
оплата товара по накладным». В айко это проводки определённых типов:

    кредиторка  приход  = INVOICE                 (приходная накладная)
                оплата  = INVOICE_PAYMENT(+AUTO)  (оплата поставщику)
    дебиторка   отгрузка= OUTGOING_INVOICE_REVENUE(расходная накладная, выручка)
                оплата  = PAYIN, где контр-счёт «Задолженность перед
                          поставщиками» или «Расчёты с гостями» — то есть
                          деньги, закрывающие долг покупателя

Сверено на неделе 03.10–09.10.2026 с книгой: приход 31 967 153, оплата
30 884 202, отгрузка 67 967 998 против 67 941 198 в книге, поступление
62 362 863 — тенга в тенгу.

Входящий остаток. Движения айко отдаёт сколько угодно, а точку отсчёта —
нет: долг на начало года зафиксирован только в книге. Берём его оттуда, из
колонки «на 04.01.26», и дальше всё считается из айко.

Разрезы. По кредиторке контрагент в книге и в айко — одно лицо, поэтому
строки идут как есть. По дебиторке в книге сеть сведена в одну строку
(«99-RP АЗС 1 (все точки)»), а в айко у неё карточка на каждую точку —
складываем их по номеру сети, иначе не сверить.
"""
import sys, os, re, json, hashlib, warnings
from datetime import date, timedelta
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import almaty
from parse_dz_kz import fetch_csv, KZ_GID, DZ_GID

BASE   = date(2026, 1, 4)        # входящий остаток из книги на этот день
OUTPUT = "balans.js"

T_IN_KZ  = ["INVOICE"]
T_PAY_KZ = ["INVOICE_PAYMENT", "INVOICE_PAYMENT_AUTO"]
T_IN_DZ  = ["OUTGOING_INVOICE_REVENUE"]
T_PAY_DZ = ["PAYIN"]
DZ_PAY_CONTRA = {"задолженность перед поставщиками", "расчеты с гостями",
                 "расчёты с гостями"}

src   = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"',   src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"',  src).group(1)

PREF = re.compile(r"^(\d+)\s*[-–\s]")


def chain(n):
    """Номер сети: «99-RP АЗС основной» и «99-RP АЗС 1 (все точки)» — одно."""
    m = PREF.match(str(n or ""))
    return m.group(1) if m else None


def norm(s):
    s = re.sub(r"^\d+\s*[-–]?\s*", "", str(s or ""))
    s = re.sub(r"[«»\"'`]", "", s).lower()
    s = re.sub(r"\((все точки|дистрибьютор|закрыто)\)", "", s)
    return re.sub(r"[^a-zа-я0-9]+", "", s)


def num(v):
    s = re.sub(r"[\s  ]", "", str(v or "")).replace(",", ".")
    s = s.replace("−", "-").replace("–", "-")
    if s in ("", "-", "—"):
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^\d.\-]", "", s.strip("()"))
    try:
        x = float(s)
    except Exception:
        return 0.0
    return -x if neg else x


def opening(gid, pattern, sign):
    """Долг на 04.01.26 из книги: единственная точка отсчёта, какая есть."""
    rows = fetch_csv(gid)
    if not rows:
        print("  книга не прочиталась — входящие остатки будут нулевые")
        return {}
    col = hi = None
    for i, r in enumerate(rows[:12]):
        for j, c in enumerate(r):
            if re.search(pattern, str(c or ""), re.I):
                hi, col = i, j
                break
        if col is not None:
            break
    if col is None:
        print("  колонка входящего остатка не нашлась:", pattern)
        return {}
    print(f"  входящий остаток: строка {hi}, колонка {col} «{rows[hi][col].strip()}»")
    out = {}
    for r in rows[hi + 1:]:
        if not r:
            continue
        n = (r[0] or "").strip()
        if not n or n.lower().startswith(("итого", "всего", "сумма")):
            continue
        v = num(r[col]) * sign if len(r) > col else 0.0
        out[n] = out.get(n, 0.0) + v
    return out


def auth():
    s = requests.Session()
    tok = s.get(f"{URL}/resto/api/auth",
                params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
                verify=False, timeout=60).text.strip().strip('"')
    return s, {"Cookie": f"key={tok}", "Content-Type": "application/json"}


def olap(s, H, group, types, d_from, d_to_excl):
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": group,
            "aggregateFields": ["Sum.Incoming"],
            "filters": {
                "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                       "from": d_from.isoformat(), "to": d_to_excl.isoformat(),
                                       "includeLow": True, "includeHigh": False},
                "TransactionType": {"filterType": "IncludeValues", "values": types}}}
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers=H, data=json.dumps(body),
               verify=False, timeout=900)
    if r.status_code != 200:
        raise RuntimeError(f"OLAP {r.status_code}: {r.text[:300]}")
    return r.json().get("data", [])


def collect(s, H, d_to_excl):
    """День за днём: приход/отгрузка и оплата по каждому контрагенту."""
    mv = {"kz": {}, "dz": {}}

    def add(side, name, day, up, down):
        if not name or not day:
            return
        i = (date.fromisoformat(day[:10]) - BASE).days
        if i < 0:
            return
        c = mv[side].setdefault(name, {}).setdefault(i, [0.0, 0.0])
        c[0] += up
        c[1] += down

    for x in olap(s, H, ["Counteragent.Name", "DateTime.DateTyped"], T_IN_KZ, BASE, d_to_excl):
        add("kz", (x.get("Counteragent.Name") or "").strip(),
            str(x.get("DateTime.DateTyped") or ""), x.get("Sum.Incoming") or 0.0, 0.0)
    for x in olap(s, H, ["Counteragent.Name", "DateTime.DateTyped"], T_PAY_KZ, BASE, d_to_excl):
        add("kz", (x.get("Counteragent.Name") or "").strip(),
            str(x.get("DateTime.DateTyped") or ""), 0.0, x.get("Sum.Incoming") or 0.0)
    for x in olap(s, H, ["Counteragent.Name", "DateTime.DateTyped"], T_IN_DZ, BASE, d_to_excl):
        add("dz", (x.get("Counteragent.Name") or "").strip(),
            str(x.get("DateTime.DateTyped") or ""), x.get("Sum.Incoming") or 0.0, 0.0)
    # оплата покупателя — это PAYIN, закрывающий его долг, а не любой приход денег
    for x in olap(s, H, ["Counteragent.Name", "DateTime.DateTyped", "Contr-Account.Name"],
                  T_PAY_DZ, BASE, d_to_excl):
        if (x.get("Contr-Account.Name") or "").strip().lower() not in DZ_PAY_CONTRA:
            continue
        add("dz", (x.get("Counteragent.Name") or "").strip(),
            str(x.get("DateTime.DateTyped") or ""), 0.0, x.get("Sum.Incoming") or 0.0)
    return mv


def build(side, mv, book, group_chains):
    """Складываем движения и входящий остаток в строки отчёта."""
    rows, used = {}, set()

    def key(n):
        c = chain(n)
        return ("#" + c) if (group_chains and c) else n

    for n, days in mv.items():
        k = key(n)
        r = rows.setdefault(k, {"n": n, "open": 0.0, "mv": {}, "src": []})
        r["src"].append(n)
        if group_chains and chain(n) and len(n) > len(r["n"]):
            r["n"] = n
        for i, (a, b) in days.items():
            c = r["mv"].setdefault(i, [0.0, 0.0])
            c[0] += a
            c[1] += b

    # входящий остаток из книги — по имени, а для сетей по номеру
    idx = {}
    for k, r in rows.items():
        idx.setdefault(norm(r["n"]), k)
        for sn in r["src"]:
            idx.setdefault(norm(sn), k)
        c = chain(r["n"])
        if group_chains and c:
            idx.setdefault("#" + c, k)
    lost = []
    for bn, bv in book.items():
        if abs(bv) < 1:
            continue
        c = chain(bn)
        k = (idx.get("#" + c) if (group_chains and c) else None) or idx.get(norm(bn))
        if not k:
            k = ("#" + c) if (group_chains and c) else bn
            if k not in rows:
                rows[k] = {"n": bn, "open": 0.0, "mv": {}, "src": [bn]}
                lost.append(bn)
        rows[k]["open"] += bv
        used.add(bn)

    out = []
    for k, r in sorted(rows.items(), key=lambda kv: kv[1]["n"].lower()):
        pts = sorted(r["mv"].items())
        op = round(r["open"])
        if not pts and abs(op) < 1:
            continue
        row = {"n": r["n"], "open": op,
               "mv": [[i, round(a), round(b)] for i, (a, b) in pts]}
        if len(r["src"]) > 1:
            row["src"] = sorted(r["src"])
        out.append(row)
    return out, lost


def main():
    today = almaty.now().date()
    tomorrow = today + timedelta(days=1)

    print("-> входящие остатки из книги")
    op_kz = opening(KZ_GID, r"задолженность\s+на\s+04\.01\.26", -1)   # в книге КЗ минусом
    op_dz = opening(DZ_GID, r"дз\s+на\s+04\.01\.26",             1)
    print(f"   КЗ {len(op_kz)} строк, ДЗ {len(op_dz)} строк")

    print("-> движения из айко по накладным")
    s, H = auth()
    mv = collect(s, H, tomorrow)

    kz, lost_kz = build("kz", mv["kz"], op_kz, False)
    dz, lost_dz = build("dz", mv["dz"], op_dz, True)

    data = {"updated": almaty.now().strftime("%d.%m.%Y %H:%M"),
            "base": BASE.isoformat(),
            "maxDay": (today - BASE).days,
            "note": "приход и оплата — из айко по накладным; долг на 04.01.2026 — из книги",
            "sides": {
                "kz": {"title": "Кредиторка — сколько должны мы",
                       "src": "INVOICE / INVOICE_PAYMENT", "rows": kz},
                "dz": {"title": "Дебиторка — сколько должны нам",
                       "src": "OUTGOING_INVOICE_REVENUE / PAYIN", "rows": dz}}}

    with open(os.path.join(HERE, OUTPUT), "w", encoding="utf-8") as f:
        f.write("window.BALANS = " + json.dumps(data, ensure_ascii=False,
                                                separators=(",", ":")) + ";\n")

    for k, rows, lost in (("kz", kz, lost_kz), ("dz", dz, lost_dz)):
        tot = sum(r["open"] + sum(a - b for _, a, b in r["mv"]) for r in rows)
        print(f"{k}: строк {len(rows)}, итого на {today:%d.%m.%Y}: "
              f"{tot:,.0f} ₸".replace(",", " "))
        if lost:
            print(f"    в книге есть, в айко движений нет ({len(lost)}): "
                  + ", ".join(lost[:8]))
        for r in sorted(rows, key=lambda r: -(r["open"] + sum(a - b for _, a, b in r["mv"])))[:6]:
            v = r["open"] + sum(a - b for _, a, b in r["mv"])
            print(f"    {r['n'][:42]:42} {v:>15,.0f}".replace(",", " "))
    print(f"{OUTPUT}: {os.path.getsize(os.path.join(HERE, OUTPUT)):,} байт".replace(",", " "))


if __name__ == "__main__":
    main()
