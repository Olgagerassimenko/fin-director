# -*- coding: utf-8 -*-
"""
rebuild_sales.py — пересобирает данные раздела «Продажи 2026» из выгрузок
«I Отчет  ПРОДАЖИ MM.2026.xlsx» (это проверенный источник: суммы сходятся
с отчётом iiko до тенге).

Для каждого месяца считает: выручку, категории, топ-20 SKU, Magnum Chef,
кол-во SKU. Валовую прибыль (total_gp) выгрузка не содержит — переносим
из прежних данных. Затем перезаписывает объект `const DS = {...}`
в продажи_2026.html.

Запуск: python rebuild_sales.py
"""
import sys, os, re, json, glob, warnings
from collections import defaultdict

warnings.filterwarnings("ignore")
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import openpyxl

HERE      = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(HERE, "продажи_2026.html")

RU_MONTHS = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
             "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

REVENUE_TYPE = "Выручка расходной накладной"


def log(*a):
    print(*a, flush=True)


def get_cat(name):
    """Классификатор категорий. Должен совпадать с skuCat() в sku_analytics.js,
    иначе диаграмма категорий и блок аналитики покажут разные цифры."""
    n = str(name).upper()
    def has(*w): return any(x in n for x in w)
    if has('КОМПОТ','МОРС','ЛИМОНАД','СОК ','ЧАЙ ','КОФЕ','ВОДА','НАПИТ','СМУЗИ','АЙРАН','КВАС'):
        return 'Напитки'
    if has('ТОРТ','БЕНТО'): return 'Торты'
    if has('КИМПАБ','ОНИГИР','УДОН','РАМЕН','СУШИ','ГИОЗА','ПОКЕ','ЯПОН','ВОК ','ЯННЕМ','ТОКПОК'):
        return 'Япония'
    if has('БЛИН','СЫРНИК','КАША','ОМЛЕТ','ЗАВТРАК','ГРАНОЛА','ХЛОПЬ'): return 'Завтраки'
    if has('САЛАТ','ШУБА','ВИНЕГРЕТ'): return 'Салаты'
    if has('СЭНДВИЧ','СЕНДВИЧ','БУРГЕР','ХОТ-ДОГ','ХОТДОГ','ДОГ (','ШАУРМА','ЧИАБАТТА','БАГЕТ С','ТОСТ'):
        return 'Сэндвичи'
    if has('ЧИЗКЕЙК','ТИРАМИСУ','БРАУНИ','МЕДОВИК','НАПОЛЕОН','ПИРОЖН','ЭКЛЕР','ДЕСЕРТ','ЧИА ',
           'ПУДДИНГ','ПУДИНГ','МАФФИН','КУКИС','ОРЕШКИ','СИННАБОН','МОРОЖ','ШАРЛОТКА','ПАХЛАВА',
           'ЗЕФИР','МАКАРУН'):
        return 'Десерты'
    if has('СОСИСКА В ТЕСТЕ','ПИРОЖОК','ПИРОГ','САМСА','СЛОЙК','КРУАССАН','БУЛОЧК','ХЛЕБ','ЛАВАШ',
           'БРЕЦЕЛЬ','СОЧНИК','ЛЕПЁШ','ЛЕПЕШ','ХАЧАПУРИ','ВЫПЕЧК','БАГЕТ','ШТРУДЕЛЬ','РУЛЕТ'):
        return 'Выпечка'
    if has('П/Ф','ПП*','КУРИЦ','ГОВЯД','СВИН','ИНДЕЙК','КОТЛЕТ','ШНИЦЕЛЬ','МАНТЫ','ПЛОВ','ПАСТА',
           'ПЕННЕ','ФУЗИЛЛИ','ЛАГМАН','ГУЙРУ','ЦОМЯН','ПЕЛЬМЕН','ВАРЕНИК','ТЕФТЕЛ','БРИЗОЛЬ','ЛЮЛЯ',
           'БЕФСТРОГ','ЗРАЗ','СУП ','БОРЩ','ТОМ ЯМ','КРЫЛЬЯ','ЗАПЕКАНК','ПЮРЕ','ГРЕЧК','РИС ','РАГУ',
           'ЖАРЕН','БИФШТЕКС','ГУЛЯШ','ТУЧИКЕН','ГАРНИР','ГОЛУБЦ','ФАРШ','ШАШЛЫК','СТЕЙК','НАГГЕТС',
           'КАРТОФ'):
        return 'Горячее'
    return 'Прочее'


def is_magnum(name):
    u = str(name).upper()
    return 'MAGNUM' in u or 'МАГНУМ' in u


def parse_report(path):
    """Возвращает (период_текст, dict[item] = {'rev':..,'qty':..})."""
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]
    period = ''
    items = defaultdict(lambda: {'rev': 0.0, 'qty': 0.0})
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 2 and row and row[0]:
            period = str(row[0])
        if i < 5 or not row or len(row) < 5:
            continue
        if str(row[2]).strip() != REVENUE_TYPE:
            continue
        name = str(row[1] or '').strip()
        if not name:
            continue
        try:
            rev = float(row[4])
        except (TypeError, ValueError):
            continue
        try:
            qty = abs(float(row[3]))
        except (TypeError, ValueError):
            qty = 0.0
        items[name]['rev'] += rev
        items[name]['qty'] += qty
    wb.close()
    return period, items


def build_month(items):
    cat_agg = defaultdict(lambda: {'rev': 0.0, 'qty': 0.0, 'count': 0})
    total_rev = 0.0
    for name, v in items.items():
        cat = get_cat(name)
        total_rev += v['rev']
        cat_agg[cat]['rev'] += v['rev']
        cat_agg[cat]['qty'] += v['qty']
        cat_agg[cat]['count'] += 1

    cats = [{'cat': c, 'rev': round(x['rev']), 'qty': round(x['qty']), 'count': x['count'],
             'pct': round(x['rev'] / total_rev * 100, 1) if total_rev else 0}
            for c, x in sorted(cat_agg.items(), key=lambda kv: -kv[1]['rev'])]

    ranked = sorted(items.items(), key=lambda kv: -kv[1]['rev'])
    top20 = [{'name': n, 'cat': get_cat(n), 'rev': round(v['rev']), 'qty': round(v['qty']),
              'magnum': is_magnum(n)} for n, v in ranked[:20]]

    mag = [(n, v) for n, v in items.items() if is_magnum(n)]
    mag_items = [{'name': n, 'rev': round(v['rev']), 'qty': round(v['qty'])}
                 for n, v in sorted(mag, key=lambda kv: -kv[1]['rev'])[:30]]
    mag_rev = sum(v['rev'] for _, v in mag)

    return {
        'total_rev': round(total_rev),
        'mag_rev': round(mag_rev),
        'mag_pct': round(mag_rev / total_rev * 100, 1) if total_rev else 0,
        'sku_count': len(items),
        'categories': cats,
        'top20': top20,
        'magnum_items': mag_items,
    }


def read_period(path):
    """Быстро читает строку «Период: с ДД.ММ.ГГГГ по ДД.ММ.ГГГГ»."""
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]
    txt = ''
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 2:
            txt = str(row[0]) if row and row[0] else ''
            break
    wb.close()
    m = re.search(r'с\s*(\d{2})\.(\d{2})\.(\d{4})\s*по\s*(\d{2})\.(\d{2})\.(\d{4})', txt)
    if not m:
        return None
    d1, m1, y1 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    d2, m2, y2 = int(m.group(4)), int(m.group(5)), int(m.group(6))
    return {'txt': txt, 'd1': d1, 'm1': m1, 'y1': y1, 'd2': d2, 'm2': m2, 'y2': y2}


def scan_reports(folder, year):
    """По каждому месяцу выбирает выгрузку с 1-го числа и самой поздней датой конца."""
    best = {}
    for path in glob.glob(os.path.join(folder, "I Отчет*ПРОДАЖИ*.xlsx")):
        if os.path.basename(path).startswith('~$'):
            continue
        try:
            p = read_period(path)
        except Exception:
            continue
        # берём только выгрузки «с 1-го числа» внутри одного месяца нужного года
        if not p or p['y1'] != year or p['m1'] != p['m2'] or p['d1'] != 1:
            continue
        m = p['m1']
        if m not in best or p['d2'] > best[m][2]['d2']:
            best[m] = (path, p['txt'], p)
    return best


def period_label(month_num, period_text):
    """«Период: с 01.07.2026 по 13.07.2026» -> ('Июль (1–13)', True)."""
    base = RU_MONTHS[month_num]
    m = re.search(r'с\s*(\d{2})\.(\d{2})\.(\d{4})\s*по\s*(\d{2})\.(\d{2})\.(\d{4})', period_text or '')
    if not m:
        return base, False
    d1, m1, d2, m2 = int(m.group(1)), int(m.group(2)), int(m.group(4)), int(m.group(5))
    import calendar
    last = calendar.monthrange(int(m.group(3)), m1)[1]
    if d1 == 1 and d2 >= last:
        return base, False
    return f"{base} ({d1}–{d2})", True


def load_html_and_old_ds():
    h = open(HTML_FILE, encoding='utf-8').read()
    i = h.find('const DS =')
    seg = h[i + len('const DS ='):]
    depth = 0; end = -1; st = False
    for j, ch in enumerate(seg):
        if ch == '{':
            depth += 1; st = True
        elif ch == '}':
            depth -= 1
            if st and depth == 0:
                end = j + 1; break
    obj = re.sub(r"'([A-Za-z_][A-Za-z0-9_]*)'\s*:", r'"\1":', seg[:end])
    return h, json.loads(obj)


def inject_ds(html, ds):
    i = html.find('const DS =')
    seg = html[i + len('const DS ='):]
    depth = 0; end = -1; st = False
    for j, ch in enumerate(seg):
        if ch == '{':
            depth += 1; st = True
        elif ch == '}':
            depth -= 1
            if st and depth == 0:
                end = j + 1; break
    return html[:i] + 'const DS = ' + json.dumps(ds, ensure_ascii=False) + seg[end:]



RETURNS_ANCHOR = '<div class="card"><canvas id="ch-year" height="340"></canvas></div>'
RETURNS_BLOCK = '\n  <div class="card" id="returns-card" style="margin-top:12px;display:none">\n    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:10px">\n      <div style="font-size:14px;font-weight:700;color:#f1f5f9">&#8617;&#65038; Возвраты покупателей <span style="font-weight:500;font-size:12px;color:#94a3b8">— уже вычтены из выручки на графике выше</span></div>\n      <div id="returns-total" style="font-size:13px;color:#c9a94e;font-weight:700"></div>\n    </div>\n    <div id="returns-chips" style="display:flex;flex-wrap:wrap;gap:8px"></div>\n  </div>\n  <script>\n  (function(){\n    function fmt(v){ v=Math.round(Math.abs(v));\n      if(v>=1e6) return (v/1e6).toFixed(1).replace(".",",")+" млн";\n      if(v>=1e3) return Math.round(v/1e3)+" тыс"; return String(v); }\n    function render(){\n      var card=document.getElementById("returns-card"); if(!card) return;\n      var R=(window.SALES_META&&window.SALES_META.returns)||null;\n      var keys=R?Object.keys(R).sort():[];\n      if(!keys.length){ card.style.display="none"; return; }\n      var MN=["","Янв","Фев","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек"];\n      var tot=0, gtot=0, chips="";\n      keys.forEach(function(k){\n        var val=R[k]||0, mo=parseInt(k.split("-")[1],10);\n        var net=(window.DS&&window.DS[k]&&window.DS[k].total_rev)||0, gross=net+val;\n        tot+=val; gtot+=gross;\n        var pctTxt=gross>0?" · "+(val/gross*100).toFixed(1).replace(".",",")+"%":"";\n        chips+=\'<span style="background:#0f172a;border:1px solid #334155;border-radius:9px;padding:6px 10px;font-size:12px;color:#cbd5e1">\'\n             +\'<b style="color:#e2e8f0">\'+(MN[mo]||k)+\'</b> &minus;\'+fmt(val)\n             +\'<span style="color:#94a3b8">\'+pctTxt+\'</span></span>\';\n      });\n      document.getElementById("returns-chips").innerHTML=chips;\n      var gpct=gtot>0?" ("+(tot/gtot*100).toFixed(1).replace(".",",")+"% от выручки)":"";\n      document.getElementById("returns-total").textContent="Итого возвраты: −"+fmt(tot)+gpct;\n      card.style.display="block";\n    }\n    if(document.readyState==="loading"){ document.addEventListener("DOMContentLoaded",render); } else { render(); }\n  })();\n  </script>'

def inject_returns_block(html):
    """Вставляет блок «Возвраты покупателей» под графиком выручки (идемпотентно)."""
    if 'id="returns-card"' in html:
        return html
    i = html.find(RETURNS_ANCHOR)
    if i < 0:
        return html
    j = i + len(RETURNS_ANCHOR)
    return html[:j] + RETURNS_BLOCK + html[j:]


def main():
    log("=" * 60)
    log("  Пересборка продаж из выгрузок «I Отчет ПРОДАЖИ»")
    log("=" * 60)

    html, old = load_html_and_old_ds()
    year = 2026
    months = {}
    year_months = []

    reports = scan_reports(HERE, year)
    log(f"  Найдены выгрузки по месяцам: {sorted(reports.keys())}\n")

    all_items = defaultdict(lambda: {'rev': 0.0, 'qty': 0.0})   # накопление за год

    for m in range(1, 13):
        if m not in reports:
            continue
        path = reports[m][0]
        log(f"  · {RU_MONTHS[m]}: {os.path.basename(path)}")
        period, items = parse_report(path)
        if not items:
            log(f"  {RU_MONTHS[m]:8} — пусто, пропуск ({os.path.basename(path)})")
            continue
        for _n, _v in items.items():
            all_items[_n]['rev'] += _v['rev']
            all_items[_n]['qty'] += _v['qty']

        md = build_month(items)
        label, partial = period_label(m, period)
        md['label'] = label

        mk = f"{year}-{m:02d}"
        gp_old = (old.get(mk) or {}).get('total_gp')
        md['total_gp'] = gp_old if gp_old else 0
        if mk in old:
            for k, v in old[mk].items():
                if k not in md:
                    md[k] = v
        months[mk] = md
        year_months.append({'mk': mk, 'label': label, 'rev': md['total_rev'],
                            'gp': gp_old if gp_old else None,
                            **({'partial': True} if partial else {})})
        old_rev = (old.get(mk) or {}).get('total_rev', 0)
        diff = md['total_rev'] - old_rev
        log(f"  {label:16} {md['total_rev']:>14,}   было {old_rev:>14,}   Δ {diff:>+13,}   SKU={md['sku_count']}")

    # ── валовая прибыль неполного месяца ───────────────────────────────
    # Выгрузка продаж не содержит себестоимости, а перенесённая ВП относится
    # к прежнему (более короткому) периоду — из-за этого маржа занижалась.
    # Для неполного месяца оцениваем ВП по средней марже последних полных
    # месяцев, где ВП известна, и помечаем как оценку.
    full_m = [x for x in year_months if not x.get('partial') and x['gp'] and x['rev']]
    if full_m:
        base = full_m[-2:]
        margin = sum(x['gp'] for x in base) / sum(x['rev'] for x in base)
        for x in year_months:
            if x.get('partial'):
                est = round(x['rev'] * margin)
                x['gp'] = est
                x['gp_est'] = True
                months[x['mk']]['total_gp'] = est
                months[x['mk']]['gp_est'] = True
                log(f"  ~ {x['label']}: ВП оценена по марже {margin*100:.1f}% → {est:,} "
                    f"(была перенесена за другой период)")

    total_rev = sum(x['rev'] for x in year_months)
    total_gp = sum(x['gp'] for x in year_months if x['gp'])
    last_m = int(year_months[-1]['mk'][5:7]) if year_months else 1
    ds = dict(months)
    # Год оформляем так же, как месяц: категории, топ-SKU, Magnum — но итогово
    ya = build_month(all_items)
    ds['year'] = {'label': f"{year} — Янв–{RU_MONTHS[last_m][:3]}",
                  'total_rev': total_rev, 'total_gp': total_gp,
                  'is_year': True, 'months': year_months,
                  'categories': ya['categories'], 'top20': ya['top20'],
                  'magnum_items': ya['magnum_items'], 'mag_rev': ya['mag_rev'],
                  'mag_pct': ya['mag_pct'], 'sku_count': ya['sku_count']}
    log(f"  {'ГОД (итого)':16} категорий={len(ya['categories'])}  SKU={ya['sku_count']}")

    old_year = (old.get('year') or {}).get('total_rev', 0)
    log("-" * 60)
    log(f"  {'ИТОГО ГОД':16} {total_rev:>14,}   было {old_year:>14,}   Δ {total_rev-old_year:>+13,}")

    bak = HTML_FILE + ".bak2"
    if not os.path.exists(bak):
        open(bak, 'w', encoding='utf-8').write(html)
    open(HTML_FILE, 'w', encoding='utf-8').write(inject_returns_block(inject_ds(html, ds)))
    log(f"  Записано: {HTML_FILE}")
    log("  Готово.")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        log("  ОШИБКА:", e)
        traceback.print_exc()
        sys.exit(1)
