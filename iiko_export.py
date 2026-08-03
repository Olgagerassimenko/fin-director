# -*- coding: utf-8 -*-
"""
Выгрузка «I Отчет ПРОДАЖИ» напрямую из айко — замена ручного экспорта в Excel.

Что делает:
  1. Ходит в OLAP-отчёт по проводкам (TRANSACTIONS), тип «Выручка расходной
     накладной» (OUTGOING_INVOICE_REVENUE) — это ровно то, что вы выгружали руками.
  2. Складывает результат в файлы «I Отчет ПРОДАЖИ MM.2026.xlsx» в том же формате,
     что отдаёт бэк-офис, поэтому rebuild_sales.py и gen_contractor_items.py
     работают без изменений.
  3. Старые ручные выгрузки убирает в папку «архив выгрузок», чтобы сборщик
     не выбирал устаревший файл.

Важно про границу периода: айко считает верхнюю дату исключительно, поэтому
конец периода задаём следующим днём. Проверено на 2026 году — январь, март,
апрель и май сходятся с ручной выгрузкой до тенге.

Текущий месяц берём по последний ПОЛНЫЙ день (вчера): незакрытый день
занижал бы темп продаж.
"""
import sys, os, json, glob, shutil, hashlib, calendar, warnings
from datetime import date, timedelta
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
import requests
from openpyxl import Workbook

URL = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS = "1234"
YEAR = 2026
REVENUE_TYPE_CODE = "OUTGOING_INVOICE_REVENUE"
REVENUE_TYPE_RU = "Выручка расходной накладной"
RETURN_TYPE_CODE = "INCOMING_RETURNED_INVOICE_REVENUE"   # возврат от покупателя — вычитаем из выручки

HERE = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(HERE, "архив выгрузок")
LOG = open(os.path.join(HERE, "iiko_export_log.txt"), "w", encoding="utf-8")


def log(*a):
    t = " ".join(str(x) for x in a)
    print(t)
    LOG.write(t + "\n")
    LOG.flush()


def auth():
    s = requests.Session()
    r = s.get(f"{URL}/resto/api/auth",
              params={"login": LOGIN, "pass": hashlib.sha1(PASS.encode()).hexdigest()},
              verify=False, timeout=60)
    r.raise_for_status()
    return s, {"Cookie": f"key={r.text.strip().strip(chr(34))}",
               "Content-Type": "application/json"}


def pull(s, H, d_from, d_to_exclusive, txn_types=None):
    """Строки (контрагент, товар, кол-во, сумма) за период [d_from, d_to_exclusive)."""
    if txn_types is None: txn_types = [REVENUE_TYPE_CODE]
    body = {
        "reportType": "TRANSACTIONS",
        "buildSummary": "true",
        "groupByRowFields": ["Counteragent.Name", "Product.Name"],
        "aggregateFields": ["Amount", "Sum.Incoming"],
        "filters": {
            "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                   "from": d_from.isoformat(), "to": d_to_exclusive.isoformat(),
                                   "includeLow": True, "includeHigh": True},
            "TransactionType": {"filterType": "IncludeValues", "values": txn_types},
        },
    }
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers=H, data=json.dumps(body),
               verify=False, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"OLAP {r.status_code}: {r.text[:300]}")
    return r.json().get("data", [])


def write_xlsx(path, d1, d2, rows):
    """Формат бэк-офиса: шапка 5 строк, дальше контрагент / товар / тип / кол-во / сумма."""
    wb = Workbook()
    ws = wb.active
    ws.title = "I Отчет  ПРОДАЖИ"
    ws.append(["I Отчет  ПРОДАЖИ"])
    ws.append(["Название ресторана: Фуд завод"])
    ws.append([f"Период: с {d1:%d.%m.%Y} по {d2:%d.%m.%Y}"])
    ws.append(["", "", "", "Итого"])
    ws.append(["Контрагент", "Элемент номенклатуры", "Тип транзакции",
               "Количество", "Сумма прихода, тнг."])
    rows.sort(key=lambda x: (str(x.get("Counteragent.Name") or ""),
                             str(x.get("Product.Name") or "")))
    prev = None
    for x in rows:
        ca = str(x.get("Counteragent.Name") or "").strip()
        pr = str(x.get("Product.Name") or "").strip()
        if not pr:
            continue
        ws.append([ca if ca != prev else "", pr, REVENUE_TYPE_RU,
                   x.get("Amount") or 0, x.get("Sum.Incoming") or 0])
        prev = ca
    wb.save(path)


def main():
    today = date.today()
    last_full = today - timedelta(days=1)          # последний полный день
    s, H = auth()
    log(f"айко: авторизация ok   сегодня {today:%d.%m.%Y}, "
        f"последний полный день {last_full:%d.%m.%Y}\n")

    os.makedirs(ARCH, exist_ok=True)
    moved = 0
    for p in glob.glob(os.path.join(HERE, "I Отчет*ПРОДАЖИ*.xlsx")):
        b = os.path.basename(p)
        if b.startswith("~$"):
            continue
        dst = os.path.join(ARCH, b)
        if os.path.exists(dst):
            os.remove(dst)
        shutil.move(p, dst)
        moved += 1
    if moved:
        log(f"старые выгрузки убраны в «архив выгрузок»: {moved} шт.\n")

    log(f"{'месяц':7} {'период':24} {'строк':>7} {'выручка, ₸':>18}")
    log("-" * 60)
    grand = 0.0
    for m in range(1, 13):
        d1 = date(YEAR, m, 1)
        if d1 > last_full:
            break
        eom = date(YEAR, m, calendar.monthrange(YEAR, m)[1])
        d2 = min(eom, last_full)                    # последний включаемый день
        d_end = d2 + timedelta(days=1)
        sales = pull(s, H, d1, d_end, [REVENUE_TYPE_CODE])
        rets  = pull(s, H, d1, d_end, [RETURN_TYPE_CODE])   # возвраты от покупателей
        agg = {}
        for x in sales:
            k = (str(x.get("Counteragent.Name") or ""), str(x.get("Product.Name") or ""))
            a = agg.setdefault(k, [0.0, 0.0]); a[0] += x.get("Amount") or 0; a[1] += x.get("Sum.Incoming") or 0
        ret_sum = 0.0
        for x in rets:
            k = (str(x.get("Counteragent.Name") or ""), str(x.get("Product.Name") or ""))
            a = agg.setdefault(k, [0.0, 0.0]); a[0] -= x.get("Amount") or 0; a[1] -= x.get("Sum.Incoming") or 0
            ret_sum += x.get("Sum.Incoming") or 0
        rows = [{"Counteragent.Name": k[0], "Product.Name": k[1], "Amount": v[0], "Sum.Incoming": v[1]}
                for k, v in agg.items() if abs(v[1]) > 0.5 or abs(v[0]) > 0.5]
        if not rows:
            log(f"{m:02d}      нет данных")
            continue
        total = sum((x.get("Sum.Incoming") or 0) for x in rows)
        if ret_sum: log(f"{m:02d}      возвраты вычтены: -{ret_sum:>15,.0f}")
        grand += total
        name = f"I Отчет ПРОДАЖИ {m:02d}.{YEAR}.xlsx"
        write_xlsx(os.path.join(HERE, name), d1, d2, rows)
        log(f"{m:02d}      {d1:%d.%m}–{d2:%d.%m}{'':>13} {len(rows):>7} {total:>18,.0f}")
    log("-" * 60)
    log(f"{'ИТОГО':7} {'':24} {'':>7} {grand:>18,.0f}")

    # отметка об обновлении для страницы продаж
    from datetime import datetime
    meta = {"pulled": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "through": last_full.strftime("%d.%m.%Y"),
            "source": "iiko",
            "report": "выручка расходных накладных за вычетом возвратов"}
    with open(os.path.join(HERE, "sales_meta.js"), "w", encoding="utf-8") as f:
        f.write("window.SALES_META=" + json.dumps(meta, ensure_ascii=False) + ";\n")
    log(f"\nотметка обновления: {meta['pulled']}, данные по {meta['through']}")
    log("\nГотово. Дальше: rebuild_sales.py и gen_contractor_items.py")
    LOG.close()


if __name__ == "__main__":
    main()
