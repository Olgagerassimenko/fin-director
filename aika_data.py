# -*- coding: utf-8 -*-
"""
aika_data.py — «Айка»: всё, что происходит в айко, и что с этим стало со счетами.

Зачем. Журнал событий айко живёт один день: на запрос с любым периодом он
отдаёт только сегодняшние события и обнуляется назавтра. Значит, историю
правок надо копить самим — иначе через сутки уже не узнать, кто и что трогал.

Что делает каждый запуск:
  1. Забирает журнал событий и дописывает новые в _айка/события.json
     (ключ — id события, повторы не дублируются).
  2. Снимает обороты по ВСЕМ счетам помесячно за год и входящее сальдо
     на 1 января.
  3. Сравнивает обороты закрытых месяцев с прошлым снимком. Любое
     расхождение — это правка задним числом; она ложится в _айка/правки.json
     и больше оттуда не пропадает.
  4. Собирает aika_data.js для страницы айка.html.

Закрытый период — всё, что раньше первого числа текущего месяца. Дату можно
переопределить переменной окружения AIKA_CLOSED (ГГГГ-ММ-ДД).
"""
import sys, os, re, json, hashlib, warnings, datetime, calendar, collections
import xml.etree.ElementTree as ET
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    import almaty
    TODAY = almaty.today()
except Exception:
    TODAY = datetime.date.today()

src   = open(os.path.join(HERE, "iiko_export.py"), encoding="utf-8").read()
URL   = re.search(r'URL\s*=\s*"([^"]+)"', src).group(1)
LOGIN = re.search(r'LOGIN\s*=\s*"([^"]+)"', src).group(1)
PASS  = re.search(r'PASS\s*=\s*"([^"]+)"', src).group(1)

DIR   = os.path.join(HERE, "_айка")
EV_F  = os.path.join(DIR, "события.json")
SNAP_F= os.path.join(DIR, "обороты.json")
FIX_F = os.path.join(DIR, "правки.json")
OUT   = os.path.join(HERE, "aika_data.js")
YEAR  = TODAY.year

# события, которые нас интересуют: всё, что меняет учёт или номенклатуру
KEEP = {"documentCreated", "documentModified", "documentDeleted", "documentProcessed",
        "documentUnprocessed", "accountingTransactionUpdated", "accountingTransactionCreated",
        "accountingTransactionDeleted", "productCreated", "productUpdated", "productDeleted",
        "backLogin", "backLogout", "pinAuthorization", "priceUpdated", "employeeUpdated"}
# шум репликации и обменов не копим: он ничего не говорит о деньгах
DROP = {"dataReplicationResult", "customersExchangeEvent", "nomenclatureExportEvent"}

DOCRU = {
    "INCOMING_INVOICE": "Приходная накладная", "OUTGOING_INVOICE": "Расходная накладная",
    "RETURNED_INVOICE": "Возвратная накладная", "INCOMING_SERVICE": "Акт приёма услуг",
    "OUTGOING_SERVICE": "Акт оказания услуг", "WRITEOFF_DOCUMENT": "Акт списания",
    "PRODUCTION_DOCUMENT": "Акт приготовления", "INTERNAL_TRANSFER": "Внутреннее перемещение",
    "INCOMING_INVENTORY": "Инвентаризация", "TRANSFORMATION_DOCUMENT": "Акт переработки",
    "DISASSEMBLE_DOCUMENT": "Акт разбора", "CASH_CONSUMPTION": "Расходный кассовый ордер",
    "CASH_INCOME": "Приходный кассовый ордер", "PAYMENT_DOCUMENT": "Платёжный документ",
    "ACCOUNT_TRANSACTION": "Проводка вручную", "MENU_CHANGE_DOCUMENT": "Изменение меню",
    "RETURNED_INVOICE_COST_AFFECTED": "Возврат с себестоимостью",
}


def log(*a):
    print(" ".join(str(x) for x in a), flush=True)


def auth():
    s = requests.Session()
    tok = s.get(f"{URL}/resto/api/auth",
                params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
                verify=False, timeout=60).text.strip().strip('"')
    return s, tok, {"Cookie": f"key={tok}", "Content-Type": "application/json"}


def olap(s, H, group, d_from, d_to_excl, extra=None):
    flt = {"DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                  "from": d_from, "to": d_to_excl,
                                  "includeLow": True, "includeHigh": False}}
    if extra:
        flt.update(extra)
    body = {"reportType": "TRANSACTIONS", "buildSummary": "true",
            "groupByRowFields": group, "aggregateFields": ["Sum.Incoming", "Sum.Outgoing"],
            "filters": flt}
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers=H, data=json.dumps(body),
               verify=False, timeout=900)
    if r.status_code != 200:
        raise RuntimeError("OLAP %d: %s" % (r.status_code, r.text[:300]))
    return r.json().get("data", [])


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


# ──────────────────────────────────────────────────────────────────────────
# 1. ЖУРНАЛ СОБЫТИЙ
# ──────────────────────────────────────────────────────────────────────────
def employees(s, tok):
    """id → ФИО. Имя в событии приходит идентификатором."""
    try:
        r = s.get(URL + "/resto/api/employees", params={"key": tok}, verify=False, timeout=300)
        root = ET.fromstring(r.text)
        out = {}
        for e in root.iter("employee"):
            i = (e.findtext("id") or "").strip()
            n = (e.findtext("name") or "").strip() or (e.findtext("displayName") or "").strip()
            if i:
                out[i] = n
        return out
    except Exception as e:
        log("справочник сотрудников не прочитался:", e)
        return {}


def pull_events(s, tok, emp):
    """Журнал айко отдаёт только текущие сутки — поэтому и копим."""
    got = []
    r = s.get(URL + "/resto/api/events", params={"key": tok}, verify=False, timeout=300)
    if r.status_code != 200:
        log("журнал: HTTP", r.status_code)
        return got, None
    try:
        root = ET.fromstring(r.text)
    except Exception as e:
        log("журнал не разобрался:", e)
        return got, None
    rev = root.findtext("revision")
    for ev in root.iter("event"):
        t = (ev.findtext("type") or "").strip()
        if t in DROP or (KEEP and t not in KEEP):
            continue
        a = {}
        for at in ev.findall("attribute"):
            a[(at.findtext("name") or "").strip()] = (at.findtext("value") or "").strip()
        u = a.get("user") or ""
        got.append({
            "id": (ev.findtext("id") or "").strip(),
            "d": (ev.findtext("date") or "").strip()[:19],
            "t": t,
            "u": emp.get(u, u if len(u) < 40 else ""),
            "dt": a.get("documentType") or "",
            "dn": a.get("documentNumber") or "",
            "di": a.get("documentId") or "",
            "ac": a.get("account") or "",
        })
    return got, rev


# ──────────────────────────────────────────────────────────────────────────
# 2. ОБОРОТЫ ПО СЧЕТАМ
# ──────────────────────────────────────────────────────────────────────────
GKEY = ["Account.Code", "Account.Name", "Account.Type", "Account.Group",
        "Account.IsCashFlowAccount", "Account.AccountHierarchyTop",
        "Account.AccountHierarchySecond", "Account.AccountHierarchyThird",
        "Account.StoreOrAccount"]


def akey(x):
    return (str(x.get("Account.Code") or "").strip() + "|" + str(x.get("Account.Name") or "").strip())


def months_of(year, upto):
    out = []
    for m in range(1, 13):
        a = datetime.date(year, m, 1)
        if a > upto:
            break
        out.append("%04d-%02d" % (year, m))
    return out


def month_bounds(mk):
    y, m = int(mk[:4]), int(mk[5:7])
    a = datetime.date(y, m, 1)
    b = datetime.date(y + 1, 1, 1) if m == 12 else datetime.date(y, m + 1, 1)
    return a.isoformat(), b.isoformat()


def collect_accounts(s, H, mons):
    meta, mv = {}, collections.defaultdict(dict)
    for mk in mons:
        a, b = month_bounds(mk)
        for x in olap(s, H, GKEY, a, b):
            k = akey(x)
            if k not in meta:
                meta[k] = {
                    "code": str(x.get("Account.Code") or "").strip(),
                    "name": str(x.get("Account.Name") or "").strip(),
                    "type": x.get("Account.Type") or "",
                    "grp":  x.get("Account.Group") or "",
                    "cf":   1 if x.get("Account.IsCashFlowAccount") == "CASH_FLOW" else 0,
                    "top":  str(x.get("Account.AccountHierarchyTop") or "").strip(),
                    "sec":  str(x.get("Account.AccountHierarchySecond") or "").strip(),
                    "thr":  str(x.get("Account.AccountHierarchyThird") or "").strip(),
                    "so":   x.get("Account.StoreOrAccount") or "",
                }
            i = round(float(x.get("Sum.Incoming") or 0), 2)
            o = round(float(x.get("Sum.Outgoing") or 0), 2)
            if i or o:
                p = mv[k].get(mk) or [0, 0]
                mv[k][mk] = [round(p[0] + i, 2), round(p[1] + o, 2)]
        log("  обороты", mk, "— счетов", len(meta))
    return meta, mv


def collect_open(s, H, year):
    """Входящее сальдо на 1 января: приход минус расход за всю историю до."""
    out = {}
    for x in olap(s, H, ["Account.Code", "Account.Name"], "2010-01-01", "%d-01-01" % year):
        k = akey(x)
        out[k] = round(float(x.get("Sum.Incoming") or 0) - float(x.get("Sum.Outgoing") or 0), 2)
    return out


CFKEY = ["CashFlowCategory.HierarchyLevel1", "CashFlowCategory.HierarchyLevel2",
         "CashFlowCategory", "CashFlowCategory.Type", "Account.Name"]


def collect_cf(s, H, mons):
    """Статьи ДДС по месяцам — только по денежным счетам это станет ДДС,
    но режем уже на странице: здесь важно отдать всё как есть."""
    rows = {}
    for mk in mons:
        a, b = month_bounds(mk)
        for x in olap(s, H, CFKEY, a, b):
            k = "|".join(str(x.get(f) or "").strip() for f in CFKEY)
            r = rows.get(k)
            if not r:
                r = rows[k] = {"l1": str(x.get(CFKEY[0]) or "").strip(),
                               "l2": str(x.get(CFKEY[1]) or "").strip(),
                               "cat": str(x.get("CashFlowCategory") or "").strip(),
                               "ct": x.get("CashFlowCategory.Type") or "",
                               "acc": str(x.get("Account.Name") or "").strip(), "m": {}}
            i = round(float(x.get("Sum.Incoming") or 0), 2)
            o = round(float(x.get("Sum.Outgoing") or 0), 2)
            if i or o:
                p = r["m"].get(mk) or [0, 0]
                r["m"][mk] = [round(p[0] + i, 2), round(p[1] + o, 2)]
        log("  статьи ДДС", mk, "— строк", len(rows))
    return list(rows.values())


def collect_tt(s, H, mons):
    rows = {}
    for mk in mons:
        a, b = month_bounds(mk)
        for x in olap(s, H, ["TransactionType"], a, b):
            k = str(x.get("TransactionType") or "")
            r = rows.setdefault(k, {"t": k, "m": {}})
            i = round(float(x.get("Sum.Incoming") or 0), 2)
            o = round(float(x.get("Sum.Outgoing") or 0), 2)
            if i or o:
                p = r["m"].get(mk) or [0, 0]
                r["m"][mk] = [round(p[0] + i, 2), round(p[1] + o, 2)]
    return list(rows.values())


# ──────────────────────────────────────────────────────────────────────────
# 3. СРАВНЕНИЕ С ПРОШЛЫМ СНИМКОМ — ЛОВИМ ПРАВКИ ЗАДНИМ ЧИСЛОМ
# ──────────────────────────────────────────────────────────────────────────
def diff_snapshots(prev, cur, meta, closed_mons):
    """Любое изменение оборота закрытого месяца — правка задним числом."""
    found, stamp = [], datetime.datetime.now().isoformat(timespec="seconds")
    keys = set(prev) | set(cur)
    for k in sorted(keys):
        pm, cm = prev.get(k) or {}, cur.get(k) or {}
        for mk in closed_mons:
            p = pm.get(mk) or [0, 0]
            c = cm.get(mk) or [0, 0]
            di, do = round(c[0] - p[0], 2), round(c[1] - p[1], 2)
            if abs(di) < 0.5 and abs(do) < 0.5:
                continue
            nm = (meta.get(k) or {}).get("name") or k.split("|", 1)[-1]
            found.append({"when": stamp, "acc": nm, "code": (meta.get(k) or {}).get("code", ""),
                          "m": mk, "was": p, "now": c, "di": di, "do": do})
    return found


# ──────────────────────────────────────────────────────────────────────────
def main():
    s, tok, H = auth()
    log("айко: авторизовались")

    closed_env = os.environ.get("AIKA_CLOSED") or ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", closed_env):
        closed = datetime.date.fromisoformat(closed_env)
    else:
        closed = datetime.date(TODAY.year, TODAY.month, 1) - datetime.timedelta(days=1)
    log("закрытый период: по", closed.isoformat())

    # — журнал —
    emp = employees(s, tok)
    new_ev, rev = pull_events(s, tok, emp)
    store = load(EV_F, {"ev": [], "rev": None})
    have = {e.get("id") for e in store.get("ev", [])}
    added = [e for e in new_ev if e.get("id") and e["id"] not in have]
    store["ev"] = (store.get("ev", []) + added)
    store["ev"].sort(key=lambda e: e.get("d") or "")
    store["rev"] = rev
    store["last"] = datetime.datetime.now().isoformat(timespec="seconds")
    save(EV_F, store)
    log("журнал: пришло %d, новых %d, всего в копилке %d" % (len(new_ev), len(added), len(store["ev"])))

    # — обороты —
    mons = months_of(YEAR, TODAY)
    meta, mv = collect_accounts(s, H, mons)
    opn = collect_open(s, H, YEAR)
    cf = collect_cf(s, H, mons)
    tt = collect_tt(s, H, mons)
    log("счетов: %d, строк ДДС: %d, типов операций: %d" % (len(meta), len(cf), len(tt)))

    closed_mons = [m for m in mons if month_bounds(m)[1] <= (closed + datetime.timedelta(days=1)).isoformat()]
    prev = load(SNAP_F, {})
    fixes = load(FIX_F, [])
    new_fix = diff_snapshots(prev, mv, meta, closed_mons) if prev else []
    if new_fix:
        fixes = fixes + new_fix
        log("ПРАВКИ ЗАКРЫТОГО ПЕРИОДА: %d" % len(new_fix))
        for f in new_fix[:20]:
            log("   %s · %s · Дт %+.0f Кт %+.0f" % (f["m"], f["acc"], f["di"], f["do"]))
    save(FIX_F, fixes)
    save(SNAP_F, mv)

    accounts = []
    for k, m in meta.items():
        r = dict(m)
        r["open"] = opn.get(k, 0)
        r["m"] = mv.get(k, {})
        accounts.append(r)
    accounts.sort(key=lambda r: -(sum(abs(v[0]) + abs(v[1]) for v in r["m"].values())))

    ev = store["ev"][-4000:]
    data = {
        "updated": datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        "today": TODAY.isoformat(), "year": YEAR,
        "closed": closed.isoformat(), "months": mons, "closedMonths": closed_mons,
        "accounts": accounts, "cf": cf, "tt": tt,
        "fixes": fixes[-2000:], "events": ev,
        "evTotal": len(store["ev"]),
        "evFrom": (store["ev"][0]["d"][:10] if store["ev"] else ""),
        "docru": DOCRU,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("window.AIKA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
    log("записан", OUT, os.path.getsize(OUT), "байт")

    # Публиковать сайт каждые три часа незачем: страница всё равно смотрит
    # на цифры закрытого периода. Выкладываем утром и сразу же — если нашлась
    # правка задним числом: такое должно быть видно в тот же час.
    try:
        hour = almaty.now().hour
    except Exception:
        hour = datetime.datetime.now().hour
    publish = bool(new_fix) or hour in (6, 7)
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a", encoding="utf-8") as f:
            f.write("skipci=%s\n" % ("" if publish else " [skip ci]"))
            f.write("nfix=%d\n" % len(new_fix))
            f.write("nev=%d\n" % len(added))


if __name__ == "__main__":
    main()
