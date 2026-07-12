#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Дашборд продаж — локальный сервер.
Тянет данные с iiko API по выбранному месяцу.
Открывайте http://localhost:8090
"""

import requests, hashlib, json, re, os, sys, warnings, webbrowser, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from collections import defaultdict

warnings.filterwarnings("ignore")

IIKO_URL   = "https://fudzavod.iiko.it"
IIKO_LOGIN = "GerassimenkoO"
IIKO_PASS  = "1234"
PORT       = 8090
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
HTML_FILE  = os.path.join(PARENT_DIR, "продажи_live.html")

# ── iiko auth ──────────────────────────────────────
_token = None
_session = None

def get_session():
    global _token, _session
    _session = requests.Session()
    sha1 = hashlib.sha1(IIKO_PASS.encode()).hexdigest()
    r = _session.get(f"{IIKO_URL}/resto/api/auth",
                     params={"login": IIKO_LOGIN, "pass": sha1},
                     verify=False, timeout=30)
    _token = r.text.strip().strip('"')
    print(f"  Auth OK: {_token[:16]}...")
    return _session, _token

def get_cat(name):
    n = str(name).upper()
    if any(x in n for x in ['КИМПАБ','ОНИГИРИ','УДОН','РАМЕН','СУШИ','ГИОЗА','ВОК','ЯПОН']): return 'Япония'
    if 'ЗАВТРАК' in n: return 'Завтраки'
    if any(x in n for x in ['ДЕСЕРТ','ТИРАМИСУ','БРАУНИ','ЧИЗКЕЙК','МЕДОВИК','ТОРТ','ПИРОЖН']): return 'Десерты'
    if 'САЛАТ' in n: return 'Салаты'
    if any(x in n for x in ['СЭНДВИЧ','СЕНДВИЧ','КЛАБ СЭНД','ЧИАБАТТА']): return 'Сэндвичи'
    if any(x in n for x in ['КРУАССАН','БАГЕТ','ПИРОГ','ПИРОЖОК','БУЛОЧКА','ЛАВАШ','ХЛЕБ']): return 'Выпечка'
    if any(x in n for x in ['П/Ф','КОТЛЕТ','ШНИЦЕЛЬ','МАНТЫ','ПЛОВ','ПАСТА','ГУЙРУ','ЛАГМАН','ПЕЛЬМЕН']): return 'Горячее'
    return 'Прочее'

def is_magnum(name):
    return 'MAGNUM' in str(name).upper() or 'МАГНУМ' in str(name).upper()

# ── iiko OLAP query ────────────────────────────────
def fetch_sales(month_key):
    """Запрашивает продажи за месяц YYYY-MM, возвращает список записей."""
    global _session, _token
    if not _session:
        _session, _token = get_session()

    from_dt = f"{month_key}-01"
    # last day of month
    y, m = int(month_key[:4]), int(month_key[5:7])
    import calendar
    last_day = calendar.monthrange(y, m)[1]
    to_dt = f"{month_key}-{last_day:02d}"

    headers = {"Cookie": f"key={_token}", "Content-Type": "application/json"}
    body = {
        "reportType": "SALES",
        "buildSummary": "false",
        "groupByRowFields": ["OpenDate", "DishCategory", "DishName"],
        "groupByColFields": [],
        "aggregateFields": ["DishDiscountSumInt", "DishAmountInt"],
        "filters": {
            "OpenDate.Typed": {
                "filterType": "DateRange", "periodType": "CUSTOM",
                "from": from_dt, "to": to_dt,
                "includeLow": "true", "includeHigh": "true"
            },
            "DeletedWithWriteoff": {
                "filterType": "ExcludeValues",
                "values": ["DELETED_WITHOUT_WRITEOFF"]
            }
        }
    }

    print(f"  Запрос SALES {from_dt}..{to_dt}", flush=True)
    try:
        r = _session.post(f"{IIKO_URL}/resto/api/v2/reports/olap",
                          json=body, headers=headers, verify=False, timeout=120)
    except Exception as e:
        # re-auth once
        _session, _token = get_session()
        headers = {"Cookie": f"key={_token}", "Content-Type": "application/json"}
        r = _session.post(f"{IIKO_URL}/resto/api/v2/reports/olap",
                          json=body, headers=headers, verify=False, timeout=120)

    if not r.ok:
        print(f"  OLAP error {r.status_code}: {r.text[:300]}", flush=True)
        return []

    resp = r.json()
    rows = resp.get('data', resp) if isinstance(resp, dict) else resp
    cols = resp.get('columns', []) if isinstance(resp, dict) else []
    col_names = [c.get('name', c.get('id','')) if isinstance(c,dict) else str(c) for c in cols]

    def ci(variants):
        for v in variants:
            for i, c in enumerate(col_names):
                if v.lower() in c.lower(): return i
        return -1

    i_date = ci(['OpenDate','Date'])
    i_cat  = ci(['DishCategory','Category'])
    i_name = ci(['DishName','Dish','MenuItem'])
    i_rev  = ci(['DishDiscountSumInt','DishSumInt','DishSum'])
    i_qty  = ci(['DishAmountInt','DishAmount'])

    records = []
    for row in (rows if isinstance(rows, list) else []):
        if isinstance(row, dict):
            def gv(i, key): return row.get(col_names[i]) if i>=0 else row.get(key)
            name = gv(i_name, 'DishName') or ''
            cat  = gv(i_cat,  'DishCategory') or ''
            rev  = gv(i_rev,  'DishDiscountSumInt') or 0
            qty  = gv(i_qty,  'DishAmountInt') or 0
        elif isinstance(row, list):
            name = row[i_name] if i_name>=0 and i_name<len(row) else ''
            cat  = row[i_cat]  if i_cat>=0  and i_cat<len(row)  else ''
            rev  = row[i_rev]  if i_rev>=0  and i_rev<len(row)  else 0
            qty  = row[i_qty]  if i_qty>=0  and i_qty<len(row)  else 0
        else:
            continue

        name = str(name).strip()
        if not name or name.lower().startswith('итого'): continue

        cat_str = str(cat).strip() if cat else get_cat(name)
        if not cat_str or cat_str.lower() in ('none','null',''):
            cat_str = get_cat(name)

        try: rev_f = abs(float(rev)) if rev else 0
        except: rev_f = 0
        try: qty_f = abs(float(qty)) if qty else 0
        except: qty_f = 0

        records.append({'name': name, 'cat': cat_str, 'rev': rev_f, 'qty': qty_f, 'magnum': is_magnum(name)})

    print(f"  Записей: {len(records)}", flush=True)
    return records

def aggregate(records):
    """Строит итоговую структуру из записей."""
    # By category
    cat_agg = defaultdict(lambda: {'rev':0,'qty':0,'count':0})
    for r in records:
        cat_agg[r['cat']]['rev']   += r['rev']
        cat_agg[r['cat']]['qty']   += r['qty']
        cat_agg[r['cat']]['count'] += 1

    total_rev = sum(v['rev'] for v in cat_agg.values())

    cats_sorted = sorted(cat_agg.items(), key=lambda x: -x[1]['rev'])
    cats_out = []
    for cat, v in cats_sorted:
        pct = v['rev']/total_rev*100 if total_rev else 0
        cats_out.append({'cat': cat, 'rev': round(v['rev']), 'qty': round(v['qty']),
                         'count': v['count'], 'pct': round(pct,1)})

    # Top 20 by revenue
    sku_agg = defaultdict(lambda: {'cat':'','rev':0,'qty':0,'magnum':False})
    for r in records:
        sku_agg[r['name']]['cat']    = r['cat']
        sku_agg[r['name']]['rev']   += r['rev']
        sku_agg[r['name']]['qty']   += r['qty']
        sku_agg[r['name']]['magnum'] = r['magnum']

    top20 = sorted(sku_agg.items(), key=lambda x: -x[1]['rev'])[:20]
    top20_out = [{'name': k, **v, 'rev': round(v['rev']), 'qty': round(v['qty'])} for k,v in top20]

    # Magnum items
    magnum = [(k,v) for k,v in sku_agg.items() if v['magnum']]
    magnum_sorted = sorted(magnum, key=lambda x: -x[1]['rev'])[:30]
    magnum_out = [{'name': k, 'rev': round(v['rev']), 'qty': round(v['qty'])} for k,v in magnum_sorted]
    mag_rev = sum(v['rev'] for _,v in magnum)

    return {
        'total_rev': round(total_rev),
        'mag_rev': round(mag_rev),
        'mag_pct': round(mag_rev/total_rev*100, 1) if total_rev else 0,
        'sku_count': len(sku_agg),
        'categories': cats_out,
        'top20': top20_out,
        'magnum_items': magnum_out,
    }

# Cache: month_key → data
_cache = {}

# ── HTTP Handler ───────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass  # тихий режим

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == '/':
            self._serve_file(HTML_FILE, 'text/html; charset=utf-8')

        elif parsed.path == '/api/sales':
            month = params.get('month', [''])[0]
            if not re.match(r'20\d\d-\d\d', month):
                self._json_error('Неверный формат месяца. Пример: 2026-06')
                return
            if month not in _cache:
                try:
                    records = fetch_sales(month)
                    _cache[month] = aggregate(records)
                except Exception as e:
                    print(f"  Ошибка: {e}", flush=True)
                    self._json_error(str(e)); return
            self._json(_cache[month])

        elif parsed.path == '/api/months':
            # Список доступных месяцев (текущий год до сегодня)
            now = datetime.now()
            months = []
            for m in range(1, now.month + 1):
                months.append(f"{now.year}-{m:02d}")
            self._json({'months': months})

        elif parsed.path == '/reload':
            month = params.get('month', [''])[0]
            if month in _cache:
                del _cache[month]
            self._json({'ok': True})

        else:
            self.send_response(404); self.end_headers()

    def _serve_file(self, path, ctype):
        try:
            with open(path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404); self.end_headers()

    def _json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def _json_error(self, msg):
        self._json({'error': msg})

# ── Main ───────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("  Дашборд продаж — Live сервер")
    print(f"  http://localhost:{PORT}")
    print("=" * 50)

    # Pre-auth
    try:
        get_session()
    except Exception as e:
        print(f"  Ошибка авторизации: {e}")

    url = f"http://localhost:{PORT}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"\n  Открываю браузер...\n  Ctrl+C для остановки\n")

    server = HTTPServer(('localhost', PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Сервер остановлен.")
