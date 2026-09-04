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
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import almaty  # время завода — Алматы (UTC+5), не UTC раннера

URL = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS = "1234"
YEAR = 2026
REVENUE_TYPE_CODE = "OUTGOING_INVOICE_REVENUE"
REVENUE_TYPE_RU = "Выручка расходной накладной"
RETURN_TYPE_CODE = "INCOMING_RETURNED_INVOICE_REVENUE"   # возврат от покупателя — вычитаем из выручки
# С июля 2026 часть возвратов проводится не обратной реализацией, а актом
# приёма услуг: документ «Акты приёма услуг» с пометкой «Возврат товара» и
# счётом «Торговая выручка». В номенклатуре такие возвраты не расписаны —
# только контрагент и сумма, — но выручку они уменьшают так же. Без них
# август показывал 20 тысяч возвратов вместо пяти с половиной миллионов.
SERVICE_RETURN_TYPE = "INCOMING_SERVICE"
SERVICE_RETURN_ACCOUNT = "Торговая выручка"

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


def pull_service_returns(s, H, d_from, d_to_exclusive):
    """Возвраты, проведённые актом приёма услуг: контрагент и сумма за период.

    Отбираем по счёту «Торговая выручка» — именно на него ложится возврат
    товара, оформленный услугой. Номенклатуры в таком документе нет, поэтому
    разложить возврат по товарам нельзя: только по контрагентам и месяцам."""
    body = {
        "reportType": "TRANSACTIONS",
        "buildSummary": "true",
        "groupByRowFields": ["Counteragent.Name", "Account.Name"],
        "aggregateFields": ["Sum.Incoming"],
        "filters": {
            "DateTime.DateTyped": {"filterType": "DateRange", "periodType": "CUSTOM",
                                   "from": d_from.isoformat(), "to": d_to_exclusive.isoformat(),
                                   "includeLow": True, "includeHigh": True},
            "TransactionType": {"filterType": "IncludeValues", "values": [SERVICE_RETURN_TYPE]},
        },
    }
    r = s.post(f"{URL}/resto/api/v2/reports/olap", headers=H, data=json.dumps(body),
               verify=False, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"OLAP {r.status_code}: {r.text[:300]}")
    out = []
    for x in r.json().get("data", []):
        if str(x.get("Account.Name") or "").strip() != SERVICE_RETURN_ACCOUNT:
            continue
        v = x.get("Sum.Incoming") or 0
        if v > 0.5:
            out.append({"Counteragent.Name": str(x.get("Counteragent.Name") or "—"),
                        "Sum.Incoming": v})
    return out


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
    today = almaty.today()
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
    returns_by_m = {}          # сумма возвратов покупателей по месяцам (для дашборда)
    from collections import defaultdict
    c_tot = defaultdict(lambda: [0.0, 0.0]); p_tot = defaultdict(lambda: [0.0, 0.0])   # [возврат, продажи] всего
    c_mon = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))                        # [name][mo]=[возврат, продажи]
    p_mon = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    p_qty = defaultdict(float)
    svc_by_m = {}                      # возвраты актами услуг по месяцам
    svc_ctr = defaultdict(float)       # и по контрагентам
    svc_ctr_mon = defaultdict(lambda: defaultdict(float))
    for m in range(1, 13):
        d1 = date(YEAR, m, 1)
        if d1 > last_full:
            break
        eom = date(YEAR, m, calendar.monthrange(YEAR, m)[1])
        d2 = min(eom, last_full)                    # последний включаемый день
        d_end = d2 + timedelta(days=1)
        sales = pull(s, H, d1, d_end, [REVENUE_TYPE_CODE])
        rets  = pull(s, H, d1, d_end, [RETURN_TYPE_CODE])   # возвраты от покупателей
        # Второй канал возвратов — акты приёма услуг. В номенклатуре их нет,
        # поэтому в выручку по товарам они не попадают: считаем отдельно.
        try:
            svc = pull_service_returns(s, H, d1, d_end)
        except Exception as e:
            log(f"{m:02d}      возвраты актами услуг не получены: {e}")
            svc = []
        if svc:
            mo_key = f"{YEAR}-{m:02d}"
            ssum = 0.0
            for x in svc:
                v = x["Sum.Incoming"]
                svc_ctr[x["Counteragent.Name"]] += v
                svc_ctr_mon[x["Counteragent.Name"]][mo_key] += v
                ssum += v
            svc_by_m[mo_key] = round(ssum)
            log(f"{m:02d}      возвраты актами услуг: -{ssum:>15,.0f}  ({len(svc)} строк)")
        agg = {}
        for x in sales:
            k = (str(x.get("Counteragent.Name") or ""), str(x.get("Product.Name") or ""))
            a = agg.setdefault(k, [0.0, 0.0]); a[0] += x.get("Amount") or 0; a[1] += x.get("Sum.Incoming") or 0
            _inc = x.get("Sum.Incoming") or 0
            c_tot[k[0]][1] += _inc; p_tot[k[1]][1] += _inc
            c_mon[k[0]][f"{YEAR}-{m:02d}"][1] += _inc; p_mon[k[1]][f"{YEAR}-{m:02d}"][1] += _inc
        ret_sum = 0.0
        for x in rets:
            k = (str(x.get("Counteragent.Name") or ""), str(x.get("Product.Name") or ""))
            a = agg.setdefault(k, [0.0, 0.0]); a[0] -= x.get("Amount") or 0; a[1] -= x.get("Sum.Incoming") or 0
            ret_sum += x.get("Sum.Incoming") or 0
            _inc = x.get("Sum.Incoming") or 0
            c_tot[k[0]][0] += _inc; p_tot[k[1]][0] += _inc
            c_mon[k[0]][f"{YEAR}-{m:02d}"][0] += _inc; p_mon[k[1]][f"{YEAR}-{m:02d}"][0] += _inc
            p_qty[k[1]] += abs(x.get("Amount") or 0)
        rows = [{"Counteragent.Name": k[0], "Product.Name": k[1], "Amount": v[0], "Sum.Incoming": v[1]}
                for k, v in agg.items() if abs(v[1]) > 0.5 or abs(v[0]) > 0.5]
        if not rows:
            log(f"{m:02d}      нет данных")
            continue
        total = sum((x.get("Sum.Incoming") or 0) for x in rows)
        returns_by_m[f"{YEAR}-{m:02d}"] = round(ret_sum)   # нетто-выручка = total; gross = total + ret_sum
        if ret_sum: log(f"{m:02d}      возвраты вычтены: -{ret_sum:>15,.0f}")
        grand += total
        name = f"I Отчет ПРОДАЖИ {m:02d}.{YEAR}.xlsx"
        write_xlsx(os.path.join(HERE, name), d1, d2, rows)
        log(f"{m:02d}      {d1:%d.%m}–{d2:%d.%m}{'':>13} {len(rows):>7} {total:>18,.0f}")
    log("-" * 60)
    log(f"{'ИТОГО':7} {'':24} {'':>7} {grand:>18,.0f}")

    # отметка об обновлении для страницы продаж
    meta = {"pulled": almaty.now().strftime("%d.%m.%Y %H:%M"),
            "through": last_full.strftime("%d.%m.%Y"),
            "source": "iiko",
            "report": "выручка расходных накладных за вычетом возвратов",
            "returns": returns_by_m}
    with open(os.path.join(HERE, "sales_meta.js"), "w", encoding="utf-8") as f:
        f.write("window.SALES_META=" + json.dumps(meta, ensure_ascii=False) + ";\n")

    # детализация возвратов (для раздела «Аналитика возвратов»): полный список + помесячно
    def build_entities(tot_d, mon_d, qty_d=None):
        rows = []
        for name, (ret, gross) in tot_d.items():
            if ret <= 0.5:
                continue
            mm = {}
            for mo, (r, g) in mon_d.get(name, {}).items():
                if r > 0.5:
                    mm[mo] = [round(r), round(g)]
            row = {"n": (name or "—"), "r": round(ret), "g": round(gross),
                   "s": round(ret / gross * 100, 1) if gross > 0 else None, "m": mm}
            if qty_d is not None:
                row["q"] = round(qty_d.get(name, 0.0))
            rows.append(row)
        rows.sort(key=lambda z: z["r"], reverse=True)
        return rows
    # Возвраты актами услуг: отдельный блок. Из выручки по товарам они НЕ
    # вычтены — в документе нет номенклатуры, разложить по SKU нечем. Поэтому
    # держим их отдельно и честно подписываем на странице.
    svc_rows = sorted(
        ({"n": nm, "r": round(v),
          "m": {k: round(x) for k, x in svc_ctr_mon.get(nm, {}).items() if x > 0.5}}
         for nm, v in svc_ctr.items() if v > 0.5),
        key=lambda z: -z["r"])
    all_by_m = {}
    for k in set(list(returns_by_m.keys()) + list(svc_by_m.keys())):
        all_by_m[k] = round(returns_by_m.get(k, 0) + svc_by_m.get(k, 0))

    detail = {"by_month": returns_by_m,
              "months": sorted(k for k, v in returns_by_m.items() if v),
              "contractors": build_entities(c_tot, c_mon),
              "products": build_entities(p_tot, p_mon, p_qty),
              "total": round(sum(returns_by_m.values())),
              "svc_by_month": svc_by_m,
              "svc_contractors": svc_rows,
              "svc_total": round(sum(svc_by_m.values())),
              "svc_account": SERVICE_RETURN_ACCOUNT,
              "all_by_month": all_by_m,
              "all_total": round(sum(all_by_m.values())),
              "_pulled": meta["pulled"], "_through": meta["through"]}
    with open(os.path.join(HERE, "returns_meta.js"), "w", encoding="utf-8") as f:
        f.write("window.RETURNS_DETAIL=" + json.dumps(detail, ensure_ascii=False) + ";\n")
    log(f"returns_meta.js: контрагентов {len(detail['contractors'])}, товаров {len(detail['products'])}")
    if detail["svc_total"]:
        log(f"  возвраты актами услуг: {detail['svc_total']:,.0f} ₸ за "
            f"{len(svc_by_m)} мес., контрагентов {len(svc_rows)}")
        log(f"  всего возвратов с обоими каналами: {detail['all_total']:,.0f} ₸")

    log(f"\nотметка обновления: {meta['pulled']}, данные по {meta['through']}")
    log("\nГотово. Дальше: rebuild_sales.py и gen_contractor_items.py")
    LOG.close()


if __name__ == "__main__":
    main()
