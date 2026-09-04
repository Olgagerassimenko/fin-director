/* sku_analytics.js — интерактивная аналитика продаж по ассортименту.
   Работает на данных window.CTR (контрагент → позиции) и window.DS (итоги месяцев).
   Виды: «По товарам» (SKU) и «По контрагентам». Динамика к прошлому месяцу. */

(function () {
  'use strict';

  // Короткое имя контрагента для графиков и списков: «102-Яндекс лавка Абылай хана,62» → «102-Яндекс»
  function shortCtr(name) {
    name = String(name == null ? '' : name).trim();
    var m = name.match(/^\s*(\d+)\s*[-\s.]*/);
    var pref = m ? m[1] : '';
    var rest = (m ? name.slice(m[0].length) : name);
    var U = rest.toUpperCase(), brand;
    if (pref === '90') brand = 'Маймарт';
    else if (pref === '97') brand = 'ИП Ник и Co';
    else if (U.indexOf('ДФЗ') >= 0) brand = 'ДФЗ';
    else if (U.indexOf('ЯНДЕКС') >= 0) brand = 'Яндекс';
    else if (U.indexOf('KASPI') >= 0 || U.indexOf('КАСПИ') >= 0) brand = 'Kaspi';
    else if (U.indexOf('RP') >= 0 || U.indexOf('АЗС') >= 0) brand = 'RP АЗС';
    else if (U.indexOf('DSF') >= 0) brand = 'DSF';
    else if (U.indexOf('O-LIVE') >= 0 || U.indexOf('O-LIVE') >= 0) brand = 'O-live';
    else if (U.indexOf('БАЗИЛИК') >= 0) brand = 'Базилик';
    else if (U.indexOf('ГЛОВО') >= 0 || U.indexOf('GLOVO') >= 0) brand = 'Glovo';
    else if (U.indexOf('ПРИМАВЕРА') >= 0 || U.indexOf('АЛЬ-ФАРАБИ') >= 0 || U.indexOf('АЛЬ ФАРАБИ') >= 0) brand = 'Маймарт';
    else brand = rest.replace(/[():].*$/, '').split(/[ ,]/)[0] || rest;
    return (pref ? pref + '-' : '') + brand;
  }
  window.shortCtr = shortCtr;

  var CATC = {
    'Горячее': '#3b82f6', 'Выпечка': '#f97316', 'Сэндвичи': '#eab308',
    'Япония': '#a855f7', 'Десерты': '#ec4899', 'Завтраки': '#14b8a6',
    'Салаты': '#22c55e', 'Торты': '#f43f5e', 'Напитки': '#06b6d4',
    'Прочее': '#6366f1'
  };

  function skuCat(name) {
    var s = String(name).toUpperCase();
    if (/КОМПОТ|МОРС|ЛИМОНАД|СОК |ЧАЙ |КОФЕ|ВОДА|НАПИТ|СМУЗИ|АЙРАН|КВАС/.test(s)) return 'Напитки';
    if (/ТОРТ|БЕНТО/.test(s)) return 'Торты';
    if (/КИМПАБ|ОНИГИР|УДОН|РАМЕН|СУШИ|ГИОЗА|ПОКЕ|ЯПОН|ВОК |ЯННЕМ|ТОКПОК/.test(s)) return 'Япония';
    if (/БЛИН|СЫРНИК|КАША|ОМЛЕТ|ЗАВТРАК|ГРАНОЛА|ХЛОПЬ/.test(s)) return 'Завтраки';
    if (/САЛАТ|ШУБА|ВИНЕГРЕТ/.test(s)) return 'Салаты';
    if (/СЭНДВИЧ|СЕНДВИЧ|БУРГЕР|ХОТ-ДОГ|ХОТДОГ|ДОГ \(|ШАУРМА|ЧИАБАТТА|БАГЕТ С|ТОСТ/.test(s)) return 'Сэндвичи';
    if (/ЧИЗКЕЙК|ТИРАМИСУ|БРАУНИ|МЕДОВИК|НАПОЛЕОН|ПИРОЖН|ЭКЛЕР|ДЕСЕРТ|ЧИА |ПУДДИНГ|ПУДИНГ|МАФФИН|КУКИС|ОРЕШКИ|СИННАБОН|МОРОЖ|ШАРЛОТКА|ПАХЛАВА|ЗЕФИР|МАКАРУН/.test(s)) return 'Десерты';
    if (/СОСИСКА В ТЕСТЕ|ПИРОЖОК|ПИРОГ|САМСА|СЛОЙК|КРУАССАН|БУЛОЧК|ХЛЕБ|ЛАВАШ|БРЕЦЕЛЬ|СОЧНИК|ЛЕПЁШ|ЛЕПЕШ|ХАЧАПУРИ|ВЫПЕЧК|БАГЕТ|ШТРУДЕЛЬ|РУЛЕТ/.test(s)) return 'Выпечка';
    if (/П\/Ф|ПП\*|КУРИЦ|ГОВЯД|СВИН|ИНДЕЙК|КОТЛЕТ|ШНИЦЕЛЬ|МАНТЫ|ПЛОВ|ПАСТА|ПЕННЕ|ФУЗИЛЛИ|ЛАГМАН|ГУЙРУ|ЦОМЯН|ПЕЛЬМЕН|ВАРЕНИК|ТЕФТЕЛ|БРИЗОЛЬ|ЛЮЛЯ|БЕФСТРОГ|ЗРАЗ|СУП |БОРЩ|ТОМ ЯМ|КРЫЛЬЯ|ЗАПЕКАНК|ПЮРЕ|ГРЕЧК|РИС |РАГУ|ЖАРЕН|БИФШТЕКС|ГУЛЯШ|ТУЧИКЕН|ГАРНИР|ГОЛУБЦ|ФАРШ|ШАШЛЫК|СТЕЙК|НАГГЕТС|КАРТОФ/.test(s)) return 'Горячее';
    return 'Прочее';
  }

  // ── состояние ──────────────────────────────────────────────
  var MK = null;                 // текущий месяц
  var VIEW = 'sku';              // 'sku' | 'ctr'
  var SORT = { k: 'r', dir: -1 };
  var CATS_OFF = {};             // выключенные категории
  var OPEN_SKU = -1;             // раскрытая строка SKU
  var SHOW_ALL = false;          // показывать все позиции (иначе первые 150)
  var OPEN_CTR = {};             // раскрытые контрагенты
  var IDX = {};                  // кеш индексов по месяцам
  var TREND = null;              // {sku: {mk: rev}}
  var CH = null;                 // график в раскрытой строке

  function months() {
    return Object.keys(window.CTR || {}).filter(function (k) { return /^\d{4}-\d{2}$/.test(k); }).sort();
  }
  function prevKey(mk) {
    var all = months(), i = all.indexOf(mk);
    return i > 0 ? all[i - 1] : null;
  }
  function monthName(mk) {
    var d = (window.DS && window.DS[mk] && window.DS[mk].label) || mk;
    return String(d).replace(/\s*\(.*\)$/, '');
  }
  var MDAT = ['', 'январю', 'февралю', 'марту', 'апрелю', 'маю', 'июню',
    'июлю', 'августу', 'сентябрю', 'октябрю', 'ноябрю', 'декабрю'];
  function monthDat(mk) { return MDAT[+String(mk).slice(5, 7)] || monthName(mk).toLowerCase(); }
  var MPRE = ['', 'январе', 'феврале', 'марте', 'апреле', 'мае', 'июне',
    'июле', 'августе', 'сентябре', 'октябре', 'ноябре', 'декабре'];
  function monthPre(mk) { return MPRE[+String(mk).slice(5, 7)] || monthName(mk).toLowerCase(); }
  // сколько дней месяца отражено (для неполного месяца)
  function periodInfo(mk) {
    if (mk === 'year') return { partial: false, days: 1, dim: 1 };
    var lbl = (window.DS && window.DS[mk] && window.DS[mk].label) || '';
    var m = lbl.match(/\((\d+)\s*[–-]\s*(\d+)\)/);
    var y = +mk.slice(0, 4), mo = +mk.slice(5, 7);
    var dim = new Date(y, mo, 0).getDate();
    return m ? { partial: true, days: +m[2], dim: dim } : { partial: false, days: dim, dim: dim };
  }

  // Собирает годовой итог (CTR.year и категории/топ для DS.year) прямо в браузере
  window.ensureYear = function () {
    if (!window.CTR) return;
    if (!window.CTR.year) {
      var g = {};
      months().forEach(function (mk) {
        (window.CTR[mk] || []).forEach(function (c) {
          var x = g[c.num] || (g[c.num] = { num: c.num, name: c.name, rev: 0, points: 0, items: {} });
          x.rev += c.rev;
          x.points = Math.max(x.points, c.points || 0);
          (c.items || []).forEach(function (it) {
            var t = x.items[it.n] || (x.items[it.n] = { n: it.n, q: 0, r: 0 });
            t.q += it.q; t.r += it.r;
          });
        });
      });
      var tot = 0; Object.keys(g).forEach(function (k) { tot += g[k].rev; }); tot = tot || 1;
      var list = Object.keys(g).map(function (k) {
        var x = g[k];
        return {
          num: x.num, name: x.name, rev: Math.round(x.rev),
          pct: +(x.rev / tot * 100).toFixed(1), points: x.points,
          items: Object.keys(x.items).map(function (n) { return x.items[n]; })
            .sort(function (a, b) { return b.r - a.r; })
        };
      });
      list.sort(function (a, b) { return b.rev - a.rev; });
      window.CTR.year = list;
    }
    var D = window.DS && window.DS.year;
    if (D && !D.categories) {
      var ix = index('year'), cats = {};
      Object.keys(ix.sku).forEach(function (n) {
        var s = ix.sku[n]; cats[s.cat] = (cats[s.cat] || 0) + s.r;
      });
      D.categories = Object.keys(cats).sort(function (a, b) { return cats[b] - cats[a]; })
        .map(function (c) {
          return { cat: c, rev: Math.round(cats[c]), qty: 0, count: 0, pct: +(cats[c] / ix.total * 100).toFixed(1) };
        });
      D.top20 = Object.keys(ix.sku).map(function (n) { return ix.sku[n]; })
        .sort(function (a, b) { return b.r - a.r; }).slice(0, 20)
        .map(function (s) { return { name: s.n, cat: s.cat, rev: Math.round(s.r), qty: Math.round(s.q), magnum: false }; });
      D.sku_count = Object.keys(ix.sku).length;
    }
  };

  function index(mk) {
    if (IDX[mk]) return IDX[mk];
    var list = (window.CTR && window.CTR[mk]) || [];
    var sku = {}, total = 0;
    list.forEach(function (c) {
      (c.items || []).forEach(function (it) {
        var s = sku[it.n];
        if (!s) s = sku[it.n] = { n: it.n, cat: skuCat(it.n), q: 0, r: 0, buyers: [] };
        s.q += it.q; s.r += it.r; total += it.r;
        s.buyers.push({ name: c.name, q: it.q, r: it.r });
      });
    });
    Object.keys(sku).forEach(function (k) {
      sku[k].buyers.sort(function (a, b) { return b.r - a.r; });
    });
    IDX[mk] = { sku: sku, total: total, ctr: list };
    return IDX[mk];
  }

  function trend() {
    if (TREND) return TREND;
    TREND = {};
    months().forEach(function (mk) {
      ((window.CTR || {})[mk] || []).forEach(function (c) {
        (c.items || []).forEach(function (it) {
          (TREND[it.n] || (TREND[it.n] = {}))[mk] = (TREND[it.n][mk] || 0) + it.r;
        });
      });
    });
    return TREND;
  }

  // ── формат ─────────────────────────────────────────────────
  function sf(v) {
    var a = Math.abs(v);
    if (a >= 1e6) return (v / 1e6).toFixed(1) + ' млн';
    if (a >= 1e3) return Math.round(v / 1e3) + ' тыс';
    return Math.round(v).toLocaleString('ru');
  }
  function num(v) { return Math.round(v).toLocaleString('ru'); }
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function hl(s, q) {
    var e = esc(s); if (!q) return e;
    var i = String(s).toLowerCase().indexOf(q); if (i < 0) return e;
    return esc(String(s).slice(0, i)) + '<span class="ctr-hl">' + esc(String(s).slice(i, i + q.length)) +
      '</span>' + esc(String(s).slice(i + q.length));
  }
  function pill(cur, prev, isNew) {
    if (isNew) return '<span class="ctr-d new">NEW</span>';
    if (!prev) return '<span class="ctr-d flat">—</span>';
    var d = (cur - prev) / prev * 100;
    if (Math.abs(d) < 0.5) return '<span class="ctr-d flat">≈ 0%</span>';
    var up = d > 0;
    return '<span class="ctr-d ' + (up ? 'up' : 'down') + '">' + (up ? '▲' : '▼') + ' ' +
      Math.abs(d).toFixed(0) + '%</span>';
  }

  // ── герой-панель ───────────────────────────────────────────
  function hero() {
    var el = document.getElementById('dyn-hero'); if (!el) return;
    var cur = index(MK), pk = prevKey(MK);
    var pi = periodInfo(MK);
    var k = pi.partial ? pi.dim / pi.days : 1;           // пересчёт неполного месяца
    var curTotal = cur.total, curRate = curTotal * k;
    var prevTotal = pk ? index(pk).total : 0;
    var d = prevTotal ? (curRate - prevTotal) / prevTotal * 100 : 0;

    var grew = 0, fell = 0, nw = 0, lost = 0;
    if (pk) {
      var ps = index(pk).sku, cs = cur.sku;
      Object.keys(cs).forEach(function (n) {
        if (!ps[n]) { nw++; return; }
        var a = cs[n].r * k, b = ps[n].r;
        if (a > b * 1.02) grew++; else if (a < b * 0.98) fell++;
      });
      Object.keys(ps).forEach(function (n) { if (!cs[n]) lost++; });
    }
    var html = '<div class="dyn-hero">'
      + '<div><div class="dyn-lbl">' + esc(monthName(MK)) + (pi.partial ? ' · 1–' + pi.days : '') + '</div>'
      + '<div class="dyn-val">' + sf(curTotal) + '</div>'
      + '<div class="dyn-sub">' + Object.keys(cur.sku).length + ' позиций · ' + cur.ctr.length + ' контрагентов'
      + (pi.partial ? ' · в темпе на месяц ≈ <b style="color:#a78bfa">' + sf(curRate) + '</b>' : '') + '</div></div>';
    if (pk) {
      html += '<div class="dyn-delta ' + (d >= 0 ? 'up' : 'down') + '">' + (d >= 0 ? '▲' : '▼') + ' '
        + Math.abs(d).toFixed(1) + '%<span style="font-size:12px;font-weight:600;opacity:.75">к '
        + esc(monthDat(pk)) + '</span></div>';
      html += '<div class="dyn-chips">'
        + '<div class="chip up"><b>' + grew + '</b><span>выросли</span></div>'
        + '<div class="chip down"><b>' + fell + '</b><span>просели</span></div>'
        + '<div class="chip new"><b>' + nw + '</b><span>новых</span></div>'
        + '<div class="chip lost"><b>' + lost + '</b><span>пропало</span></div>'
        + '</div>';
    }
    html += '</div>';
    el.innerHTML = html;
  }

  // ── фильтр категорий ───────────────────────────────────────
  function catFilter() {
    var el = document.getElementById('cat-filter'); if (!el) return;
    if (VIEW !== 'sku') { el.innerHTML = ''; return; }
    var cur = index(MK), agg = {};
    Object.keys(cur.sku).forEach(function (n) {
      var s = cur.sku[n];
      (agg[s.cat] || (agg[s.cat] = { r: 0, c: 0 }));
      agg[s.cat].r += s.r; agg[s.cat].c++;
    });
    var arr = Object.keys(agg).map(function (c) { return { c: c, r: agg[c].r, n: agg[c].c }; })
      .sort(function (a, b) { return b.r - a.r; });
    el.innerHTML = arr.map(function (x) {
      var on = !CATS_OFF[x.c];
      return '<div class="cat-chip' + (on ? ' on' : '') + '" onclick="skuToggleCat(\'' + esc(x.c) + '\')">'
        + '<i style="background:' + (CATC[x.c] || '#6366f1') + '"></i>' + esc(x.c)
        + ' <b>' + sf(x.r) + '</b></div>';
    }).join('');
  }

  // ── таблица по товарам ─────────────────────────────────────
  function th(k, label, align) {
    var a = SORT.k === k ? '<span class="ar">' + (SORT.dir < 0 ? '▼' : '▲') + '</span>' : '';
    return '<th onclick="skuSort(\'' + k + '\')"' + (align ? ' style="text-align:' + align + '"' : '') + '>' + label + a + '</th>';
  }

  function drawSkuView(q) {
    var cur = index(MK), pk = prevKey(MK), prev = pk ? index(pk).sku : {};
    var pi = periodInfo(MK), k = pi.partial ? pi.dim / pi.days : 1;
    var rows = Object.keys(cur.sku).map(function (n) { return cur.sku[n]; })
      .filter(function (s) {
        if (CATS_OFF[s.cat]) return false;
        if (!q) return true;
        if (s.n.toLowerCase().indexOf(q) >= 0) return true;
        return s.buyers.some(function (b) { return b.name.toLowerCase().indexOf(q) >= 0; });
      });
    rows.forEach(function (s) {
      var p = prev[s.n];
      s._prev = p ? p.r : 0;
      s._new = !p;
      s._d = p ? (s.r * k - p.r) : 0;
    });
    var kk = SORT.k, dir = SORT.dir;
    rows.sort(function (a, b) {
      var x = kk === 'n' ? a.n.localeCompare(b.n) : kk === 'cat' ? a.cat.localeCompare(b.cat)
        : kk === 'd' ? (a._d - b._d) : (a[kk] - b[kk]);
      return dir * x;
    });
    var shown = rows.reduce(function (s, x) { return s + x.r; }, 0);
    var max = rows.length ? Math.max.apply(null, rows.map(function (r) { return r.r; })) : 1;
    // на годовой вкладке позиций больше полутора тысяч — рисуем частями, иначе страница виснет
    var totalRows = rows.length, LIM = 150, cut = false;
    if (!SHOW_ALL && totalRows > LIM) { rows = rows.slice(0, LIM); cut = true; }

    var h = '<div class="sku-wrap"><table class="sku-tbl"><thead><tr>'
      + '<th style="width:34px">#</th>'
      + th('n', 'Позиция') + th('cat', 'Категория')
      + th('q', 'Кол-во', 'right') + th('r', 'Выручка', 'right')
      + '<th style="text-align:right">Доля</th>'
      + th('d', 'Динамика', 'right')
      + '<th style="text-align:right">Покупатели</th>'
      + '</tr></thead><tbody>';
    if (!rows.length) h += '<tr><td colspan="8" class="ctr-empty">Ничего не найдено</td></tr>';
    rows.forEach(function (s, i) {
      var open = OPEN_SKU === i;
      h += '<tr class="' + (open ? 'open' : '') + '" onclick="skuToggle(' + i + ')">'
        + '<td class="sku-rank">' + (i + 1) + '</td>'
        + '<td class="sku-name">' + hl(s.n, q)
        + (s._new ? '<span class="tag new">NEW</span>' : '')
        + '<div class="mini"><i style="width:' + Math.max(2, Math.round(s.r / max * 100)) + '%;background:'
        + (CATC[s.cat] || '#6366f1') + '"></i></div></td>'
        + '<td><span class="cat-tag"><i style="background:' + (CATC[s.cat] || '#6366f1') + '"></i>' + esc(s.cat) + '</span></td>'
        + '<td class="sku-num">' + num(s.q) + '</td>'
        + '<td class="sku-num sku-rev">' + num(s.r) + '</td>'
        + '<td class="sku-num" style="color:#64748b">' + (cur.total ? (s.r / cur.total * 100).toFixed(1) : 0) + '%</td>'
        + '<td class="sku-num">' + pill(s.r * k, s._prev, s._new) + '</td>'
        + '<td class="sku-num" style="color:#94a3b8">' + s.buyers.length + '</td></tr>';
      if (open) {
        h += '<tr class="sku-det"><td colspan="8"><div class="inner" id="sku-det-inner">'
          + '<div style="display:grid;grid-template-columns:1fr 340px;gap:20px;align-items:start">'
          + '<div><div class="dt">Кто покупал — ' + esc(monthName(MK)) + '</div><table class="buy-tbl">'
          + s.buyers.map(function (b) {
            return '<tr><td>' + hl(b.name, q) + '<div class="buy-bar"><i style="width:'
              + Math.max(2, Math.round(b.r / s.r * 100)) + '%"></i></div></td>'
              + '<td style="text-align:right;color:#94a3b8;white-space:nowrap">' + num(b.q) + ' шт</td>'
              + '<td style="text-align:right;font-weight:700;color:#a78bfa;white-space:nowrap">' + num(b.r) + '</td>'
              + '<td style="text-align:right;color:#64748b">' + (b.r / s.r * 100).toFixed(0) + '%</td></tr>';
          }).join('')
          + '</table></div>'
          + '<div><div class="dt">Динамика по месяцам</div><canvas id="sku-chart" height="190"></canvas></div>'
          + '</div></div></td></tr>';
      }
    });
    h += '</tbody></table>';
    if (cut) {
      h += '<div style="padding:14px;text-align:center;border-top:1px solid #1e293b;color:#94a3b8;font-size:13px">'
        + 'Показаны первые <b style="color:#e2e8f0">' + LIM + '</b> из <b style="color:#e2e8f0">' + totalRows
        + '</b> позиций &nbsp;·&nbsp; уточните поиском или '
        + '<a href="javascript:void(0)" onclick="skuShowAll(true)" style="color:#818cf8;text-decoration:none;font-weight:700">показать все</a></div>';
    } else if (SHOW_ALL && totalRows > 150) {
      h += '<div style="padding:14px;text-align:center;border-top:1px solid #1e293b;color:#94a3b8;font-size:13px">'
        + 'Показаны все <b style="color:#e2e8f0">' + totalRows + '</b> позиций &nbsp;·&nbsp; '
        + '<a href="javascript:void(0)" onclick="skuShowAll(false)" style="color:#818cf8;text-decoration:none;font-weight:700">свернуть до 150</a></div>';
    }
    h += '</div>';
    document.getElementById('ctr-list').innerHTML = h;

    var st = document.getElementById('ctr-stat');
    if (st) st.innerHTML = '<b style="color:#e2e8f0">' + rows.length + '</b> позиций на <b style="color:#a78bfa">'
      + sf(shown) + '</b>' + (q ? ' (найдено)' : '');

    if (OPEN_SKU >= 0 && rows[OPEN_SKU]) drawSkuChart(rows[OPEN_SKU].n);
  }

  function drawSkuChart(name) {
    var cv = document.getElementById('sku-chart'); if (!cv || !window.Chart) return;
    if (CH) { CH.destroy(); CH = null; }
    var t = trend()[name] || {};
    var ms = months();
    var labels = ms.map(function (m) { return monthName(m).slice(0, 3); });
    var data = ms.map(function (m) { return (t[m] || 0) / 1e6; });
    CH = new Chart(cv, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: ms.map(function (m) { return m === MK ? '#a855f7' : 'rgba(124,58,237,.35)'; }),
          borderRadius: 5
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          datalabels: {
            anchor: 'end', align: 'top', color: '#c4b5fd',
            font: { size: 10, weight: 700 },
            formatter: function (v) { return v ? v.toFixed(1) : ''; }
          }
        },
        scales: {
          x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
          y: { display: false, grace: '18%' }
        }
      }
    });
  }

  // ── список по контрагентам ─────────────────────────────────
  function drawCtrView(q) {
    var cur = index(MK), pk = prevKey(MK);
    var pmap = {};
    if (pk) ((window.CTR || {})[pk] || []).forEach(function (c) { pmap[c.num] = c; });
    var pi = periodInfo(MK), k = pi.partial ? pi.dim / pi.days : 1;
    var data = cur.ctr, max = data.length ? data[0].rev : 1;
    var h = '', nc = 0, sum = 0;
    data.forEach(function (c, i) {
      var items = c.items, nameHit = c.name.toLowerCase().indexOf(q) >= 0;
      if (q) {
        var f = c.items.filter(function (it) { return it.n.toLowerCase().indexOf(q) >= 0; });
        if (f.length) items = f; else if (!nameHit) return;
      }
      nc++;
      var s2 = q ? items.reduce(function (a, b) { return a + b.r; }, 0) : c.rev;
      sum += s2;
      var p = pmap[c.num], prevRev = p ? p.rev : 0;
      var open = q ? true : !!OPEN_CTR[i];
      var pit = {};
      if (p) p.items.forEach(function (it) { pit[it.n] = it.r; });
      h += '<div class="ctr-acc' + (open ? ' open' : '') + '">'
        + '<div class="ctr-head" onclick="ctrToggle(' + i + ')">'
        + '<span class="ctr-arrow">▶</span>'
        + '<span class="ctr-name" title="' + esc(c.name) + '">' + hl(shortCtr(c.name), q) + '</span>'
        + (c.points > 1 ? '<span class="ctr-pts">' + c.points + ' точек</span>' : '')
        + (prevRev ? '<span class="ctr-prev">было ' + sf(prevRev) + '</span>' : '')
        + '<span class="ctr-rev">' + sf(s2) + '</span>'
        + pill(c.rev * k, prevRev, !p)
        + '<span class="ctr-pct">' + c.pct + '%</span></div>'
        + '<div class="ctr-bar"><i style="width:' + Math.max(1, Math.round(c.rev / max * 100)) + '%"></i></div>'
        + '<div class="ctr-body"><table class="ctr-tbl"><thead><tr>'
        + '<th>Позиция</th><th style="text-align:right">Кол-во</th>'
        + '<th style="text-align:right">Сумма</th><th style="text-align:right">Было</th>'
        + '<th style="text-align:right">Динамика</th></tr></thead><tbody>'
        + items.map(function (it) {
          var pr = pit[it.n] || 0;
          return '<tr><td>' + hl(it.n, q) + (pr ? '' : '<span class="tag new">NEW</span>') + '</td>'
            + '<td style="text-align:right;color:#94a3b8">' + num(it.q) + '</td>'
            + '<td style="text-align:right;font-weight:700;color:#a78bfa">' + num(it.r) + '</td>'
            + '<td style="text-align:right;color:#64748b">' + (pr ? num(pr) : '—') + '</td>'
            + '<td style="text-align:right">' + pill(it.r * k, pr, !pr) + '</td></tr>';
        }).join('')
        + '</tbody></table></div></div>';
    });
    document.getElementById('ctr-list').innerHTML = h || '<div class="ctr-empty">Ничего не найдено</div>';
    var st = document.getElementById('ctr-stat');
    if (st) st.innerHTML = '<b style="color:#e2e8f0">' + nc + '</b> контрагентов на <b style="color:#a78bfa">' + sf(sum) + '</b>';
  }

  // ── публичные ──────────────────────────────────────────────
  var MGEN = ['', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];

  window.renderCtrItems = function (mk) {
    MK = mk; OPEN_SKU = -1; OPEN_CTR = {}; CATS_OFF = {}; SHOW_ALL = false;
    if (CH) { CH.destroy(); CH = null; }
    var s = document.getElementById('ctr-search'); if (s) s.value = '';
    // актуализируем плашку о неполном месяце
    var w = document.getElementById('warn');
    if (w) {
      var pi = periodInfo(mk);
      if (pi.partial) {
        w.textContent = '⚠ Неполный месяц: данные за 1–' + pi.days + ' ' +
          (MGEN[+String(mk).slice(5, 7)] || '') + ' ' + String(mk).slice(0, 4);
        w.style.display = 'block';
      } else { w.style.display = 'none'; }
    }
    // водопад сравнивает два месяца — на годовой вкладке он не нужен
    var wfs = document.getElementById('wf-section');
    if (wfs) wfs.style.display = (mk === 'year') ? 'none' : '';
    window.drawCtr();
    if (mk !== 'year' && window.wfInit) window.wfInit();
    drawYearByCtr();
  };

  window.drawCtr = function () {
    var sec = document.getElementById('ctr-section');
    var list = document.getElementById('ctr-list');
    if (!sec || !list || !MK) return;
    if (!((window.CTR || {})[MK] || []).length) { sec.style.display = 'none'; return; }
    sec.style.display = '';
    var box = document.getElementById('ctr-search');
    var q = ((box && box.value) || '').trim().toLowerCase();
    hero(); catFilter(); renderFacts();
    if (VIEW === 'sku') drawSkuView(q); else drawCtrView(q);
  };

  // ── ИНТЕРЕСНЫЕ ФАКТЫ ───────────────────────────────────────
  function fact(icon, text) {
    return '<div class="fact"><span class="fi">' + icon + '</span><span>' + text + '</span></div>';
  }
  function renderFacts() {
    var el = document.getElementById('facts'); if (!el || !MK) return;
    var cur = index(MK), pk = prevKey(MK);
    var pi = periodInfo(MK), k = pi.partial ? pi.dim / pi.days : 1;
    var out = [];

    // 1) топ-категория
    var cats = {};
    Object.keys(cur.sku).forEach(function (n) { var s = cur.sku[n]; cats[s.cat] = (cats[s.cat] || 0) + s.r; });
    var cl = Object.keys(cats).sort(function (a, b) { return cats[b] - cats[a]; });
    if (cl.length) {
      out.push(fact('🥇', '<b>' + esc(cl[0]) + '</b> — главная категория: ' +
        '<b class="g">' + sf(cats[cl[0]]) + '</b> (' + (cats[cl[0]] / cur.total * 100).toFixed(0) + '% выручки)'));
    }
    // 2) ядро ассортимента (Парето 80%)
    var arr = Object.keys(cur.sku).map(function (n) { return cur.sku[n].r; }).sort(function (a, b) { return b - a; });
    var acc = 0, core = 0;
    for (var i = 0; i < arr.length; i++) { acc += arr[i]; core++; if (acc >= cur.total * 0.8) break; }
    out.push(fact('🎯', '<b class="g">' + core + '</b> позиций из <b>' + arr.length +
      '</b> дают 80% выручки — это <b>' + (core / arr.length * 100).toFixed(0) + '%</b> ассортимента' +
      ' <button onclick="exportSkuPareto()" title="Скачать Excel за ' + esc(monthName(MK)) + ': лист «Срочно сделать» — список дел с приоритетами (считается по последнему закрытому месяцу), лист «Топ 80%» (' + core + ' позиций) и лист «Весь ассортимент» (' + arr.length + '). В таблицах есть количество, цена за единицу и число покупателей. Обновляется по выбранному месяцу." style="margin-left:8px;padding:4px 11px;border:none;border-radius:8px;background:linear-gradient(135deg,#10b981,#059669);color:#fff;font-size:11px;font-weight:800;cursor:pointer;box-shadow:0 3px 10px -3px rgba(16,185,129,.7);vertical-align:middle;white-space:nowrap">📊 Скачать Excel</button>'));
    // 3) лидер месяца
    var top = Object.keys(cur.sku).map(function (n) { return cur.sku[n]; })
      .sort(function (a, b) { return b.r - a.r; })[0];
    if (top) out.push(fact('👑', 'Лидер продаж: <b>' + esc(top.n) + '</b> — <b class="g">' + sf(top.r) + '</b>'));
    // 4) концентрация клиентов
    var c3 = cur.ctr.slice(0, 3).reduce(function (s, c) { return s + c.rev; }, 0);
    out.push(fact('⚠️', 'Топ-3 покупателя дают <b class="r">' + (c3 / cur.total * 100).toFixed(0) +
      '%</b> выручки — высокая зависимость'));
    // 5) рост / падение к прошлому месяцу
    if (pk) {
      var ps = index(pk).sku, moves = [];
      Object.keys(cur.sku).forEach(function (n) {
        if (!ps[n]) return;
        moves.push({ n: n, d: cur.sku[n].r * k - ps[n].r });
      });
      moves.sort(function (a, b) { return b.d - a.d; });
      if (moves.length) {
        var up = moves[0], dn = moves[moves.length - 1];
        if (up && up.d > 0) out.push(fact('📈', 'Сильнее всех вырос <b>' + esc(up.n) + '</b>: <b class="g">+' + sf(up.d) + '</b>'));
        if (dn && dn.d < 0) out.push(fact('📉', 'Сильнее всех просел <b>' + esc(dn.n) + '</b>: <b class="r">' + sf(dn.d) + '</b>'));
      }
      var nw = 0, lost = 0;
      Object.keys(cur.sku).forEach(function (n) { if (!ps[n]) nw++; });
      Object.keys(ps).forEach(function (n) { if (!cur.sku[n]) lost++; });
      out.push(fact('🔄', 'Появилось <b class="g">' + nw + '</b> новых позиций, перестали продаваться <b class="r">' + lost + '</b>'));
    }
    el.innerHTML = out.join('');
  }

  // ── ЭКСПОРT SKU В EXCEL (Парето, по выбранному месяцу) ──────
  function exportSkuPareto() {
    if (!MK) { alert('Выберите месяц'); return; }
    if (typeof ExcelJS === 'undefined') { alert('Модуль Excel ещё грузится — повторите через секунду'); return; }
    var cur = index(MK), pk = prevKey(MK), prev = pk ? index(pk).sku : {};
    var pi = periodInfo(MK);
    /* Лист «Срочно сделать» считаем ТОЛЬКО по закрытому месяцу. Если выбран
       неполный период (например «Сентябрь (1–3)»), половина позиций просто
       ещё не успела отгрузиться — и любой вывод про «пропала из продаж» или
       «просела» будет ложной тревогой. Поэтому берём последний закрытый. */
    var AK = (pi.partial && pk) ? pk : MK;

    var list = Object.keys(cur.sku).map(function (n) {
      var s = cur.sku[n], b = s.buyers || [];
      return {
        name: s.n, cat: s.cat, rev: Math.round(s.r),
        qty: Math.round((s.q || 0) * 100) / 100,
        price: s.q ? Math.round(s.r / s.q) : null,
        nb: b.length, topShare: (b.length && s.r) ? b[0].r / s.r : 0,
        topName: b.length ? b[0].name : ''
      };
    }).filter(function (x) { return x.rev > 0; });
    list.sort(function (a, b) { return b.rev - a.rev; });
    var total = list.reduce(function (a, x) { return a + x.rev; }, 0) || 1, acc = 0, top = [];
    for (var i = 0; i < list.length; i++) { acc += list[i].rev; top.push(list[i]); if (acc >= total * 0.8) break; }
    var mn = (window.DS && window.DS[MK] && window.DS[MK].label) || MK;
    var wb = new ExcelJS.Workbook(); wb.creator = 'Пульс · Мастерская Сегодня';

    /* ── Лист 1: «Срочно сделать» — не таблица, а список дел ── */
    function sheetTodo() {
      var acur = index(AK), apk = prevKey(AK), prev = apk ? index(apk).sku : {};
      var alist = Object.keys(acur.sku).map(function (n) {
        var s = acur.sku[n], b = s.buyers || [];
        return {
          name: s.n, cat: s.cat, rev: Math.round(s.r),
          qty: Math.round((s.q || 0) * 100) / 100,
          nb: b.length, topShare: (b.length && s.r) ? b[0].r / s.r : 0,
          topName: b.length ? b[0].name : ''
        };
      }).filter(function (x) { return x.rev > 0; });
      alist.sort(function (a, b) { return b.rev - a.rev; });
      var atotal = alist.reduce(function (a, x) { return a + x.rev; }, 0) || 1, aacc = 0, atop = [];
      for (var ai = 0; ai < alist.length; ai++) { aacc += alist[ai].rev; atop.push(alist[ai]); if (aacc >= atotal * 0.8) break; }
      var amn = (window.DS && window.DS[AK] && window.DS[AK].label) || AK;
      function fx(v, d) { return String(v.toFixed(d)).replace('.', ','); }
      var ws = wb.addWorksheet('Срочно сделать', { views: [{ state: 'frozen', ySplit: 2 }] });
      ws.columns = [
        { header: 'Приоритет', key: 'p', width: 13 },
        { header: 'Что сделать', key: 'a', width: 44 },
        { header: 'Позиция / кто', key: 'o', width: 46 },
        { header: 'Сумма, ₸', key: 'v', width: 14, style: { numFmt: '#,##0' } },
        { header: 'Кол-во', key: 'q', width: 11, style: { numFmt: '#,##0.##' } },
        { header: 'Почему это важно', key: 'w', width: 56 },
        { header: 'Статус', key: 's', width: 14 }
      ];
      // строка-заголовок периода над шапкой
      ws.spliceRows(1, 0, ['Срочно сделать по итогам месяца: ' + amn +
        (AK !== MK ? '   (выбран неполный период ' + mn + ' — выводы считаем по последнему закрытому месяцу, иначе половина позиций выглядела бы «пропавшей»)' : '')]);
      ws.mergeCells('A1:G1');
      var t = ws.getRow(1); t.height = 26;
      t.getCell(1).font = { bold: true, size: 13, color: { argb: 'FF064E3B' } };
      t.getCell(1).alignment = { vertical: 'middle' };
      var hdr = ws.getRow(2); hdr.height = 24;
      hdr.eachCell(function (c) {
        c.font = { bold: true, color: { argb: 'FFFFFFFF' }, size: 11 };
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFB45309' } };
        c.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true };
      });
      var n = 0, bn = 0;
      function block(title) {
        bn++;
        var r = ws.addRow([bn + '. ' + title]);
        ws.mergeCells(r.number, 1, r.number, 7);
        r.height = 20;
        r.getCell(1).font = { bold: true, size: 11, color: { argb: 'FF1F2937' } };
        r.getCell(1).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF3F4F6' } };
        r.getCell(1).alignment = { vertical: 'middle' };
      }
      function item(pr, a, o, v, q, w) {
        n++;
        var r = ws.addRow({ p: pr, a: a, o: o, v: (v === null ? '' : v), q: (q === null ? '' : q), w: w, s: '' });
        r.height = 16.5;
        r.alignment = { vertical: 'middle', wrapText: true };
        r.eachCell(function (c) { c.border = { bottom: { style: 'hair', color: { argb: 'FFE5E7EB' } } }; });
        r.getCell('p').alignment = { horizontal: 'center', vertical: 'middle' };
        r.getCell('p').font = { bold: true, color: { argb: pr.indexOf('Срочно') >= 0 ? 'FFB91C1C' : (pr.indexOf('Важно') >= 0 ? 'FFB45309' : 'FF065F46') } };
        r.getCell('v').font = { bold: true, color: { argb: 'FF065F46' } };
        r.getCell('s').fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFFFFBEB' } };
        r.getCell('s').dataValidation = {
          type: 'list', allowBlank: true, formulae: ['"Сделано,В работе,Отложено"']
        };
      }

      // 1) пропали из продаж
      var gone = [];
      Object.keys(prev).forEach(function (nm) {
        if (acur.sku[nm]) return;
        var s = prev[nm]; if (s.r < atotal * 0.0005) return;
        gone.push({ n: s.n, r: Math.round(s.r), q: Math.round((s.q || 0) * 100) / 100 });
      });
      gone.sort(function (a, b) { return b.r - a.r; });
      if (gone.length) {
        block('Пропали из продаж — были в ' + (apk ? monthPre(apk) : 'прошлом месяце') + ', в ' + monthPre(AK) + ' продаж нет (' + gone.length + ')');
        gone.slice(0, 12).forEach(function (x) {
          item('🔴 Срочно', 'Выяснить, почему продажи прекратились: снята с производства, нет сырья или ушёл покупатель',
            x.n, x.r, x.q, 'Месяцем раньше позиция принесла ' + num(x.r) + ' ₸. В ' + monthPre(AK) + ' — ноль.');
        });
      }

      // 2) резко просели к прошлому месяцу
      var drops = [];
      alist.forEach(function (x) {
        var p = prev[x.name]; if (!p || p.r < atotal * 0.0008) return;
        var d = x.rev - p.r;
        if (d >= 0) return;
        if (Math.abs(d) < p.r * 0.25) return;   // падение меньше четверти — не срочно
        drops.push({ n: x.name, d: Math.round(d), pct: d / p.r * 100, rev: x.rev, q: x.qty });
      });
      drops.sort(function (a, b) { return a.d - b.d; });
      if (drops.length) {
        block('Резко просели — падение больше четверти к ' + (apk ? monthDat(apk) : 'прошлому месяцу') + ' (' + drops.length + ')');
        drops.slice(0, 12).forEach(function (x) {
          item('🔴 Срочно', 'Разобрать причину падения с отделом продаж и производством',
            x.n, x.rev, x.q, 'Минус ' + num(Math.abs(x.d)) + ' ₸ к ' + (apk ? monthDat(apk) : 'прошлому месяцу') + ' — падение на ' + Math.abs(x.pct).toFixed(0) + '%.');
        });
      }

      // 3) держится на одном покупателе
      var solo = alist.filter(function (x) { return x.rev >= atotal * 0.003 && x.topShare >= 0.8 && x.nb <= 3; });
      if (solo.length) {
        block('Держатся на одном покупателе — уйдёт клиент, уйдёт вся позиция (' + solo.length + ')');
        solo.slice(0, 12).forEach(function (x) {
          item('🟠 Важно', 'Найти второго покупателя на позицию или заложить риск в план',
            x.name, x.rev, x.qty,
            'Один покупатель даёт ' + (x.topShare * 100).toFixed(0) + '% продаж позиции: ' + x.topName + '. Всего покупателей: ' + x.nb + '.');
        });
      }

      // 4) хвост ассортимента
      var tail = alist.slice(atop.length).slice().sort(function (a, b) { return a.rev - b.rev; });
      var cut = [], s = 0;
      for (var ti = 0; ti < tail.length; ti++) {
        if (s + tail[ti].rev > atotal * 0.01) break;
        s += tail[ti].rev; cut.push(tail[ti]);
      }
      if (cut.length) {
        block('Хвост ассортимента — ' + cut.length + ' позиций дают вместе ' + fx(s / atotal * 100, 1) + '% выручки (' + num(s) + ' ₸)');
        item('🟠 Важно', 'Пересмотреть весь хвост: вывести из ассортимента или объединить в одну позицию',
          cut.length + ' позиций суммарно', Math.round(s), null,
          'Каждая позиция — это отдельная закупка, техкарта, остаток и место на складе. Отдача — ' + fx(s / atotal * 100, 1) + '% выручки.');
        cut.slice(-15).reverse().forEach(function (x) {
          item('🟠 Важно', 'Решить: оставляем или выводим', x.name, x.rev, x.qty,
            'Доля в выручке — ' + fx(x.rev / atotal * 100, 2) + '%. Покупателей: ' + x.nb + '.');
        });
      }

      // 6) зависимость от покупателей
      var c3 = acur.ctr.slice(0, 3).reduce(function (a, c) { return a + c.rev; }, 0);
      if (acur.total && c3 / acur.total >= 0.5) {
        block('Зависимость от покупателей');
        item('🟠 Важно', 'Работать над расширением базы покупателей',
          acur.ctr.slice(0, 3).map(function (c) { return c.name; }).join(', '), Math.round(c3), null,
          'Топ-3 покупателя дают ' + (c3 / acur.total * 100).toFixed(0) + '% всей выручки месяца.');
      }

      // 7) что защищать
      block('Держать на контроле — на этих позициях стоит выручка');
      atop.slice(0, 5).forEach(function (x) {
        item('🟢 Контроль', 'Не допускать перебоев: сырьё, смена, упаковка',
          x.name, x.rev, x.qty,
          'Позиция даёт ' + fx(x.rev / atotal * 100, 1) + '% выручки месяца. Простой сразу видно в деньгах.');
      });

      if (!n) {
        item('🟢 Контроль', 'Срочных вопросов по ассортименту не найдено', '—', null, null,
          'Ни одна позиция не пропала из продаж и не просела больше чем на четверть.');
      }
      ws.autoFilter = 'A2:G2';
    }
    sheetTodo();

    /* ── Листы 2–3: ABC по выручке ── */
    function build(name, rows) {
      var ws = wb.addWorksheet(name, { views: [{ state: 'frozen', ySplit: 1 }] });
      ws.columns = [
        { header: '№', key: 'i', width: 6 },
        { header: 'Позиция', key: 'name', width: 50 },
        { header: 'Категория', key: 'cat', width: 18 },
        { header: 'Кол-во', key: 'qty', width: 12, style: { numFmt: '#,##0.##' } },
        { header: 'Выручка, ₸', key: 'rev', width: 16, style: { numFmt: '#,##0' } },
        { header: 'Цена за ед., ₸', key: 'price', width: 14, style: { numFmt: '#,##0' } },
        { header: 'Доля, %', key: 'share', width: 11, style: { numFmt: '0.0"%"' } },
        { header: 'Накоплено, %', key: 'cum', width: 14, style: { numFmt: '0.0"%"' } },
        { header: 'Покупателей', key: 'nb', width: 13 }
      ];
      var cc = 0;
      rows.forEach(function (x, idx) {
        var sh = x.rev / total * 100; cc += sh;
        ws.addRow({
          i: idx + 1, name: x.name, cat: x.cat, qty: x.qty, rev: x.rev,
          price: (x.price === null ? '' : x.price),
          share: +sh.toFixed(1), cum: +cc.toFixed(1), nb: x.nb
        });
      });
      var hdr = ws.getRow(1); hdr.height = 24;
      hdr.eachCell(function (c) {
        c.font = { bold: true, color: { argb: 'FFFFFFFF' }, size: 11 };
        c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF059669' } };
        c.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true };
        c.border = { bottom: { style: 'medium', color: { argb: 'FF047857' } } };
      });
      // единица измерения у каждой позиции своя — предупреждаем в примечании
      try {
        hdr.getCell('qty').note = 'Количество в единицах самой позиции: где-то штуки, где-то килограммы или порции — единица зашита в названии.';
      } catch (e) { }
      for (var r = 2; r <= rows.length + 1; r++) {
        var row = ws.getRow(r); row.height = 16.5;
        row.eachCell(function (c) {
          c.border = { bottom: { style: 'hair', color: { argb: 'FFE5E7EB' } } };
          if (r % 2 === 0) c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF3FBF7' } };
        });
        row.getCell('rev').font = { bold: true, color: { argb: 'FF065F46' } };
        row.getCell('i').alignment = { horizontal: 'center' };
        row.getCell('nb').alignment = { horizontal: 'center' };
      }
      ws.autoFilter = 'A1:I1';
    }
    build('Топ 80% (' + top.length + ')', top);
    build('Весь ассортимент (' + list.length + ')', list);

    wb.xlsx.writeBuffer().then(function (buf) {
      var blob = new Blob([buf], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
      a.download = ('SKU_ABC_' + mn).replace(/[^0-9A-Za-zА-Яа-яЁё]+/g, '_') + '.xlsx';
      document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    });
  }

  window.exportSkuPareto = exportSkuPareto;

  // ── ВОДОПАД: из чего сложилось изменение ───────────────────
  var WF = null, WF_MODE = 'ctr';

  function wfAgg(mk, mode) {
    var r = {};
    ((window.CTR || {})[mk] || []).forEach(function (c) {
      if (mode === 'ctr') { var sn = shortCtr(c.name); r[sn] = (r[sn] || 0) + c.rev; }
      else (c.items || []).forEach(function (it) { r[it.n] = (r[it.n] || 0) + it.r; });
    });
    return r;
  }

  window.wfMode = function (m) {
    WF_MODE = m;
    var a = document.getElementById('wf-b-ctr'), b = document.getElementById('wf-b-sku');
    if (a) a.classList.toggle('active', m === 'ctr');
    if (b) b.classList.toggle('active', m === 'sku');
    window.wfDraw();
  };

  window.wfInit = function () {
    var ms = months(); if (ms.length < 2) return;
    var f = document.getElementById('wf-from'), t = document.getElementById('wf-to');
    if (!f || !t) return;
    var opts = ms.map(function (m) { return '<option value="' + m + '">' + monthName(m) + '</option>'; }).join('');
    f.innerHTML = opts; t.innerHTML = opts;
    var to = MK && ms.indexOf(MK) > 0 ? MK : ms[ms.length - 1];
    var from = ms[ms.indexOf(to) - 1] || ms[0];
    f.value = from; t.value = to;
    var nb = document.getElementById('wf-norm');
    if (nb) nb.checked = periodInfo(to).partial;
    window.wfDraw();
  };

  window.wfDraw = function () {
    var cv = document.getElementById('ch-wf'); if (!cv || !window.Chart) return;
    var f = document.getElementById('wf-from'), t = document.getElementById('wf-to');
    if (!f || !t || !f.value || !t.value) return;
    var from = f.value, to = t.value;
    var norm = (document.getElementById('wf-norm') || {}).checked;
    var topN = +((document.getElementById('wf-top') || {}).value || 8);

    var pi = periodInfo(to), k = (norm && pi.partial) ? pi.dim / pi.days : 1;
    var A = wfAgg(from, WF_MODE), B = wfAgg(to, WF_MODE);
    var keys = {}; Object.keys(A).forEach(function (x) { keys[x] = 1; }); Object.keys(B).forEach(function (x) { keys[x] = 1; });
    var deltas = Object.keys(keys).map(function (n) {
      return { n: n, d: (B[n] || 0) * k - (A[n] || 0) };
    }).filter(function (x) { return Math.abs(x.d) > 1; });

    deltas.sort(function (a, b) { return Math.abs(b.d) - Math.abs(a.d); });
    var main = deltas.slice(0, topN), rest = deltas.slice(topN);
    var restSum = rest.reduce(function (s, x) { return s + x.d; }, 0);

    var neg = main.filter(function (x) { return x.d < 0; }).sort(function (a, b) { return a.d - b.d; });
    var pos = main.filter(function (x) { return x.d > 0; }).sort(function (a, b) { return b.d - a.d; });
    var steps = neg.concat(pos);
    if (Math.abs(restSum) > 1) steps.push({ n: 'Прочие (' + rest.length + ')', d: restSum });

    var totA = Object.keys(A).reduce(function (s, n) { return s + A[n]; }, 0);
    var totB = Object.keys(B).reduce(function (s, n) { return s + B[n]; }, 0) * k;

    var labels = [monthName(from)], base = [0], val = [totA / 1e6], col = ['#7c3aed'];
    var cum = totA;
    steps.forEach(function (s) {
      labels.push(s.n.length > 26 ? s.n.slice(0, 26) + '…' : s.n);
      if (s.d >= 0) { base.push(cum / 1e6); val.push(s.d / 1e6); col.push('#10b981'); }
      else { base.push((cum + s.d) / 1e6); val.push(-s.d / 1e6); col.push('#ef4444'); }
      cum += s.d;
    });
    labels.push(monthName(to) + (k !== 1 ? ' (в темпе)' : ''));
    base.push(0); val.push(totB / 1e6); col.push('#a855f7');

    if (WF) { try { WF.destroy(); } catch (e) { } }
    WF = new Chart(cv, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          { data: base, backgroundColor: 'rgba(0,0,0,0)', stack: 'w', pointStyle: false },
          { data: val, backgroundColor: col, stack: 'w', borderRadius: 4 }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        animation: { duration: 650, easing: 'easeOutQuart' },
        layout: { padding: { top: 30, right: 16, left: 4, bottom: 2 } },
        plugins: {
          legend: { display: false },
          datalabels: {
            display: function (c) { return c.datasetIndex === 1; },
            anchor: 'end', align: 'top', color: function (c) { return col[c.dataIndex]; },
            font: { size: 11, weight: 800 },
            formatter: function (v, c) {
              var i = c.dataIndex;
              if (i === 0 || i === labels.length - 1) return v.toFixed(1);
              return (col[i] === '#10b981' ? '+' : '−') + v.toFixed(1);
            }
          },
          tooltip: {
            filter: function (i) { return i.datasetIndex === 1; },
            callbacks: {
              label: function (c) {
                var i = c.dataIndex;
                if (i === 0 || i === labels.length - 1) return 'Итого: ' + c.parsed.y.toFixed(1) + ' млн';
                var s = steps[i - 1];
                var was = (A[s.n] || 0) / 1e6, now = ((B[s.n] || 0) * k) / 1e6;
                var pct = was ? (s.d / (A[s.n] || 1) * 100) : 100;
                return [(s.d >= 0 ? '+' : '−') + Math.abs(s.d / 1e6).toFixed(2) + ' млн (' +
                  (s.d >= 0 ? '+' : '') + pct.toFixed(0) + '%)',
                  'было ' + was.toFixed(1) + ' → стало ' + now.toFixed(1) + ' млн'];
              }
            }
          }
        },
        scales: {
          x: { stacked: true, ticks: { color: '#94a3b8', font: { size: 10 }, maxRotation: 38, minRotation: 0 }, grid: { display: false } },
          y: { stacked: true, grace: '10%', ticks: { color: '#64748b', font: { size: 10 }, callback: function (v) { return v + 'М'; } }, grid: { color: 'rgba(51,65,85,.3)' } }
        }
      }
    });

    // авто-вывод текстом
    var note = document.getElementById('wf-note');
    if (note) {
      var dt = totB - totA, p = totA ? dt / totA * 100 : 0;
      var dn = neg.slice(0, 3).map(function (x) { return '<b>' + esc(x.n) + '</b> ' + (x.d / 1e6).toFixed(1) + ' млн'; });
      var dp = pos.slice(0, 3).map(function (x) { return '<b>' + esc(x.n) + '</b> +' + (x.d / 1e6).toFixed(1) + ' млн'; });
      note.innerHTML = '<span class="' + (dt >= 0 ? 'wf-up' : 'wf-down') + '">'
        + monthName(to) + (k !== 1 ? ' (в темпе на месяц)' : '') + ': ' + sf(totB) + ' — '
        + (dt >= 0 ? 'рост' : 'падение') + ' на ' + sf(Math.abs(dt)) + ' (' + p.toFixed(1) + '%) к '
        + monthDat(from) + '.</span>'
        + (dn.length ? ' Больше всего потеряли: ' + dn.join(', ') + '.' : '')
        + (dp.length ? ' Компенсировали: ' + dp.join(', ') + '.' : '');
    }
    var sub = document.getElementById('wf-sub');
    if (sub) sub.textContent = '— ' + (WF_MODE === 'ctr' ? 'по контрагентам' : 'по товарам');
  };

  // ── выручка по месяцам с долями топ-5 контрагентов ─────────
  var CTRCOL = ['#7c3aed', '#06b6d4', '#f59e0b', '#10b981', '#ef4444'];
  var BCH = null;
  function drawYearByCtr() {
    var cv = document.getElementById('ch-year');
    if (!cv || !window.Chart) return;
    var ms = months(); if (!ms.length) return;

    var tot = {}, nm = {};
    ms.forEach(function (mk) {
      ((window.CTR || {})[mk] || []).forEach(function (c) {
        tot[c.num] = (tot[c.num] || 0) + c.rev; nm[c.num] = c.name;
      });
    });
    var top = Object.keys(tot).sort(function (a, b) { return tot[b] - tot[a]; }).slice(0, 5);

    var byMonth = {};
    ms.forEach(function (mk) {
      byMonth[mk] = {};
      ((window.CTR || {})[mk] || []).forEach(function (c) { byMonth[mk][c.num] = c.rev; });
    });

    var ds = top.map(function (n, i) {
      return {
        label: shortCtr(nm[n]), backgroundColor: CTRCOL[i], borderRadius: 3, stack: 's',
        data: ms.map(function (mk) { return (byMonth[mk][n] || 0) / 1e6; })
      };
    });
    ds.push({
      label: 'Остальные', backgroundColor: '#475569', borderRadius: 3, stack: 's',
      data: ms.map(function (mk) {
        var t = index(mk).total, s = 0;
        top.forEach(function (n) { s += byMonth[mk][n] || 0; });
        return Math.max(0, t - s) / 1e6;
      })
    });

    var prev = (Chart.getChart ? Chart.getChart(cv) : null) || BCH;
    if (prev) { try { prev.destroy(); } catch (e) { } }
    BCH = new Chart(cv, {
      type: 'bar',
      data: { labels: ms.map(function (m) { return monthName(m); }), datasets: ds },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#cbd5e1', boxWidth: 12, font: { size: 11 }, padding: 14 } },
          datalabels: {
            display: function (c) { return c.datasetIndex === c.chart.data.datasets.length - 1; },
            anchor: 'end', align: 'top', offset: 2, color: '#e2e8f0',
            font: { size: 12, weight: 800 },
            formatter: function (v, c) {
              var i = c.dataIndex;
              var tt = c.chart.data.datasets.reduce(function (s, d) { return s + (d.data[i] || 0); }, 0);
              return tt.toFixed(1) + ' млн';
            }
          },
          tooltip: {
            callbacks: {
              label: function (c) {
                var tt = c.chart.data.datasets.reduce(function (s, d) { return s + (d.data[c.dataIndex] || 0); }, 0);
                var p = tt ? (c.parsed.y / tt * 100).toFixed(1) : 0;
                return c.dataset.label + ': ' + c.parsed.y.toFixed(1) + ' млн (' + p + '%)';
              },
              footer: function (items) {
                var tt = items[0].chart.data.datasets.reduce(function (s, d) { return s + (d.data[items[0].dataIndex] || 0); }, 0);
                return 'Итого: ' + tt.toFixed(1) + ' млн';
              }
            }
          }
        },
        scales: {
          x: { stacked: true, ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { display: false } },
          y: {
            stacked: true, ticks: { color: '#64748b', font: { size: 10 }, callback: function (v) { return v + 'М'; } },
            grid: { color: 'rgba(51,65,85,.35)' }
          }
        }
      }
    });
  }

  // ── аналитика за год ───────────────────────────────────────
  var YCH = null;
  window.renderYearAnalytics = function () {
    var ms = months(); if (!ms.length) return;

    // 1) динамика категорий по месяцам (накопительные столбцы)
    var cats = {}, perMonth = {};
    ms.forEach(function (mk) {
      var ix = index(mk); perMonth[mk] = {};
      Object.keys(ix.sku).forEach(function (n) {
        var s = ix.sku[n];
        perMonth[mk][s.cat] = (perMonth[mk][s.cat] || 0) + s.r;
        cats[s.cat] = (cats[s.cat] || 0) + s.r;
      });
    });
    var catList = Object.keys(cats).sort(function (a, b) { return cats[b] - cats[a]; });
    var cv = document.getElementById('ch-year-cats');
    if (cv && window.Chart) {
      if (YCH) { YCH.destroy(); YCH = null; }
      YCH = new Chart(cv, {
        type: 'bar',
        data: {
          labels: ms.map(function (m) { return monthName(m); }),
          datasets: catList.map(function (c) {
            return {
              label: c, backgroundColor: CATC[c] || '#6366f1', borderRadius: 3,
              data: ms.map(function (m) { return (perMonth[m][c] || 0) / 1e6; })
            };
          })
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#94a3b8', boxWidth: 12, font: { size: 11 } } },
            datalabels: { display: false },
            tooltip: { callbacks: { label: function (c) { return c.dataset.label + ': ' + c.parsed.y.toFixed(1) + ' млн'; } } }
          },
          scales: {
            x: { stacked: true, ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { display: false } },
            y: { stacked: true, ticks: { color: '#64748b', font: { size: 10 }, callback: function (v) { return v + 'М'; } }, grid: { color: 'rgba(51,65,85,.35)' } }
          }
        }
      });
    }

    // 2) ТОП-20 товаров за год + накопленная доля (Парето)
    var T = trend(), tot = {};
    Object.keys(T).forEach(function (n) {
      tot[n] = ms.reduce(function (s, m) { return s + (T[n][m] || 0); }, 0);
    });
    var all = Object.keys(tot).map(function (n) { return { n: n, r: tot[n], cat: skuCat(n) }; })
      .sort(function (a, b) { return b.r - a.r; });
    var grand = all.reduce(function (s, x) { return s + x.r; }, 0) || 1;
    var top = all.slice(0, 20), max = top.length ? top[0].r : 1, cum = 0;
    var h = '<table class="sku-tbl"><thead><tr><th style="width:34px">#</th><th>Позиция</th>'
      + '<th>Категория</th><th style="text-align:right">Выручка за год</th>'
      + '<th style="text-align:right">Доля</th><th style="text-align:right">Накопл.</th>'
      + '<th style="width:150px">По месяцам</th></tr></thead><tbody>';
    top.forEach(function (s, i) {
      cum += s.r / grand * 100;
      var mx = Math.max.apply(null, ms.map(function (m) { return T[s.n][m] || 0; })) || 1;
      var spark = '<div style="display:flex;align-items:flex-end;gap:3px;height:26px">'
        + ms.map(function (m) {
          var v = T[s.n][m] || 0;
          return '<div title="' + monthName(m) + ': ' + num(v) + '" style="flex:1;height:'
            + Math.max(8, Math.round(v / mx * 100)) + '%;background:' + (m === ms[ms.length - 1] ? '#a855f7' : 'rgba(124,58,237,.45)')
            + ';border-radius:2px"></div>';
        }).join('') + '</div>';
      h += '<tr style="cursor:default"><td class="sku-rank">' + (i + 1) + '</td>'
        + '<td class="sku-name">' + esc(s.n) + '<div class="mini"><i style="width:'
        + Math.max(2, Math.round(s.r / max * 100)) + '%;background:' + (CATC[s.cat] || '#6366f1') + '"></i></div></td>'
        + '<td><span class="cat-tag"><i style="background:' + (CATC[s.cat] || '#6366f1') + '"></i>' + esc(s.cat) + '</span></td>'
        + '<td class="sku-num sku-rev">' + num(s.r) + '</td>'
        + '<td class="sku-num" style="color:#94a3b8">' + (s.r / grand * 100).toFixed(1) + '%</td>'
        + '<td class="sku-num" style="color:#34d399;font-weight:700">' + cum.toFixed(1) + '%</td>'
        + '<td>' + spark + '</td></tr>';
    });
    h += '</tbody></table>';
    var el = document.getElementById('year-top-sku');
    if (el) el.innerHTML = h;
  };

  window.setCtrView = function (v) {
    VIEW = v; OPEN_SKU = -1;
    if (CH) { CH.destroy(); CH = null; }
    var a = document.getElementById('vb-sku'), b = document.getElementById('vb-ctr');
    if (a) a.classList.toggle('active', v === 'sku');
    if (b) b.classList.toggle('active', v === 'ctr');
    window.drawCtr();
  };

  window.skuShowAll = function (v) { SHOW_ALL = !!v; OPEN_SKU = -1; window.drawCtr(); };

  window.skuSort = function (k) {
    if (SORT.k === k) SORT.dir = -SORT.dir;
    else { SORT.k = k; SORT.dir = (k === 'n' || k === 'cat') ? 1 : -1; }
    OPEN_SKU = -1;
    window.drawCtr();
  };

  window.skuToggle = function (i) {
    OPEN_SKU = (OPEN_SKU === i) ? -1 : i;
    if (CH) { CH.destroy(); CH = null; }
    window.drawCtr();
  };

  window.skuToggleCat = function (c) {
    if (CATS_OFF[c]) delete CATS_OFF[c]; else CATS_OFF[c] = 1;
    OPEN_SKU = -1;
    window.drawCtr();
  };

  window.ctrToggle = function (i) {
    OPEN_CTR[i] = !OPEN_CTR[i];
    window.drawCtr();
  };
})();
