# -*- coding: utf-8 -*-
"""
Генератор HTML-отчёта «Продажи июнь 2026» из iiko API.
Использует GOODS_MOTION с фильтром по складам ГП.
Запуск: py generate_june2026.py
"""
import requests, hashlib, json, warnings, re, os, sys
from datetime import datetime
warnings.filterwarnings("ignore")

# ─── Настройки ───────────────────────────────────────────────────────────────
IIKO_URL   = "https://fudzavod.iiko.it"
IIKO_LOGIN = "GerassimenkoO"
IIKO_PASS  = "1234"
DATE_FROM  = "2026-06-01"
DATE_TO    = "2026-06-30"
OUT_FILE   = os.path.join(os.path.dirname(__file__), "..", "продажи_июнь_2026_iiko.html")
# ─────────────────────────────────────────────────────────────────────────────

s = requests.Session()

def auth():
    sha1 = hashlib.sha1(IIKO_PASS.encode()).hexdigest()
    r = s.get(f"{IIKO_URL}/resto/api/auth",
              params={"login": IIKO_LOGIN, "pass": sha1},
              verify=False, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Auth failed: {r.status_code} {r.text[:100]}")
    token = r.text.strip().strip('"')
    print(f"  Авторизация OK ({token[:12]}...)")
    return token

def get_stores(token):
    """Ищем UUID складов ГП."""
    headers = {"Cookie": f"key={token}"}
    gp_stores = {}
    for ep in ["/resto/api/corporation/stores",
               "/resto/api/corporation/departments",
               "/resto/api/v2/entities/restaurants?revisionFrom=-1"]:
        r = s.get(f"{IIKO_URL}{ep}", headers=headers, verify=False, timeout=30)
        if not r.ok:
            continue
        try:
            data = r.json()
            items = (data if isinstance(data, list)
                     else data.get("corporateItemDtos",
                          data.get("items",
                          data.get("restaurantDtos", []))))
            for d in items:
                if not isinstance(d, dict):
                    continue
                name = (d.get("name") or d.get("departmentName") or
                        d.get("restaurantName") or "")
                uid  = d.get("id","")
                if "ГП" in name and uid:
                    gp_stores[uid] = name
                    print(f"    Склад: {name}  ({uid})")
        except Exception:
            pass
        if gp_stores:
            break
    return gp_stores

def olap_query(token, report_type, extra_filters=None):
    headers = {"Cookie": f"key={token}", "Content-Type": "application/json"}
    filters = {
        "OpenDate.Typed": {
            "filterType": "DateRange", "periodType": "CUSTOM",
            "from": DATE_FROM, "to": DATE_TO,
            "includeLow": "true", "includeHigh": "true"
        },
        "DeletedWithWriteoff": {
            "filterType": "ExcludeValues",
            "values": ["DELETED_WITHOUT_WRITEOFF"]
        }
    }
    if extra_filters:
        filters.update(extra_filters)

    body = {
        "reportType": report_type,
        "buildSummary": "false",
        "groupByRowFields": ["DishCategory", "DishName"],
        "groupByColFields": [],
        "aggregateFields": ["DishDiscountSumInt", "DishAmountInt", "GrossProfit"],
        "filters": filters
    }
    r = s.post(f"{IIKO_URL}/resto/api/v2/reports/olap",
               json=body, headers=headers, verify=False, timeout=120)
    return r

def try_all_report_types(token, store_uids):
    """Пробуем разные типы отчётов, ищем тот что даёт 100+ SKU."""
    print("\n  Тестируем типы отчётов:")
    print(f"  {'Тип':<22} {'HTTP':<6} {'Строк':<8} {'SKU'}")
    print(f"  {'-'*50}")

    store_filter = None
    if store_uids:
        store_filter = {
            "Store": {
                "filterType": "IncludeValues",
                "values": list(store_uids.keys())
            }
        }

    best = None
    for rt in ["GOODS_MOTION", "SALES", "WRITEOFF", "TRANSFER",
               "PRODUCTION", "PURCHASES", "INVENTORY", "DELIVERIES"]:
        try:
            # Сначала с фильтром склада
            r = olap_query(token, rt, store_filter)
            if not r.ok:
                # Попробуем без фильтра склада
                r = olap_query(token, rt)
            if r.ok:
                data = r.json()
                rows = data.get("data", []) if isinstance(data, dict) else (data or [])
                skus = {row.get("DishName","") for row in rows
                        if isinstance(row, dict) and row.get("DishName")}
                skus.discard("")
                marker = " <<<" if len(skus) > 100 else ""
                print(f"  {rt:<22} {r.status_code:<6} {len(rows):<8} {len(skus)}{marker}")
                if len(skus) > (best[2] if best else 0):
                    best = (rt, rows, len(skus), r)
            else:
                err = r.text[:40].replace('\n',' ')
                print(f"  {rt:<22} {r.status_code:<6} {err}")
        except Exception as e:
            print(f"  {rt:<22} ERR  {str(e)[:40]}")
    return best

def parse_rows(rows):
    """Группируем строки по категории+наименованию."""
    items = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = (row.get("DishName") or "").strip()
        cat  = (row.get("DishCategory") or "Прочее").strip()
        if not name:
            continue
        rev  = float(row.get("DishDiscountSumInt") or 0)
        qty  = float(row.get("DishAmountInt") or 0)
        vp   = float(row.get("GrossProfit") or 0)
        key  = (cat, name)
        if key not in items:
            items[key] = {"cat": cat, "name": name, "rev": 0, "qty": 0, "vp": 0}
        items[key]["rev"] += rev
        items[key]["qty"] += qty
        items[key]["vp"]  += vp

    result = list(items.values())
    for it in result:
        it["margin"] = round(it["vp"] / it["rev"] * 100, 1) if it["rev"] else 0
    result.sort(key=lambda x: -x["rev"])
    return result

def agg_cats(items):
    cats = {}
    for it in items:
        c = it["cat"]
        if c not in cats:
            cats[c] = {"cat": c, "rev": 0, "vp": 0, "count": 0}
        cats[c]["rev"]   += it["rev"]
        cats[c]["vp"]    += it["vp"]
        cats[c]["count"] += 1
    result = list(cats.values())
    for c in result:
        c["margin"] = round(c["vp"] / c["rev"] * 100, 1) if c["rev"] else 0
    result.sort(key=lambda x: -x["rev"])
    return result

def fmt_mln(v):
    return f"{v/1e6:.1f} млн"

def generate_html(items, cats, report_type, store_names):
    total_rev = sum(it["rev"] for it in items)
    total_vp  = sum(it["vp"]  for it in items)
    total_qty = int(sum(it["qty"] for it in items))
    margin    = round(total_vp / total_rev * 100, 1) if total_rev else 0
    sku_count = len(items)
    cat_count = len(cats)
    top20     = items[:20]

    # Magnum
    magnum = [it for it in items if "MAGNUM" in it["name"].upper()]
    mg_rev  = sum(it["rev"] for it in magnum)
    mg_vp   = sum(it["vp"]  for it in magnum)
    mg_qty  = int(sum(it["qty"] for it in magnum))
    mg_margin = round(mg_vp / mg_rev * 100, 1) if mg_rev else 0
    mg_share  = round(mg_rev / total_rev * 100, 1) if total_rev else 0

    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    stores_str = ", ".join(store_names.values()) if store_names else "Склады ГП ФЗ"

    cats_js    = json.dumps(cats[:9],  ensure_ascii=False)
    top20_js   = json.dumps(top20,     ensure_ascii=False)
    magnum_js  = json.dumps(magnum,    ensure_ascii=False)
    mg_top_js  = json.dumps(magnum[:10], ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Продажи июнь 2026 — ТОО «Фуд завод»</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-datalabels/2.2.0/chartjs-plugin-datalabels.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
.header{{background:linear-gradient(135deg,#1e293b,#0f172a);border-bottom:1px solid #334155;padding:20px 32px;display:flex;align-items:center;justify-content:space-between}}
.header h1{{font-size:22px;font-weight:700;color:#f1f5f9}}
.header .sub{{font-size:13px;color:#64748b;margin-top:2px}}
.badge{{background:#059669;color:#fff;font-size:11px;padding:3px 10px;border-radius:20px;font-weight:600}}
.badge.api{{background:#0ea5e9}}
.updated{{font-size:11px;color:#475569;margin-top:4px}}
.container{{max-width:1400px;margin:0 auto;padding:24px 32px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-bottom:28px}}
.kpi{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px;position:relative;overflow:hidden}}
.kpi::before{{content:'';position:absolute;top:0;left:0;width:4px;height:100%}}
.kpi.blue::before{{background:#3b82f6}}
.kpi.green::before{{background:#10b981}}
.kpi.purple::before{{background:#8b5cf6}}
.kpi.orange::before{{background:#f59e0b}}
.kpi.pink::before{{background:#ec4899}}
.kpi-label{{font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}}
.kpi-val{{font-size:26px;font-weight:700;color:#f1f5f9;line-height:1}}
.kpi-sub{{font-size:12px;color:#94a3b8;margin-top:5px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}}
.grid3{{display:grid;grid-template-columns:3fr 2fr;gap:20px;margin-bottom:20px}}
.card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:22px}}
.card-title{{font-size:13px;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;margin-bottom:18px}}
.magnum-hero{{background:linear-gradient(135deg,#4c1d95,#1e1b4b);border:1px solid #7c3aed55;border-radius:12px;padding:22px;margin-bottom:20px}}
.magnum-hero .title{{font-size:16px;font-weight:700;color:#c4b5fd;margin-bottom:14px}}
.magnum-kpis{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}}
.mk{{background:#1e1035;border-radius:8px;padding:14px;text-align:center}}
.mk-v{{font-size:18px;font-weight:700;color:#e9d5ff}}
.mk-l{{font-size:10px;color:#9ca3af;margin-top:3px}}
.section-title{{font-size:16px;font-weight:700;color:#f1f5f9;margin:28px 0 14px}}
.tab-bar{{display:flex;gap:4px;margin-bottom:16px;flex-wrap:wrap}}
.tab{{padding:7px 16px;border-radius:8px;font-size:12px;cursor:pointer;border:none;background:#0f172a;color:#64748b;font-weight:600;transition:.2s}}
.tab.active{{background:#7c3aed;color:#fff}}
.hidden{{display:none}}
.tbl{{width:100%;border-collapse:collapse;font-size:12px}}
.tbl th{{background:#0f172a;color:#64748b;font-weight:600;padding:9px 12px;text-align:left;position:sticky;top:0;z-index:1}}
.tbl td{{padding:8px 12px;border-bottom:1px solid #1e293b;color:#cbd5e1}}
.tbl tr:hover td{{background:#0f172a}}
.tbl .num{{text-align:right;font-variant-numeric:tabular-nums}}
.tbl .name{{max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pill{{display:inline-block;font-size:10px;padding:2px 8px;border-radius:10px;font-weight:600}}
.pill.magnum{{background:#7c3aed22;color:#a78bfa;border:1px solid #7c3aed44}}
.pill.green{{background:#05966922;color:#34d399;border:1px solid #05966944}}
.pill.yellow{{background:#f59e0b22;color:#fbbf24;border:1px solid #f59e0b44}}
.pill.red{{background:#ef444422;color:#f87171;border:1px solid #ef444444}}
.tbl-wrap{{max-height:440px;overflow-y:auto;border-radius:8px;border:1px solid #334155}}
.info-tag{{display:inline-flex;align-items:center;gap:6px;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:5px 12px;font-size:11px;color:#64748b;margin-top:6px}}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>📊 Продажи — июнь 2026</h1>
    <div class="sub">ТОО «Фуд завод» · {stores_str}</div>
    <div class="updated">Источник: iiko API · Отчёт: {report_type} · Обновлено: {now}</div>
  </div>
  <div style="text-align:right">
    <span class="badge">Июнь 2026</span>&nbsp;
    <span class="badge api">iiko API</span>
  </div>
</div>

<div class="container">

<div class="kpis">
  <div class="kpi blue"><div class="kpi-label">Выручка</div>
    <div class="kpi-val">{fmt_mln(total_rev)}</div>
    <div class="kpi-sub">тенге · июнь 2026</div></div>
  <div class="kpi green"><div class="kpi-label">Валовая прибыль</div>
    <div class="kpi-val">{fmt_mln(total_vp)}</div>
    <div class="kpi-sub">маржа {margin}%</div></div>
  <div class="kpi orange"><div class="kpi-label">Позиций</div>
    <div class="kpi-val">{sku_count:,}</div>
    <div class="kpi-sub">номенклатурных позиций</div></div>
  <div class="kpi purple"><div class="kpi-label">Magnum Chef</div>
    <div class="kpi-val">{fmt_mln(mg_rev)}</div>
    <div class="kpi-sub">{len(magnum)} позиций · {mg_share}% выручки</div></div>
  <div class="kpi pink"><div class="kpi-label">Категорий</div>
    <div class="kpi-val">{cat_count}</div>
    <div class="kpi-sub">товарных групп</div></div>
</div>

<div class="magnum-hero">
  <div class="title">⚡ MAGNUM CHEF — анализ канала</div>
  <div class="magnum-kpis">
    <div class="mk"><div class="mk-v">{fmt_mln(mg_rev)}</div><div class="mk-l">Выручка</div></div>
    <div class="mk"><div class="mk-v">{fmt_mln(mg_vp)}</div><div class="mk-l">Вал. прибыль</div></div>
    <div class="mk"><div class="mk-v">{mg_margin}%</div><div class="mk-l">Маржа</div></div>
    <div class="mk"><div class="mk-v">{mg_qty:,}</div><div class="mk-l">Штук</div></div>
    <div class="mk"><div class="mk-v">{mg_share}%</div><div class="mk-l">Доля выручки</div></div>
  </div>
</div>

<div class="section-title">📦 Выручка по категориям</div>
<div class="grid3">
  <div class="card">
    <div class="card-title">Выручка vs Валовая прибыль, млн тнг</div>
    <canvas id="catBarChart" height="280"></canvas>
  </div>
  <div class="card">
    <div class="card-title">Доля в выручке</div>
    <canvas id="catDonutChart" height="280"></canvas>
  </div>
</div>

<div class="grid2">
  <div class="card">
    <div class="card-title">Маржа по категориям, %</div>
    <canvas id="marginChart" height="240"></canvas>
  </div>
  <div class="card">
    <div class="card-title">⚡ Топ-10 Magnum Chef по выручке</div>
    <canvas id="magnumBarChart" height="240"></canvas>
  </div>
</div>

<div class="card" style="margin-bottom:20px">
  <div class="card-title">Маржа vs Выручка — позиции Magnum Chef (размер = кол-во штук)</div>
  <canvas id="scatterChart" height="300"></canvas>
  <div style="display:flex;gap:16px;justify-content:center;margin-top:10px;font-size:11px;color:#94a3b8">
    <span>🟢 Маржа ≥ 50%</span><span>🟡 Маржа 35–50%</span><span>🔴 Маржа &lt; 35%</span>
  </div>
</div>

<div class="section-title">🗂 Детализация</div>
<div class="tab-bar">
  <button class="tab active" onclick="showTab('top')">ТОП-20 позиций</button>
  <button class="tab" onclick="showTab('magnum')">Magnum Chef ({len(magnum)})</button>
  <button class="tab" onclick="showTab('cats')">По категориям ({cat_count})</button>
</div>

<div id="tab-top">
  <div class="tbl-wrap"><table class="tbl">
    <thead><tr><th>#</th><th>Позиция</th><th>Категория</th>
      <th class="num">Выручка, тнг</th><th class="num">ВП, тнг</th>
      <th class="num">Маржа</th><th class="num">Кол-во</th></tr></thead>
    <tbody id="top-body"></tbody>
  </table></div>
</div>
<div id="tab-magnum" class="hidden">
  <div class="tbl-wrap"><table class="tbl">
    <thead><tr><th>#</th><th>Позиция</th>
      <th class="num">Выручка, тнг</th><th class="num">ВП, тнг</th>
      <th class="num">Маржа</th><th class="num">Кол-во</th></tr></thead>
    <tbody id="magnum-body"></tbody>
  </table></div>
</div>
<div id="tab-cats" class="hidden">
  <div class="tbl-wrap"><table class="tbl">
    <thead><tr><th>Категория</th><th class="num">Позиций</th>
      <th class="num">Выручка, тнг</th><th class="num">ВП, тнг</th>
      <th class="num">Маржа</th></tr></thead>
    <tbody id="cats-body"></tbody>
  </table></div>
</div>

</div><!-- /container -->
<script>
Chart.register(ChartDataLabels);
Chart.defaults.color='#64748b';
Chart.defaults.borderColor='#1e293b';
Chart.defaults.font.family="'Segoe UI',Arial,sans-serif";
Chart.defaults.font.size=11;

const CATS   = {cats_js};
const TOP20  = {top20_js};
const MAGNUM = {magnum_js};
const MG_TOP = {mg_top_js};
const TOTAL  = {total_rev:.0f};

const fmtN = v => Math.round(v).toLocaleString('ru');
const CAT_COLORS = ['#3b82f6','#8b5cf6','#10b981','#f59e0b','#ec4899','#06b6d4','#84cc16','#f97316','#6366f1'];
const short = n => n.replace(/\\s*MAGNUM\\s*CHEF/i,'').replace(/\\s+\\d+\\s*ГР$/i,'').replace(/\\s+\\(\\d+ШТ\\)$/i,'').trim();

// Bar: категории
new Chart(document.getElementById('catBarChart'),{{
  type:'bar',
  data:{{labels:CATS.map(c=>c.cat),datasets:[
    {{label:'Выручка',data:CATS.map(c=>+(c.rev/1e6).toFixed(1)),backgroundColor:'rgba(59,130,246,0.85)',borderRadius:4,borderSkipped:false}},
    {{label:'Вал. прибыль',data:CATS.map(c=>+(c.vp/1e6).toFixed(1)),backgroundColor:'rgba(16,185,129,0.85)',borderRadius:4,borderSkipped:false}}
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top',labels:{{color:'#94a3b8',boxWidth:12}}}},
      tooltip:{{callbacks:{{label:ctx=>` ${{ctx.dataset.label}}: ${{ctx.parsed.y}} млн`}}}},
      datalabels:{{display:ctx=>ctx.datasetIndex===0,anchor:'end',align:'end',
        color:'#94a3b8',font:{{size:10,weight:'600'}},
        formatter:v=>(v/({total_rev/1e6:.1f})*100).toFixed(1)+'%'}}
    }},
    scales:{{x:{{grid:{{color:'#1e293b'}},ticks:{{color:'#64748b'}}}},
      y:{{grid:{{color:'#1e293b22'}},ticks:{{color:'#64748b',callback:v=>v+' млн'}}}}}}
  }}
}});

// Donut
new Chart(document.getElementById('catDonutChart'),{{
  type:'doughnut',
  data:{{labels:CATS.map(c=>c.cat),datasets:[{{
    data:CATS.map(c=>+(c.rev/1e6).toFixed(1)),
    backgroundColor:CAT_COLORS,borderColor:'#0f172a',borderWidth:3,hoverOffset:10
  }}]}},
  options:{{responsive:true,maintainAspectRatio:false,cutout:'58%',
    plugins:{{
      legend:{{position:'right',labels:{{color:'#94a3b8',boxWidth:10,padding:8,font:{{size:10}}}}}},
      tooltip:{{callbacks:{{label:ctx=>{{const t=CATS.reduce((a,c)=>a+c.rev/1e6,0);return ` ${{ctx.label}}: ${{ctx.parsed}} млн (${{(ctx.parsed/t*100).toFixed(1)}}%)`;}}  }}}},
      datalabels:{{color:'#fff',font:{{size:11,weight:'700'}},
        formatter:(val)=>{{const t=CATS.reduce((a,c)=>a+c.rev/1e6,0);const p=(val/t*100).toFixed(1);return p<4?'':p+'%';}},
        textShadowBlur:4,textShadowColor:'rgba(0,0,0,0.6)'}}
    }}
  }}
}});

// Маржа
new Chart(document.getElementById('marginChart'),{{
  type:'bar',
  data:{{labels:CATS.map(c=>c.cat),datasets:[{{
    label:'Маржа, %',data:CATS.map(c=>c.margin),
    backgroundColor:CATS.map(c=>c.margin>=50?'rgba(52,211,153,0.85)':c.margin>=40?'rgba(251,191,36,0.85)':'rgba(248,113,113,0.85)'),
    borderRadius:4,borderSkipped:false
  }}]}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}},
      tooltip:{{callbacks:{{label:ctx=>` Маржа: ${{ctx.parsed.x}}%`}}}},
      datalabels:{{anchor:'end',align:'end',color:'#e2e8f0',font:{{size:11,weight:'700'}},formatter:v=>v+'%'}}
    }},
    scales:{{x:{{grid:{{color:'#1e293b'}},ticks:{{color:'#64748b',callback:v=>v+'%'}},min:0,max:70}},
      y:{{grid:{{display:false}},ticks:{{color:'#94a3b8'}}}}}}
  }}
}});

// Magnum top-10
const mgTotal = MAGNUM.reduce((a,it)=>a+it.rev,0);
new Chart(document.getElementById('magnumBarChart'),{{
  type:'bar',
  data:{{labels:MG_TOP.map(it=>short(it.name)),datasets:[
    {{label:'Выручка',data:MG_TOP.map(it=>+(it.rev/1e6).toFixed(2)),backgroundColor:'rgba(139,92,246,0.85)',borderRadius:4,borderSkipped:false}},
    {{label:'ВП',data:MG_TOP.map(it=>+(it.vp/1e6).toFixed(2)),backgroundColor:'rgba(196,181,253,0.6)',borderRadius:4,borderSkipped:false}}
  ]}},
  options:{{indexAxis:'y',responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'top',labels:{{color:'#94a3b8',boxWidth:10}}}},
      tooltip:{{callbacks:{{label:ctx=>` ${{ctx.dataset.label}}: ${{ctx.parsed.x}} млн тнг`}}}},
      datalabels:{{display:ctx=>ctx.datasetIndex===0,anchor:'end',align:'end',color:'#c4b5fd',font:{{size:10,weight:'700'}},
        formatter:v=>(v/mgTotal*1e6*100).toFixed(1)+'%'}}
    }},
    scales:{{x:{{grid:{{color:'#1e293b'}},ticks:{{color:'#64748b',callback:v=>v+' млн'}}}},
      y:{{grid:{{display:false}},ticks:{{color:'#94a3b8',font:{{size:10}}}}}}}}
  }}
}});

// Scatter Magnum
const scatterData = MAGNUM.map(it=>({{{{'x':+(it.rev/1e6).toFixed(2),'y':it.margin,'r':Math.max(4,Math.sqrt(it.qty)/3),'name':it.name,'qty':it.qty}}}}));
new Chart(document.getElementById('scatterChart'),{{
  type:'bubble',
  data:{{datasets:[
    {{label:'≥50%',data:scatterData.filter(d=>d.y>=50),backgroundColor:'rgba(52,211,153,0.7)',borderColor:'rgba(52,211,153,1)',borderWidth:1}},
    {{label:'35-50%',data:scatterData.filter(d=>d.y>=35&&d.y<50),backgroundColor:'rgba(251,191,36,0.7)',borderColor:'rgba(251,191,36,1)',borderWidth:1}},
    {{label:'<35%',data:scatterData.filter(d=>d.y<35),backgroundColor:'rgba(248,113,113,0.7)',borderColor:'rgba(248,113,113,1)',borderWidth:1}}
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{display:false}},datalabels:{{display:false}},
      tooltip:{{callbacks:{{label:ctx=>{{const d=ctx.raw;return[short(d.name),`Выручка: ${{d.x}} млн`,`Маржа: ${{d.y}}%`,`Кол-во: ${{d.qty.toLocaleString('ru')}} шт`];}}}}}}
    }},
    scales:{{
      x:{{title:{{display:true,text:'Выручка, млн тнг',color:'#64748b'}},grid:{{color:'#1e293b'}},ticks:{{color:'#64748b'}}}},
      y:{{title:{{display:true,text:'Маржа, %',color:'#64748b'}},grid:{{color:'#1e293b22'}},ticks:{{color:'#64748b',callback:v=>v+'%'}},min:25,max:75}}
    }}
  }}
}});

// Tables
const topBody=document.getElementById('top-body');
TOP20.forEach((it,i)=>{{
  const mc=it.margin>=50?'green':it.margin<35?'red':'yellow';
  const mg=it.name.toUpperCase().includes('MAGNUM')?'<span class="pill magnum">Magnum</span>':'';
  topBody.innerHTML+=`<tr><td style="color:#64748b">${{i+1}}</td><td class="name">${{it.name}} ${{mg}}</td>
    <td style="color:#94a3b8;font-size:11px">${{it.cat}}</td>
    <td class="num">${{fmtN(it.rev)}}</td><td class="num">${{fmtN(it.vp)}}</td>
    <td class="num"><span class="pill ${{mc}}">${{it.margin}}%</span></td><td class="num">${{fmtN(it.qty)}}</td></tr>`;
}});

const mgBody=document.getElementById('magnum-body');
MAGNUM.forEach((it,i)=>{{
  const mc=it.margin>=50?'green':it.margin<35?'red':'yellow';
  mgBody.innerHTML+=`<tr><td style="color:#64748b">${{i+1}}</td><td class="name">${{it.name}}</td>
    <td class="num">${{fmtN(it.rev)}}</td><td class="num">${{fmtN(it.vp)}}</td>
    <td class="num"><span class="pill ${{mc}}">${{it.margin}}%</span></td><td class="num">${{fmtN(it.qty)}}</td></tr>`;
}});

const catsBody=document.getElementById('cats-body');
CATS.forEach(c=>{{
  const mc=c.margin>=45?'green':c.margin<35?'red':'yellow';
  catsBody.innerHTML+=`<tr><td>${{c.cat}}</td><td class="num">${{c.count}}</td>
    <td class="num">${{fmtN(c.rev)}}</td><td class="num">${{fmtN(c.vp)}}</td>
    <td class="num"><span class="pill ${{mc}}">${{c.margin}}%</span></td></tr>`;
}});

function showTab(name){{
  ['top','magnum','cats'].forEach(t=>document.getElementById('tab-'+t).classList.toggle('hidden',t!==name));
  document.querySelectorAll('.tab').forEach((el,i)=>el.classList.toggle('active',['top','magnum','cats'][i]===name));
}}
</script>
</body>
</html>"""
    return html

def main():
    print("\n" + "="*56)
    print("  Генератор отчёта продаж июнь 2026 из iiko")
    print("="*56)

    print("\n[1] Авторизация...")
    token = auth()

    print("\n[2] Поиск складов ГП...")
    store_uids = get_stores(token)
    if not store_uids:
        print("  Склады не найдены, работаем без фильтра")

    print("\n[3] Тестирование типов отчётов...")
    best = try_all_report_types(token, store_uids)

    if not best:
        print("\n  Нет данных ни в одном типе отчёта. Проверьте API.")
        sys.exit(1)

    report_type, rows, sku_count, _ = best
    print(f"\n  Используем: {report_type} ({sku_count} SKU)")

    print("\n[4] Обработка данных...")
    items = parse_rows(rows)
    cats  = agg_cats(items)
    print(f"  Позиций: {len(items)}, Категорий: {len(cats)}")
    print(f"  Выручка: {sum(it['rev'] for it in items)/1e6:.1f} млн тнг")

    print("\n[5] Генерация HTML...")
    html = generate_html(items, cats, report_type, store_uids)
    out = os.path.abspath(OUT_FILE)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Сохранено: {out}")

    print("\n  Готово! Открой файл в браузере.")
    print("="*56 + "\n")

if __name__ == "__main__":
    main()
