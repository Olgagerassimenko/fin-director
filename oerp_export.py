# -*- coding: utf-8 -*-
"""
Пульс · выгрузка из O·ERP по API.

Зачем. С 06.11.2026 расходные накладные заводят только в O·ERP, в айко их нет,
и ноябрь на Пульсе занижен втрое. Айко остаётся источником техкарт, складов и
кассы, а продажи должны идти из O·ERP — напрямую, без ручных снимков.

Доступ. API O·ERP: https://erp-system-fz.kz/api/v1/ — только чтение (POST
отвечает 405 «API только для чтения»), авторизация Bearer-токеном, realm
"erp-api". Токен лежит в секрете репозитория OERP_TOKEN и нигде больше:
ни в коде, ни в журналах, ни в выводе этого скрипта.

Два режима:
  map  — пройтись по возможным веткам API и записать, что отвечает, в
         oerp_api_map.txt. Нужен один раз, чтобы узнать настоящие адреса.
  pull — собственно выгрузка (включается, когда карта известна).
Без аргумента: map, если карты ещё нет, иначе pull.
"""
import os, sys, json, datetime, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = (os.environ.get("OERP_TOKEN") or "").strip()
MAP_FILE = os.path.join(HERE, "oerp_api_map.txt")

HOSTS = {
    "erp": "https://erp-system-fz.kz",
    "zavod": "https://zavod.erp-system-fz.kz",
    "catalog": "https://catalog.erp-system-fz.kz",
}

# Ветки перебираем вслепую: без токена API не отдаёт даже список маршрутов —
# всё, что под /api/v1/, отвечает 401 до разбора адреса.
CANDIDATES = [
    "/api/v1/", "/api/v1/docs", "/api/v1/schema", "/api/v1/openapi.json", "/api/v1/meta",
    "/api/v1/health", "/api/v1/endpoints", "/api/v1/routes",
    "/api/v1/documents", "/api/v1/document", "/api/v1/invoices", "/api/v1/expense-invoices",
    "/api/v1/expense_invoices", "/api/v1/sales", "/api/v1/sale", "/api/v1/orders",
    "/api/v1/returns", "/api/v1/receipts", "/api/v1/writeoffs", "/api/v1/productions",
    "/api/v1/transfers", "/api/v1/inventories",
    "/api/v1/counterparties", "/api/v1/counterparty", "/api/v1/partners", "/api/v1/clients",
    "/api/v1/products", "/api/v1/items", "/api/v1/nomenclature", "/api/v1/categories",
    "/api/v1/stores", "/api/v1/warehouses", "/api/v1/stocks", "/api/v1/balances",
    "/api/v1/payments", "/api/v1/customer-payments", "/api/v1/supplier-payments",
    "/api/v1/gl", "/api/v1/gl-entries", "/api/v1/entries", "/api/v1/accounts",
    "/api/v1/reports", "/api/v1/reports/sales", "/api/v1/export",
    "/api/v1/price-lists", "/api/v1/pricelists", "/api/v1/prices",
]

def get(url, params=None, timeout=30):
    if params:
        import urllib.parse
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + TOKEN,
        "Accept": "application/json",
        "User-Agent": "pulse-oerp/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read(600)
    except Exception as e:
        return None, (type(e).__name__ + ": " + str(e)[:120]).encode()

def shape(raw):
    """Короткое описание ответа: ключи объекта или поля первой записи списка."""
    try:
        o = json.loads(raw.decode("utf-8"))
    except Exception:
        return "не JSON: " + raw[:80].decode("utf-8", "replace").replace("\n", " ")
    if isinstance(o, list):
        head = o[0] if o else None
        keys = ", ".join(list(head.keys())[:14]) if isinstance(head, dict) else type(head).__name__
        return f"список, записей {len(o)}; поля: {keys}"
    if isinstance(o, dict):
        ks = list(o.keys())
        extra = ""
        for k in ("results", "items", "data", "rows"):
            v = o.get(k)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                extra = f"; {k}[0]: " + ", ".join(list(v[0].keys())[:14])
                break
        return "объект; ключи: " + ", ".join(ks[:14]) + extra
    return type(o).__name__

def do_map():
    lines = ["карта API O·ERP, " + datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
             "токен: " + ("есть" if TOKEN else "НЕТ"), ""]
    found = 0
    for name, host in HOSTS.items():
        lines.append(f"=== {name} · {host}")
        for p in CANDIDATES:
            code, raw = get(host + p)
            if code == 404:
                continue          # ветки нет — молчим, иначе карта не читается
            mark = "  " if code != 200 else "✓ "
            lines.append(f"{mark}{str(code):>4} {p:32} {shape(raw) if code == 200 else raw[:90].decode('utf-8','replace')}")
            if code == 200:
                found += 1
        lines.append("")
    lines.append(f"рабочих веток: {found}")
    open(MAP_FILE, "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines)[:6000])
    return found

def do_pull():
    print("Карта API есть, но выгрузка ещё не настроена под её адреса.")
    print("Открой oerp_api_map.txt — по нему допишется разбор продаж, ДЗ/КЗ и остатков.")
    return 0

if __name__ == "__main__":
    if not TOKEN:
        print("Секрета OERP_TOKEN нет — выгрузка пропущена, это не ошибка.")
        print("Добавить: GitHub → репозиторий → Settings → Secrets and variables → Actions → New repository secret, имя OERP_TOKEN.")
        sys.exit(0)
    mode = sys.argv[1] if len(sys.argv) > 1 else ("map" if not os.path.exists(MAP_FILE) else "pull")
    sys.exit(0 if (do_map() if mode == "map" else do_pull()) >= 0 else 1)
