# -*- coding: utf-8 -*-
"""Журнал изменений сайта «Пульс».

Собирает историю правок прямо из git и раскладывает её по дням и разделам.
Правки людей и автоматические обновления данных разделены: первые — лента,
вторые — свёрнутая строка «обновились данные».

Запускается в CI перед публикацией; репозиторий должен быть склонирован
с полной историей (fetch-depth: 0).
"""
import os, re, json, subprocess, datetime, html

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "журнал.html")

# ── разделы сайта: по изменённым файлам понимаем, что именно правили ────────
SECTIONS = [
    (r"упаковк|upak",                                   "Упаковка",            "📦"),
    (r"ддс|dds",                                        "Про деньги · ДДС",    "💰"),
    (r"калькулятор",                                    "Калькулятор налогов", "🧮"),
    (r"опиу|opiu",                                      "ОПиУ",                "📊"),
    (r"закуп|zakup|contractor|buyer",                   "Закупки",             "🛒"),
    (r"продаж|реализац|realizaciya|sales",              "Продажи",             "📈"),
    (r"себестоим|маржа|margin|fullcost|повышение_цен|цен", "Цены и маржа",     "🏷"),
    (r"производств|production",                         "Производство",        "🏭"),
    (r"склад|sklad",                                    "Склады",              "🧊"),
    (r"дз_кз|dz_kz|просрочк|оплат|oplat|bitrix|сальдо|saldo", "Долги и оплаты", "💳"),
    (r"налог|nalogi|zp|зарплат",                        "Налоги и зарплата",   "🧾"),
    (r"sku|ску",                                        "SKU и ассортимент",   "🔬"),
    (r"рычаг|lever|развитие|план",                      "Развитие",            "🚀"),
    (r"metrics",                                        "Метрики Пульса",      "🔒"),
    (r"журнал|zhurnal",                                 "Журнал изменений",    "🗂"),
    (r"^index\.html|^nav\.js|путеводитель",             "Главная страница",    "🏠"),
    (r"worker\.js|wrangler|_headers|_redirects",        "Движок сайта",        "⚙️"),
    (r"^\.github/|requirements|almaty\.py|iiko_export", "Автоматика и сборка", "🤖"),
]
BOT_AUTHORS = {"pulse-ci", "pulse-bot", "github-actions", "github-actions[bot]"}


def sections_of(files):
    """Какие разделы сайта затронул коммит."""
    out, seen = [], set()
    for f in files:
        low = f.lower()
        for rx, name, ic in SECTIONS:
            if name in seen:
                continue
            if re.search(rx, low):
                out.append((name, ic)); seen.add(name); break
    return out or [("Прочее", "🧭")]


def collect():
    """История из git: кто, когда, что написал и какие файлы тронул."""
    fmt = "%H%x1f%an%x1f%ad%x1f%s%x1e"
    env = dict(os.environ); env["TZ"] = "Asia/Almaty"
    raw = subprocess.run(
        ["git", "log", "--no-merges", "--date=format-local:%Y-%m-%d %H:%M",
         "--pretty=format:" + fmt, "--name-only"],
        cwd=HERE, capture_output=True, text=True, env=env, timeout=240).stdout

    entries = []
    for chunk in raw.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk.strip():
            continue
        head, _, rest = chunk.partition("\n")
        parts = head.split("\x1f")
        if len(parts) < 4:
            continue
        sha, author, when, subj = parts[0], parts[1], parts[2], parts[3]
        files = [l.strip() for l in rest.split("\n") if l.strip()]
        bot = author in BOT_AUTHORS or "[skip ci]" in subj
        subj = subj.replace("[skip ci]", "").strip(" ·—-")
        d, _, t = when.partition(" ")
        secs = sections_of(files)
        entries.append({
            "h": sha[:7], "a": author, "d": d, "t": t, "m": subj, "b": 1 if bot else 0,
            "s": [s[0] for s in secs], "i": [s[1] for s in secs], "n": len(files),
        })
    return merge(entries)


def merge(entries):
    """Одна правка часто уезжает несколькими коммитами подряд (по файлу на
    коммит). В журнале это должно выглядеть как одна строка: склеиваем
    соседние записи с тем же текстом, автором и датой."""
    out = []
    for e in entries:
        p = out[-1] if out else None
        if p and p["m"] == e["m"] and p["a"] == e["a"] and p["d"] == e["d"] and p["b"] == e["b"]:
            p["n"] += e["n"]
            p["t"] = e["t"]                      # лента идёт от новых к старым
            p["k"] = p.get("k", 1) + 1
            for name, ic in zip(e["s"], e["i"]):
                if name not in p["s"]:
                    p["s"].append(name); p["i"].append(ic)
            continue
        out.append(e)
    return out


# ── страница ────────────────────────────────────────────────────────────────
PAGE = r"""<!doctype html><html lang="ru"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Журнал изменений · Пульс</title>
<!-- Фуд Завод · © 2026. Все права защищены.
     Страница собирается из истории git — руками её править незачем,
     правки затрутся при следующей публикации (см. gen_zhurnal.py). -->
<script src="nav.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#070c17;--card:#0d1526;--line:#1c2740;--line2:#26334d;--ink:#eef3fb;--ink2:#c3d0e2;
  --mut:#7b8ca6;--dim:#546279;--gold:#e8c766;--grn:#4ade80;--cy:#22d3ee}
body{font-family:Inter,-apple-system,Segoe UI,Arial,sans-serif;color:var(--ink);min-height:100vh;
  -webkit-font-smoothing:antialiased;background:
   radial-gradient(900px 500px at 6% -8%,rgba(232,199,102,.13),transparent 60%),
   radial-gradient(800px 460px at 97% 0%,rgba(34,211,238,.10),transparent 60%),var(--bg);
  background-attachment:fixed}
.topbar{display:flex;align-items:center;gap:16px;padding:15px 30px;position:sticky;top:0;z-index:60;
  background:rgba(10,16,29,.85);backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
.backbtn{display:inline-flex;align-items:center;background:#16203a;color:var(--ink2);border:1px solid var(--line2);
  font-weight:700;font-size:12.5px;padding:7px 13px;border-radius:999px;text-decoration:none;transition:.18s;white-space:nowrap}
.backbtn:hover{background:var(--gold);color:#1a1205;border-color:var(--gold)}
.topbar h1{font-size:17px;font-weight:900;letter-spacing:-.3px}
.topbar p{font-size:11.5px;color:var(--mut);margin-top:2px}
.live{margin-left:auto;font-size:11.5px;color:#fde68a;background:rgba(232,199,102,.12);
  border:1px solid rgba(232,199,102,.4);border-radius:999px;padding:6px 13px;font-weight:700;white-space:nowrap}
.section{padding:22px 30px 56px;max-width:1180px;margin:0 auto}
.lead{font-size:12.5px;color:var(--mut);line-height:1.65;margin-bottom:16px;max-width:900px}
.lead b{color:var(--ink2)}

.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.k{border:1px solid var(--line2);border-radius:16px;padding:14px 16px;
  background:linear-gradient(160deg,rgba(255,255,255,.05),rgba(255,255,255,.015))}
.k .ic{font-size:16px}.k .l{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);font-weight:800;margin-top:6px}
.k .v{font-size:25px;font-weight:900;margin-top:2px;letter-spacing:-.5px}
.k .s{font-size:11.5px;color:var(--dim);margin-top:3px}

.tools{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.inp{background:#0e1728;border:1px solid var(--line2);border-radius:999px;color:var(--ink);
  font:inherit;font-size:12.5px;padding:8px 15px;min-width:230px;outline:none}
.inp:focus{border-color:var(--gold)}
.chip{background:#121c30;border:1px solid var(--line2);color:var(--ink2);border-radius:999px;
  padding:6px 13px;font-size:12px;font-weight:700;cursor:pointer;transition:.15s;white-space:nowrap}
.chip:hover{border-color:var(--gold);color:var(--ink)}
.chip.on{background:linear-gradient(135deg,var(--gold),#c79a28);color:#1a1205;border-color:var(--gold)}
.chip .n{opacity:.6;font-weight:800;margin-left:5px}
.sw{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--ink2);cursor:pointer;margin-left:auto}
.sw input{width:16px;height:16px;accent-color:#e8c766;cursor:pointer}

.day{margin-bottom:6px}
.day-h{display:flex;align-items:baseline;gap:11px;padding:16px 2px 8px;position:sticky;top:62px;
  background:linear-gradient(180deg,var(--bg) 62%,transparent);z-index:5}
.day-d{font-size:14px;font-weight:900;color:var(--gold);white-space:nowrap}
.day-w{font-size:11.5px;color:var(--dim)}
.day-l{flex:1;height:1px;background:var(--line)}
.day-n{font-size:11px;color:var(--mut);font-weight:700;white-space:nowrap}

.ev{display:grid;grid-template-columns:52px 1fr;gap:12px;padding:9px 13px;border:1px solid var(--line);
  border-radius:13px;background:rgba(255,255,255,.022);margin-bottom:7px;transition:.15s}
.ev:hover{border-color:var(--line2);background:rgba(255,255,255,.04)}
.ev .tm{font-size:12px;color:var(--dim);font-variant-numeric:tabular-nums;font-weight:700;padding-top:1px}
.ev .m{font-size:13.5px;line-height:1.45;color:var(--ink)}
.ev .meta{display:flex;gap:7px;flex-wrap:wrap;align-items:center;margin-top:5px}
.tag{font-size:10.5px;font-weight:800;border-radius:999px;padding:2.5px 9px;white-space:nowrap;
  background:rgba(34,211,238,.1);color:#7dd3fc;border:1px solid rgba(34,211,238,.28)}
.who{font-size:11px;color:var(--dim)}
.sha{font-family:ui-monospace,Menlo,monospace;font-size:10.5px;color:#4b5a72}

.bot{display:flex;align-items:center;gap:9px;padding:8px 13px;border:1px dashed var(--line2);
  border-radius:12px;background:rgba(255,255,255,.012);margin-bottom:7px;font-size:12px;color:var(--mut)}
.bot b{color:var(--ink2);font-weight:700}
.bot .x{margin-left:auto;font-size:11px;color:var(--dim);white-space:nowrap}

.empty{padding:40px;text-align:center;color:var(--dim);font-size:13px}
.more{display:block;width:100%;margin-top:14px;background:#121c30;border:1px solid var(--line2);
  color:var(--ink2);border-radius:13px;padding:11px;font:inherit;font-size:12.5px;font-weight:800;cursor:pointer}
.more:hover{border-color:var(--gold);color:var(--ink)}
.foot{text-align:center;color:var(--dim);font-size:11.5px;padding:26px 0 0}
@media(max-width:820px){.section{padding:18px 15px 44px}.kpi{grid-template-columns:repeat(2,1fr)}
  .topbar{padding:13px 15px}.sw{margin-left:0;width:100%}}
</style></head>
<body>
<div class="topbar">
  <a class="backbtn" href="index.html">← Пульс</a>
  <div><h1>🗂 Журнал изменений</h1><p>Что меняли на сайте «Пульс» — по дням</p></div>
  <div class="live" id="live"></div>
</div>
<div class="section">
  <div class="lead">
    Страница собирается сама из истории правок сайта — здесь видно, <b>что, когда и в каком разделе</b>
    поменялось. Правки людей показаны лентой; ежедневные автоматические обновления данных из iiko и 1С
    свёрнуты в одну строку за день, их можно развернуть галочкой справа.
  </div>
  <div class="kpi" id="kpi"></div>
  <div class="tools" id="tools"></div>
  <div id="feed"></div>
  <div class="foot">Система «Пульс» · © 2026 · собрано <span id="gen"></span></div>
</div>
<script>
var LOG = /*__DATA__*/null;
var GEN = "/*__GEN__*/";

var WD = ['воскресенье','понедельник','вторник','среда','четверг','пятница','суббота'];
var MN = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];
function esc(s){ return String(s).replace(/[&<>"]/g, function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
function plw(n,a,b,c){ n=Math.abs(n)%100; var m=n%10;
  if(n>10&&n<20) return c; if(m>1&&m<5) return b; if(m===1) return a; return c; }
function dparse(s){ var p=s.split('-'); return new Date(+p[0], +p[1]-1, +p[2]); }
function dru(s){ var d=dparse(s); return d.getDate()+' '+MN[d.getMonth()]+' '+d.getFullYear(); }
function daysAgo(s){ var t=new Date(); t.setHours(0,0,0,0); return Math.round((t-dparse(s))/86400000); }

var F = { q:'', sec:'', days:0, bots:false, limit:40 };

/* ── показатели ─────────────────────────────────────────────────────────── */
function drawKpi(){
  var hum = LOG.filter(function(e){ return !e.b; });
  var d30 = hum.filter(function(e){ return daysAgo(e.d)<=30; });
  var d7  = hum.filter(function(e){ return daysAgo(e.d)<=7; });
  var last = hum[0];
  var secs = {}; d30.forEach(function(e){ e.s.forEach(function(x){ secs[x]=(secs[x]||0)+1; }); });
  var top = Object.keys(secs).sort(function(a,b){ return secs[b]-secs[a]; })[0] || '—';
  var ago = last ? daysAgo(last.d) : null;
  var agoTxt = ago===0 ? 'сегодня' : ago===1 ? 'вчера' : ago+' '+plw(ago,'день','дня','дней')+' назад';
  var k = [
    {ic:'✍️', l:'Правок всего',      v:hum.length,  s:'с '+(hum.length?dru(hum[hum.length-1].d):'—')},
    {ic:'📆', l:'За 30 дней',        v:d30.length,  s:'за неделю — '+d7.length},
    {ic:'🎯', l:'Чаще всего меняли', v:top,         s:'за последние 30 дней', sm:1},
    {ic:'🕒', l:'Последняя правка',  v:agoTxt,      s:last?(last.t+' · '+last.s[0]):'—', sm:1}
  ];
  document.getElementById('kpi').innerHTML = k.map(function(x){
    return '<div class="k"><div class="ic">'+x.ic+'</div><div class="l">'+x.l+'</div>'
      +'<div class="v"'+(x.sm?' style="font-size:16px;line-height:1.3;margin-top:5px"':'')+'>'+esc(x.v)+'</div>'
      +'<div class="s">'+esc(x.s)+'</div></div>'; }).join('');
  document.getElementById('live').textContent = hum.length+' '+plw(hum.length,'правка','правки','правок')
    +' · '+LOG.length+' записей';
  document.getElementById('gen').textContent = GEN;
}

/* ── фильтры ────────────────────────────────────────────────────────────── */
function drawTools(){
  var cnt = {}, ic = {};
  LOG.forEach(function(e){ if(e.b) return;
    e.s.forEach(function(x,i){ cnt[x]=(cnt[x]||0)+1; ic[x]=e.i[i]; }); });
  var names = Object.keys(cnt).sort(function(a,b){ return cnt[b]-cnt[a]; });
  var per = [[0,'всё время'],[7,'неделя'],[30,'месяц'],[90,'3 месяца']];
  var h = '<input class="inp" id="q" placeholder="Поиск по тексту правки…" value="'+esc(F.q)+'">';
  h += per.map(function(p){ return '<button class="chip'+(F.days===p[0]?' on':'')+'" data-d="'+p[0]+'">'+p[1]+'</button>'; }).join('');
  h += '<button class="chip'+(F.sec===''?' on':'')+'" data-s="">все разделы<span class="n">'
     + LOG.filter(function(e){return !e.b;}).length+'</span></button>';
  h += names.map(function(n){ return '<button class="chip'+(F.sec===n?' on':'')+'" data-s="'+esc(n)+'">'
     + ic[n]+' '+esc(n)+'<span class="n">'+cnt[n]+'</span></button>'; }).join('');
  h += '<label class="sw"><input type="checkbox" id="bots"'+(F.bots?' checked':'')+'>'
     + 'показывать обновления данных</label>';
  var t = document.getElementById('tools'); t.innerHTML = h;
  t.querySelectorAll('[data-s]').forEach(function(b){
    b.onclick = function(){ F.sec = b.getAttribute('data-s'); F.limit=40; drawTools(); drawFeed(); }; });
  t.querySelectorAll('[data-d]').forEach(function(b){
    b.onclick = function(){ F.days = +b.getAttribute('data-d'); F.limit=40; drawTools(); drawFeed(); }; });
  var q = document.getElementById('q');
  q.oninput = function(){ F.q = q.value; F.limit=40; drawFeed(); };
  document.getElementById('bots').onchange = function(){ F.bots = this.checked; F.limit=40; drawFeed(); };
}

/* ── лента ──────────────────────────────────────────────────────────────── */
function match(e){
  if(F.days && daysAgo(e.d) > F.days) return false;
  if(F.sec && e.s.indexOf(F.sec) < 0) return false;
  if(F.q){ var q=F.q.toLowerCase();
    if((e.m+' '+e.s.join(' ')+' '+e.a).toLowerCase().indexOf(q) < 0) return false; }
  return true;
}
function drawFeed(){
  var hum = LOG.filter(function(e){ return !e.b && match(e); });
  var bots = LOG.filter(function(e){ return e.b && match(e); });
  var days = {}, order = [];
  function put(e, kind){
    if(!days[e.d]){ days[e.d] = {h:[], b:[]}; order.push(e.d); }
    days[e.d][kind].push(e);
  }
  hum.forEach(function(e){ put(e,'h'); });
  bots.forEach(function(e){ put(e,'b'); });
  order.sort().reverse();
  /* ограничиваем по дням, чтобы страница не росла бесконечно */
  var shown = order.slice(0, F.limit), rest = order.length - shown.length;
  if(!order.length){
    document.getElementById('feed').innerHTML = '<div class="empty">Ничего не нашлось — попробуйте снять фильтры.</div>';
    return;
  }
  var h = shown.map(function(d){
    var g = days[d], n = g.h.length;
    var s = '<div class="day"><div class="day-h"><span class="day-d">'+dru(d)+'</span>'
      + '<span class="day-w">'+WD[dparse(d).getDay()]+'</span><span class="day-l"></span>'
      + '<span class="day-n">'+(n ? n+' '+plw(n,'правка','правки','правок') : 'только данные')+'</span></div>';
    s += g.h.map(function(e){
      return '<div class="ev"><div class="tm">'+e.t+'</div><div><div class="m">'+esc(e.m)+'</div>'
        + '<div class="meta">'
        + e.s.map(function(x,i){ return '<span class="tag">'+e.i[i]+' '+esc(x)+'</span>'; }).join('')
        + '<span class="who">'+esc(e.a)+'</span><span class="sha">'+e.h+'</span>'
        + '<span class="who">'+e.n+' '+plw(e.n,'файл','файла','файлов')+'</span>'
        + '</div></div></div>'; }).join('');
    if(g.b.length){
      if(F.bots){
        s += g.b.map(function(e){
          return '<div class="bot"><span style="opacity:.7">'+e.t+'</span><b>'+esc(e.m)+'</b>'
            + '<span class="x">'+e.n+' '+plw(e.n,'файл','файла','файлов')+'</span></div>'; }).join('');
      } else {
        var what = {}; g.b.forEach(function(e){ what[e.m]=1; });
        var list = Object.keys(what).slice(0,6).join(' · ');
        s += '<div class="bot">🔄 <b>'+g.b.length+' '+plw(g.b.length,'обновление','обновления','обновлений')
          + ' данных</b> <span style="opacity:.8">'+esc(list)+'</span>'
          + '<span class="x">автоматически</span></div>';
      }
    }
    return s + '</div>';
  }).join('');
  if(rest > 0) h += '<button class="more" id="more">Показать ещё · осталось '+rest+' '
      + plw(rest,'день','дня','дней')+'</button>';
  document.getElementById('feed').innerHTML = h;
  var mb = document.getElementById('more');
  if(mb) mb.onclick = function(){ F.limit += 60; drawFeed(); };
}

drawKpi(); drawTools(); drawFeed();
</script>
</body></html>
"""


def build(entries):
    try:
        import almaty
        now = almaty.now()
    except Exception:  # вне репозитория — считаем алматинское время вручную
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5)))
    gen = now.strftime("%d.%m.%Y %H:%M")
    page = PAGE.replace("/*__DATA__*/null", json.dumps(entries, ensure_ascii=False))
    page = page.replace("/*__GEN__*/", gen)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    hum = sum(1 for e in entries if not e["b"])
    print("журнал.html собран: %d записей, из них правок людей %d" % (len(entries), hum))


if __name__ == "__main__":
    build(collect())
