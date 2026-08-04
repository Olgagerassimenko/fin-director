# -*- coding: utf-8 -*-
import json
d = json.load(open("/tmp/pf.json", encoding="utf-8"))
def f(v): return f"{round(v):,}".replace(","," ")
def mln(v): return (f"{v/1e6:.1f}".replace(".",",")+" млн")
pulled = d["updated"]; through = d["through"]
pi,pe = d["plan_inc"], d["plan_exp"]
fi,fe = d["fact_inc"], d["fact_exp"]
cs,ce = d["cash_start"], d["cash_end"]
inc_pct = fi/pi*100 if pi else 0
exp_pct = fe/pe*100 if pe else 0
net_plan = pi-pe; net_fact = fi-fe

def pct(v): return f"{v:.0f}%"
def dev_cls(x): return "pos" if x>=0 else "neg"

# category rows sorted by plan desc
rows = sorted(d["rows"], key=lambda r:-r["plan"])
def cat_row(r):
    dev = r["fact"]-r["plan"]
    p = (r["fact"]/r["plan"]*100) if r["plan"] else (100 if r["fact"]==0 else 0)
    # для расходов: факт < план -> хорошо (сэкономили) -> зелёный; факт > план -> красный
    good = r["fact"] <= r["plan"]
    barw = min(100, p)
    return f"""<tr>
      <td class="cat">{r['name']}</td>
      <td class="num">{f(r['plan'])}</td>
      <td class="num">{f(r['fact'])}</td>
      <td class="num {'pos' if good else 'neg'}">{'+' if dev>0 else ''}{f(dev)}</td>
      <td class="num">{pct(p) if r['plan'] else '—'}</td>
      <td class="barcell"><div class="bar"><div class="fill {'g' if good else 'r'}" style="width:{barw:.0f}%"></div></div></td>
    </tr>"""
cat_html = "\n".join(cat_row(r) for r in rows)
fo_html = "\n".join(
    f"""<tr><td class="cat">{r['name']}</td><td class="num">—</td><td class="num">{f(r['fact'])}</td>
    <td class="num neg">+{f(r['fact'])}</td><td class="num">—</td><td class="barcell"><div class="bar"><div class="fill r" style="width:100%"></div></div></td></tr>"""
    for r in d["fact_only"])

# weekly plan
wk = d["wk_inc"]; we = d["wk_exp"]
wmax = max(max(wk.values()), max(we.values()))
wk_html = ""
for w in ["1","2","3","4","5"]:
    ih = wk[w]/wmax*100; eh = we[w]/wmax*100
    wk_html += f"""<div class="wcol">
      <div class="wbars">
        <div class="wb in" style="height:{ih:.0f}%" title="поступления {f(wk[w])}"></div>
        <div class="wb ex" style="height:{eh:.0f}%" title="выплаты {f(we[w])}"></div>
      </div>
      <div class="wlab">Нед {w}</div>
      <div class="wval"><span class="ci">{mln(wk[w])}</span><span class="ce">{mln(we[w])}</span></div>
    </div>"""

zp = next(r for r in d["rows"] if r["name"].startswith("Оплата труда"))
zp_gap = zp["plan"]-zp["fact"]

html = f"""<!doctype html><html lang="ru"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ДДС · План-факт · Июль 2026</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:#0b1220;color:#e5edf7}}
.topbar{{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:18px 22px;background:linear-gradient(120deg,#0f1b33,#12213f);border-bottom:1px solid #1e2c48}}
.backbtn{{color:#93c5fd;text-decoration:none;font-weight:600;font-size:13px;background:#0e1b33;border:1px solid #24365a;padding:7px 12px;border-radius:9px}}
.topbar h1{{font-size:19px;margin:0}}
.topbar p{{margin:2px 0 0;font-size:12.5px;color:#9fb2cc}}
.upd-badge{{margin-left:auto;display:inline-flex;align-items:center;gap:10px;flex-wrap:wrap;background:rgba(16,185,129,.12);border:1px solid rgba(52,211,153,.45);border-radius:11px;padding:8px 14px}}
.upd-src{{color:#34d399;font-weight:800;font-size:13px;white-space:nowrap}}
.upd-when{{color:#cbd5e1;font-size:12.5px;font-weight:600;white-space:nowrap}}
.wrap{{max-width:1080px;margin:0 auto;padding:20px 18px 60px}}
.insight{{background:linear-gradient(120deg,#10233f,#122a49);border:1px solid #23consists;border:1px solid #234067;border-radius:14px;padding:16px 18px;margin-bottom:20px}}
.insight h2{{margin:0 0 10px;font-size:15px;color:#cfe0f5}}
.insight ul{{margin:0;padding-left:18px;line-height:1.7;font-size:13.5px;color:#c2d3e8}}
.insight b{{color:#fff}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:22px}}
.kpi{{background:#101d34;border:1px solid #1f2f4d;border-radius:14px;padding:14px 16px}}
.kpi .t{{font-size:12px;color:#8fa4c2;margin-bottom:8px}}
.kpi .pf{{display:flex;justify-content:space-between;font-size:12.5px;color:#b6c8e0;margin:3px 0}}
.kpi .pf b{{color:#fff;font-weight:700}}
.kpi .big{{font-size:22px;font-weight:800;margin-top:6px}}
.kpi .sub{{font-size:11.5px;color:#8fa4c2;margin-top:2px}}
.pos{{color:#34d399}} .neg{{color:#fb7185}}
.card{{background:#101d34;border:1px solid #1f2f4d;border-radius:16px;padding:18px 18px;margin-bottom:20px}}
.card h2{{margin:0 0 14px;font-size:15.5px;color:#e5edf7}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:right;color:#8fa4c2;font-weight:600;font-size:11.5px;padding:6px 8px;border-bottom:1px solid #24365a;text-transform:uppercase;letter-spacing:.02em}}
th.l,td.cat{{text-align:left}}
td{{padding:8px 8px;border-bottom:1px solid #17253f}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.cat{{font-weight:600;color:#dbe6f5}}
.barcell{{width:120px}}
.bar{{background:#17253f;border-radius:6px;height:9px;overflow:hidden;min-width:90px}}
.fill{{height:100%;border-radius:6px}}
.fill.g{{background:linear-gradient(90deg,#34d399,#10b981)}}
.fill.r{{background:linear-gradient(90deg,#fb7185,#f43f5e)}}
.note{{font-size:12px;color:#9fb2cc;margin-top:12px;line-height:1.6;background:#0e1a30;border-left:3px solid #f59e0b;padding:10px 12px;border-radius:0 8px 8px 0}}
.weekly{{display:flex;gap:10px;align-items:flex-end;height:190px;padding-top:10px}}
.wcol{{flex:1;display:flex;flex-direction:column;align-items:center;height:100%}}
.wbars{{flex:1;display:flex;gap:5px;align-items:flex-end;height:130px}}
.wb{{width:20px;border-radius:5px 5px 0 0}}
.wb.in{{background:linear-gradient(180deg,#38bdf8,#0ea5e9)}}
.wb.ex{{background:linear-gradient(180deg,#fb7185,#f43f5e)}}
.wlab{{font-size:12px;color:#b6c8e0;margin-top:8px;font-weight:600}}
.wval{{display:flex;flex-direction:column;align-items:center;font-size:10.5px;margin-top:2px}}
.wval .ci{{color:#38bdf8}} .wval .ce{{color:#fb7185}}
.legend{{display:flex;gap:16px;font-size:12px;color:#9fb2cc;margin-top:10px;justify-content:center}}
.dot{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:middle}}
.foot{{text-align:center;color:#6b7f9c;font-size:11.5px;margin-top:26px;line-height:1.7}}
@media(max-width:768px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.barcell{{display:none}}table{{font-size:12px}}}}
</style></head>
<body>
<div class="topbar">
  <a href="index.html" class="backbtn">← На главную</a>
  <div><h1>💧 ДДС · План-факт · Июль 2026</h1><p>План — недельный план оплат (Google) · Факт — iiko, прямой метод</p></div>
  <div class="upd-badge"><span class="upd-src">🔄 данные из iiko</span><span class="upd-when">обновлено {pulled} · данные по {through} включительно</span></div>
</div>
<div class="wrap">

  <div class="insight">
    <h2>📌 Главное за июль</h2>
    <ul>
      <li><b>Поступления</b>: собрали <b>{f(fi)} ₸</b> из плана <b>{f(pi)} ₸</b> — <b>{pct(inc_pct)}</b> плана (недобор {f(pi-fi)} ₸).</li>
      <li><b>Выплаты</b>: провели <b>{f(fe)} ₸</b> из плана <b>{f(pe)} ₸</b> — <b>{pct(exp_pct)}</b> плана.</li>
      <li><b>Касса</b>: {f(cs)} → <b>{f(ce)} ₸</b> за месяц <span class="neg">({'+' if ce-cs>0 else ''}{f(ce-cs)} ₸)</span> — денег на счетах стало меньше.</li>
      <li>Крупнейшее расхождение — <b>ЗП</b>: план {f(zp['plan'])}, факт по статье «Оплата труда» {f(zp['fact'])}. Разница {f(zp_gap)} ₸ ушла через <b>внутренние обороты</b> (снятие наличных на зарплату), см. примечание.</li>
    </ul>
  </div>

  <div class="kpis">
    <div class="kpi"><div class="t">💰 Поступления</div>
      <div class="pf">план <b>{f(pi)}</b></div><div class="pf">факт <b>{f(fi)}</b></div>
      <div class="big {dev_cls(fi-pi)}">{pct(inc_pct)}</div><div class="sub">исполнение плана</div></div>
    <div class="kpi"><div class="t">💸 Выплаты</div>
      <div class="pf">план <b>{f(pe)}</b></div><div class="pf">факт <b>{f(fe)}</b></div>
      <div class="big">{pct(exp_pct)}</div><div class="sub">от плана выплат</div></div>
    <div class="kpi"><div class="t">📊 Чистый поток</div>
      <div class="pf">план <b>{'+' if net_plan>0 else ''}{f(net_plan)}</b></div>
      <div class="pf">факт <b>{'+' if net_fact>0 else ''}{f(net_fact)}</b></div>
      <div class="big {dev_cls(net_fact)}">{'+' if net_fact>0 else ''}{mln(net_fact)}</div><div class="sub">поступления − выплаты (опер.)</div></div>
    <div class="kpi"><div class="t">🏦 Касса на конец</div>
      <div class="pf">начало <b>{f(cs)}</b></div><div class="pf">конец <b>{f(ce)}</b></div>
      <div class="big {dev_cls(ce-cs)}">{mln(ce-cs)}</div><div class="sub">изменение за месяц</div></div>
  </div>

  <div class="card">
    <h2>Выплаты по статьям: план vs факт</h2>
    <table>
      <thead><tr><th class="l">Статья</th><th>План ₸</th><th>Факт ₸</th><th>Отклонение</th><th>Исполн.</th><th class="l">Факт/План</th></tr></thead>
      <tbody>
      {cat_html}
      </tbody>
    </table>
    <div style="margin-top:16px;font-size:12px;color:#8fa4c2;font-weight:600">Было в факте, но не заложено в плане оплат:</div>
    <table><tbody>
      {fo_html}
    </tbody></table>
    <div class="note">⚠️ <b>Наличные платежи и внутренние обороты.</b> Часть плана — выплаты <b>наличными</b> (ЗП, подотчёт, логистика, погашение кредита, аренда жилья). В iiko эти суммы проходят как <b>снятие наличных со счёта</b> и попадают в статью «Внутренние обороты» (за июль: вход {f(d['internal_in'])} / выход {f(d['internal_out'])} ₸), а не в свою статью расхода. Поэтому по таким строкам факт занижен или показывает 0 — это <u>не экономия</u>, а иная классификация (например ЗП: план ~{mln(zp['plan'])}, факт по «Оплате труда» {f(zp['fact'])} ₸). Реальное исполнение по выплатам выше показанных {pct(exp_pct)}. Межсчётные обороты в сравнении исключены с обеих сторон.</div>
  </div>

  <div class="card">
    <h2>План по неделям (из плана оплат)</h2>
    <div class="weekly">{wk_html}</div>
    <div class="legend"><span><span class="dot" style="background:#0ea5e9"></span>поступления</span><span><span class="dot" style="background:#f43f5e"></span>выплаты</span></div>
  </div>

  <div class="foot">
    Система «Пульс» · автор: <b>Ольга Герасименко</b> · © 2026<br>
    План: лист «Неделя ОПЛАТ» (Google, «ДДС — Live») · Факт: iiko, прямой метод, июль 2026 · межсчётные обороты исключены
  </div>
</div>
</body></html>"""
open("дашборд_ддс_июль.html","w",encoding="utf-8").write(html)
print("написан дашборд_ддс_июль.html:", len(html), "байт")
