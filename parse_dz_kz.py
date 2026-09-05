# -*- coding: utf-8 -*-
"""
parse_dz_kz.py — парсинг ДЗ и КЗ из публичного Google Sheets.
"""
import sys, csv, io, json, re, requests
from datetime import datetime
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import almaty  # время завода — Алматы (UTC+5), не UTC раннера

SHEET_ID = "13iFd16Hah1Yi5y2QptmyUrw51rSFfAmtnzhf0U2g_wc"
KZ_GID   = "2005257911"
DZ_GID   = "597090672"
OUTPUT_JS = "dz_kz.js"

def fetch_csv(gid):
    url = (f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
           f"/export?format=csv&gid={gid}")
    r = requests.get(url, timeout=30)
    if r.status_code in (401, 403):
        print(f"\n  [ОШИБКА] Нет доступа ({r.status_code}).")
        print("  Откройте таблицу -> Настройки Доступа ->")
        print("  'Все, у кого есть ссылка - Читатель'\n")
        return None
    r.raise_for_status()
    try:
        text = r.content.decode('utf-8-sig')
    except Exception:
        text = r.content.decode('cp1251', errors='replace')
    return list(csv.reader(io.StringIO(text)))

def num(v):
    if not v: return None
    v = str(v).replace(" ", "").replace("\xa0", "").replace(",", ".").strip()
    try: return float(v)
    except: return None

def fmt_date(s):
    s = str(s).strip().rstrip(".")
    parts = s.split(".")
    if len(parts) == 3:
        d, m, y = parts
        if len(y.strip()) == 2: y = "20" + y.strip()
        return f"{d.zfill(2)}.{m.zfill(2)}.{y}"
    return s

def is_company(name):
    if not name or not name.strip() or len(name.strip()) < 3: return False
    nm = name.strip()
    nl = nm.lower()
    skip = ["итого","всего","поставщик","кредит","ставят","стоп",
            "нам должны","мы должны","дебитор","статус","---",
            "prefix","префикс","период"]
    if any(kw in nl for kw in skip): return False
    # служебные/мусорные строки: голые коды и числа ("100","102",...) — не контрагент
    if re.fullmatch(r"[\d\s.,:\-]+", nm): return False
    return True

def find_header_row(rows, pattern, max_scan=15):
    rx = re.compile(pattern, re.I | re.UNICODE)
    for i, row in enumerate(rows[:max_scan]):
        if any(rx.search(str(c)) for c in row):
            return i, row
    return None, None

def debug_rows(rows, n=6):
    for i, row in enumerate(rows[:n]):
        nonempty = [(j, repr(c[:50])) for j, c in enumerate(row) if c.strip()][:6]
        print(f"    row[{i}]: {nonempty}")

def parse_kz(rows):
    print("  Диагностика КЗ (первые 6 строк):")
    debug_rows(rows)

    hi, header = find_header_row(rows, r"задолженность\s+на")
    if header is None:
        hi, header = find_header_row(rows, r"задолж")
    if header is None:
        hi, header = find_header_row(rows, r"кз\s+на\s+\d")
    if header is None:
        print("  [!] КЗ: не найдена строка-заголовок")
        return None

    print(f"  КЗ: заголовок найден в строке {hi}")
    data_rows = rows[hi+1:]

    itogo_row = None
    for row in data_rows:
        if row and str(row[0]).strip().upper() == 'ИТОГО':
            itogo_row = row
            break

    debt_cols = []
    for i, cell in enumerate(header):
        c = str(cell).strip()
        m_date = None
        if re.search(r"задолженность\s+на\s+\d", c, re.I | re.UNICODE):
            m_date = re.search(r"(\d{1,2}\.\d{2}\.\d{2,4})", c)
        elif re.search(r"кз\s+на\s+\d", c, re.I | re.UNICODE):
            m_date = re.search(r"(\d{1,2}\.\d{2}\.\d{2,4})", c)
        if m_date:
            lbl = fmt_date(m_date.group(1))
            debt_cols.append((i, lbl))

    if not debt_cols:
        print(f"  [!] КЗ: нет датированных колонок в строке {hi}")
        return None

    def date_key(item):
        parts = item[1].split(".")
        if len(parts) == 3:
            d, m2, y = parts
            if len(y) == 2: y = "20" + y
            try: return (int(y), int(m2), int(d))
            except: pass
        return (0, 0, 0)
    debt_cols.sort(key=date_key)
    print(f"  КЗ: {len(debt_cols)} датированных колонок, последняя: {debt_cols[-1][1]}")

    def itogo_total(col_i):
        if itogo_row and col_i < len(itogo_row):
            v = num(itogo_row[col_i])
            if v is not None and abs(v) > 1_000_000:
                return abs(v)
        return None

    dyn_candidates = []
    for col_i, lbl in debt_cols:
        t = itogo_total(col_i)
        if t and t > 50_000_000:
            dyn_candidates.append((col_i, lbl, t))

    dyn_cols = dyn_candidates[-8:]
    dynamics = [{"date": lbl, "total": round(t)} for _, lbl, t in dyn_cols]

    latest_total = 0.0
    last_date = debt_cols[-1][1]
    last_col_i = debt_cols[-1][0]
    if dyn_cols:
        last_col_i, last_date, latest_total = dyn_cols[-1]
    else:
        for row in data_rows:
            if not is_company(row[0] if row else ""): continue
            v = num(row[last_col_i]) if last_col_i < len(row) else None
            if v and v > 0: latest_total += v

    print(f"  КЗ итого (|ИТОГО|): {latest_total:,.0f}  ({last_date})")

    kz_cols_only = [(i, lbl) for i, lbl in debt_cols
                    if re.search(r"кз\s+на", header[i], re.I | re.UNICODE)]
    top_col_i = kz_cols_only[-1][0] if kz_cols_only else last_col_i

    # КЗ (кредиторка): в столбце "КЗ на ..." ОТРИЦАТЕЛЬНЫЕ значения — это наши
    # долги поставщикам. Положительные — выданные авансы/переплаты (это НЕ КЗ).
    # Топ кредиторов строим по крупнейшим отрицательным остаткам (по модулю).
    top = []
    for row in data_rows:
        name = (row[0] if row else "").strip()
        if not is_company(name): continue
        v = num(row[top_col_i]) if top_col_i < len(row) else None
        if v and v < 0:
            top.append({"name": name, "debt": round(-v)})
    top.sort(key=lambda x: -x["debt"])

    # ── Нестыковки по КЗ: что приняли на склад против того, что оплатили ─────
    # Зеркало такого же разбора по ДЗ. В листе КЗ каждая неделя занимает три
    # колонки: «Приход товара за период», «Оплата за период», «КЗ на дату».
    # Берём последнюю неделю: приход — это новый долг перед поставщиком,
    # оплата — его погашение. Разрыв в плюс означает, что товар взяли,
    # а деньги не отдали.
    # Неделя, которая заканчивается последней датой, занимает колонки между
    # предыдущей датированной колонкой и последней: «Приход товара за период»,
    # «Оплата за период», «КЗ на <дата>». Ищем только в этом промежутке —
    # тогда «ПОЛЕ ОБНОВЛЕНИЯ» с такими же подписями справа от таблицы
    # отсекается само, без догадок про «последний минус один».
    dated_idx = sorted(i for i, _ in debt_cols)
    prev_i = -1
    for i in dated_idx:
        if i < last_col_i:
            prev_i = i
    span = list(range(prev_i + 1, last_col_i))

    def pick(pat):
        for i in span:
            if i < len(header) and re.search(pat, str(header[i]), re.I | re.UNICODE):
                return i
        return None

    in_last  = pick(r"приход\s+товара")
    pay_last = pick(r"оплата\s+за\s+период")

    def kval(row, i):
        v = num(row[i]) if (i is not None and i < len(row)) else None
        return v or 0.0

    kz_ana = []
    for row in data_rows:
        name = (row[0] if row else "").strip()
        if not is_company(name): continue
        got, paid = kval(row, in_last), kval(row, pay_last)
        if got > 0 or paid > 0:
            # в колонке «КЗ на дату» наш долг записан отрицательным числом,
            # аванс поставщику — положительным. На странице удобнее наоборот:
            # debt > 0 — мы должны, debt < 0 — у поставщика лежит наш аванс.
            kz_ana.append({"name": name, "kc": round(got), "kd": round(paid),
                           "debt": round(-kval(row, last_col_i))})

    def two_dates(cell):
        ds = re.findall(r"(\d{1,2}\.\d{2})", str(cell or ""))
        return ds[0] + "–" + ds[1] if len(ds) >= 2 else None

    def kz_period(col_i):
        """Подпись недели («с 29.08.2026 по 04.09.2026») висит объединённой
        ячейкой над тройкой колонок, и в выгрузке достаётся её середине —
        колонке «Оплата». Смотреть влево нельзя: там подпись прошлой недели,
        из-за чего страница месяц показывала бы чужой период."""
        if col_i is None: return ""
        # в старых неделях период иногда вписан прямо в заголовок колонки
        own = two_dates(header[col_i]) if col_i < len(header) else None
        if own: return own
        if hi < 1: return ""
        up = rows[hi - 1] if hi - 1 < len(rows) else []
        for j in (col_i + 1, col_i, col_i + 2):
            if 0 <= j < len(up):
                d = two_dates(up[j])
                if d: return d
        return ""

    return {"total": round(latest_total), "date": last_date,
            "dynamics": dynamics, "top": top[:30],
            "ana": kz_ana,
            "anaMeta": {"period": kz_period(in_last),
                        "totalIn":  round(sum(a["kc"] for a in kz_ana)),
                        "totalPay": round(sum(a["kd"] for a in kz_ana))}}

# ── Контрагенты, снятые с учёта как безнадёжно просроченные ──────────────
# Решение финдиректора от 05.09.2026. По каждому из них остаток не менялся
# ни на тенге в течение месяцев: ни отгрузок, ни оплат. Держать их в общей
# сумме «нам должны» — обманывать себя: это не оборотная дебиторка,
# а замороженные деньги, по которым нужен резерв и взыскание.
#   84-ТОО ГАМАУС      1 887 068 ₸ — не двигается с 01.03.2026
#   89-ИП ЦОЙ Д.Л.     2 260 140 ₸ — не двигается с 21.12.2025
#   95-ТОО ФУД ПИКАССО 9 987 253 ₸ — не двигается с 01.02.2026
# Сопоставляем по коду в начале названия: имена в таблице пишут по-разному,
# а код стабилен. Исключаем ВО ВСЕХ периодах, иначе на графике возник бы
# фальшивый обвал ДЗ в день, когда их сняли.
EXCLUDED_DZ_CODES = ("84", "89", "95")


def dz_code(name):
    """Код контрагента из начала строки: «95-ТОО ФУД ПИКАССО» -> «95»."""
    m = re.match(r"\s*(\d{1,4})\s*[-–—.]", str(name or ""))
    return m.group(1) if m else None


def is_excluded_dz(name):
    return dz_code(name) in EXCLUDED_DZ_CODES


def parse_dz(rows):
    print("  Диагностика ДЗ (первые 5 строк):")
    debug_rows(rows, 5)

    hi, header = find_header_row(rows, r"дз\s+на|д/з\s+на|д\.з\.\s+на")
    if header is None:
        hi, header = find_header_row(rows, r"дз|д/з")
    if header is None:
        print("  [!] ДЗ: не найдена строка-заголовок")
        return None

    print(f"  ДЗ: заголовок найден в строке {hi}")
    dz_cols = []
    for i, cell in enumerate(header):
        c = str(cell).strip()
        if re.search(r"дз\s+на|д/з\s+на|д\.з\.\s*на", c, re.I | re.UNICODE):
            m = re.search(r"(\d{1,2}\.\d{2}\.\d{2,4})", c)
            lbl = fmt_date(m.group(1)) if m else c[:20]
            dz_cols.append((i, lbl))

    if not dz_cols:
        print(f"  [!] ДЗ: нет колонок 'ДЗ на' в строке {hi}")
        print(f"  Ячейки:", [c[:30] for c in header if c.strip()][:10])
        return None

    print(f"  ДЗ: {len(dz_cols)} колонок, последняя: {dz_cols[-1][1]}")
    data_rows = rows[hi+1:]

    # Итог ДЗ берём из строки ИТОГО (как в КЗ), а НЕ суммой всех строк —
    # иначе служебные строки (prefix, ПЕРИОД, голые коды 100-111) раздувают
    # сумму (был баг: ДЗ = 414 трлн). Строка ИТОГО = СУММ(KN4:KN43) без мусора.
    itogo_row = None
    for row in data_rows:
        if row and str(row[0]).strip().upper() == 'ИТОГО':
            itogo_row = row
            break
    if itogo_row is None:
        print("  [!] ДЗ: строка ИТОГО не найдена — падаю на сумму по контрагентам")

    def itogo_total(col_i):
        if itogo_row and col_i < len(itogo_row):
            v = num(itogo_row[col_i])
            if v is not None and abs(v) > 1_000_000:
                return abs(v)
        return None

    def sum_companies(col_i):
        s = 0.0
        for row in data_rows:
            if not is_company(row[0] if row else ""): continue
            if is_excluded_dz(row[0]): continue
            v = num(row[col_i]) if col_i < len(row) else None
            if v and v > 0: s += v
        return s

    def excluded_in(col_i):
        """Сколько в этой колонке приходится на снятых контрагентов."""
        s = 0.0
        for row in data_rows:
            if not is_company(row[0] if row else ""): continue
            if not is_excluded_dz(row[0]): continue
            v = num(row[col_i]) if col_i < len(row) else None
            if v and v > 0: s += v
        return s

    # динамика: по строке ИТОГО каждой датированной колонки ДЗ
    dyn_cols = dz_cols[-8:]
    dynamics = []
    for col_i, lbl in dyn_cols:
        t = itogo_total(col_i)
        if t is None:
            t = sum_companies(col_i)          # уже без снятых
        else:
            t -= excluded_in(col_i)           # строка ИТОГО их содержит — вычитаем
        if t and t > 0:
            dynamics.append({"date": lbl, "total": round(t)})

    last_col_i, last_date = dz_cols[-1]
    # общий итог ДЗ = строка ИТОГО последней колонки за вычетом снятых
    latest_total = itogo_total(last_col_i)
    excluded_total = excluded_in(last_col_i)
    if latest_total is not None:
        latest_total -= excluded_total

    # топ дебиторов — реальные контрагенты (служебные строки отсеяны в is_company)
    top, excluded = [], []
    for row in data_rows:
        name = (row[0] if row else "").strip()
        if not is_company(name): continue
        v = num(row[last_col_i]) if last_col_i < len(row) else None
        if v and v > 0:
            if is_excluded_dz(name):
                excluded.append({"name": name, "debt": round(v)})
            else:
                top.append({"name": name, "debt": round(v)})
    top.sort(key=lambda x: -x["debt"])
    excluded.sort(key=lambda x: -x["debt"])
    if latest_total is None:
        latest_total = sum(x["debt"] for x in top)

    # ── Аналитика по контрагентам: отгрузка/оплата/ДЗ (для «Нестыковки» и «Консигнация») ──
    def find_cols(pat):
        cs = []
        for i, cell in enumerate(header):
            c = str(cell)
            if re.search(pat, c, re.I | re.UNICODE) and re.search(r"\d{1,2}\.\d{2}", c):
                cs.append(i)
        return cs
    ship_cols = find_cols(r"отгрузк")
    pay_cols  = find_cols(r"поступлен")
    ship_last = ship_cols[-1] if ship_cols else None
    ship_prev = ship_cols[-2] if len(ship_cols) >= 2 else None
    pay_last  = pay_cols[-1] if pay_cols else None

    def val(row, i):
        v = num(row[i]) if (i is not None and i < len(row)) else None
        return v or 0.0

    consign, ana = [], []
    for row in data_rows:
        name = (row[0] if row else "").strip()
        if not is_company(name): continue
        if is_excluded_dz(name): continue      # сняты с учёта — не мешаем их в аналитику
        ship, shipPrev = val(row, ship_last), val(row, ship_prev)
        pay,  dzv      = val(row, pay_last),  val(row, last_col_i)
        if ship > 0 or pay > 0:
            ana.append({"name": name, "kc": round(ship), "kd": round(pay)})
        if dzv > 0:
            consign.append({"name": name, "ship": round(ship), "shipPrev": round(shipPrev),
                            "pay": round(pay), "dz": round(dzv)})

    def period_label(col_i):
        if col_i is None: return ""
        ds = re.findall(r"(\d{1,2}\.\d{2})", str(header[col_i]))
        return (ds[0] + "–" + ds[1]) if len(ds) >= 2 else (ds[0] if ds else "")

    prev_dz_lbl = dz_cols[-2][1] if len(dz_cols) >= 2 else ""

    return {"total": round(latest_total), "date": last_date,
            "dynamics": dynamics, "top": top[:30],
            # снятые с учёта — отдаём отдельно, страница показывает их примечанием
            "excluded": excluded,
            "excludedTotal": round(excluded_total),
            "excludedNote": "сняты как безнадёжно просроченные: остаток не менялся месяцами, "
                            "ни отгрузок, ни оплат",
            "ana": ana,
            "anaMeta": {"period": period_label(ship_last),
                        "totalShip": round(sum(a["kc"] for a in ana)),
                        "totalPay":  round(sum(a["kd"] for a in ana))},
            "consign": consign,
            "consignMeta": {"date": last_date, "prevDate": prev_dz_lbl}}

def main():
    print("=" * 50)
    print("  parse_dz_kz.py -- DZ/KZ iz Google Sheets")
    print("=" * 50)

    print("\n-> Загружаю лист КЗ...")
    kz_rows = fetch_csv(KZ_GID)
    print("-> Загружаю лист ДЗ...")
    dz_rows = fetch_csv(DZ_GID)

    if not kz_rows or not dz_rows:
        sys.exit(1)

    print(f"\n-> Размер: КЗ={len(kz_rows)} строк, ДЗ={len(dz_rows)} строк")

    print("\n-> Парсю КЗ...")
    kz = parse_kz(kz_rows)
    if kz: print(f"   Итого КЗ: {kz['total']:,.0f} тнг  ({kz['date']})")

    print("\n-> Парсю ДЗ...")
    dz = parse_dz(dz_rows)
    if dz: print(f"   Итого ДЗ: {dz['total']:,.0f} тнг  ({dz['date']})")

    if not kz or not dz:
        print("\n[!] Неполные данные. Проверьте вывод диагностики выше.")
        sys.exit(1)

    result = {
        # datetime.now() на раннере GitHub — это UTC: страница показывала
        # «обновлено 17:53», когда в Алматы было 22:53. Берём время завода.
        "updated": almaty.now().strftime("%d.%m.%Y %H:%M"),
        "kz": kz,
        "dz": dz,
    }

    js = "window.DZ_KZ = " + json.dumps(result, ensure_ascii=False, indent=2) + ";\n"
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write(js)

    net = dz["total"] - kz["total"]
    print(f"\n   Чистая позиция (ДЗ-КЗ): {'+' if net>=0 else ''}{net:,.0f} тнг")
    print(f"\n[OK] Записано в {OUTPUT_JS}\n")

if __name__ == "__main__":
    main()
