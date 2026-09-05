// ============================================================
//  Система «Пульс» — панель управления «Мастерская Сегодня».
//  Автор и разработчик: Ольга Герасименко. © 2026. Все права защищены.
// ============================================================
// worker.js — серверный расчёт ДЗ/КЗ прямо в Cloudflare.
// Читает публичную Google-таблицу, считает и отдаёт /dz_kz.js.
// Обновляется по расписанию (cron) и по запросу — компьютер не нужен.

const SHEET_ID = "13iFd16Hah1Yi5y2QptmyUrw51rSFfAmtnzhf0U2g_wc";
const KZ_GID = "2005257911";
const DZ_GID = "597090672";
const CACHE_KEY = "https://internal.cache/dz_kz.js?v=2";
const CACHE_TTL = 3600; // секунд

// Файлы данных, которые пересобирает ежедневный прогон. Их нельзя кэшировать:
// имя не меняется, а содержимое меняется по нескольку раз в день.
// (*_meta.js ловится отдельно регулярным выражением.)
const DATA_FILES = new Set([
  "/zakup_data.js", "/dz_kz.js", "/kz_ana.js", "/opiu_audit.js", "/opiu_iiko.js", "/ddsp_days.js",
  "/sku_live.js", "/sku_analytics.js", "/contractor_items.js", "/contractors.js",
  "/sales_live.js", "/opiu_rev.js",
]);

// ── Метрики посещений («что смотрят») ──
const M_KEY = "metrics:v1";
// SHA-256 пароля вкладки «Метрики» (сам пароль в репозиторий не попадает)
const METRICS_HASH = "2391eadda6fbf6a5907d84883fdd4e84da1614f7de7db7dd74e4eb7e7ed1d67b";
/* Запасная вставка счётчика в <head>. На деле до страниц она не доезжает:
   Cloudflare отдаёт файлы из [assets] в обход скрипта воркера, и HTMLRewriter
   ниже срабатывает только для HTML, собранного самим воркером. Настоящий
   счётчик живёт в nav.js, который подключён на каждом дашборде, — там же
   собирается и паспорт устройства. Оставляем на случай, если маршрутизация
   ассетов изменится и HTML снова пойдёт через воркер. */
const METRICS_BEACON = `<script>try{(function(){
var K='pulse_did',d='';
try{d=localStorage.getItem(K)||'';if(!d){d=(self.crypto&&crypto.randomUUID?crypto.randomUUID():(Date.now().toString(36)+Math.random().toString(36).slice(2)));localStorage.setItem(K,d)}}catch(e){}
var n=navigator,s=screen,o={};try{o=Intl.DateTimeFormat().resolvedOptions()}catch(e){}
var q='p='+encodeURIComponent(location.pathname)
+'&d='+encodeURIComponent(String(d).slice(0,40))
+'&sw='+(s.width||0)+'&sh='+(s.height||0)+'&vw='+(innerWidth||0)+'&vh='+(innerHeight||0)
+'&dpr='+(devicePixelRatio||1)+'&cd='+(s.colorDepth||0)
+'&cc='+(n.hardwareConcurrency||0)+'&dm='+(n.deviceMemory||0)+'&tp='+(n.maxTouchPoints||0)
+'&pf='+encodeURIComponent(n.platform||'')+'&lg='+encodeURIComponent(n.language||'')
+'&tz='+encodeURIComponent(o.timeZone||'')
+'&rf='+encodeURIComponent((document.referrer||'').slice(0,120));
fetch('/track?'+q,{method:'GET',keepalive:true})})()}catch(e){}</script>`;


// ── Личная галерея «Мальдивы» (доступ по коду) ───────────────────────────────
const GAL_HASH = "f8a5da214f3f6c281e008924914e7decf9a13637737204589eed04379dc600a8";
const GAL_PREFIX = "gal:";

function galOk(request, url) {
  const t = url.searchParams.get("t") || request.headers.get("x-gal-token") || "";
  return t === GAL_HASH;
}
function galJson(o, status) {
  return new Response(JSON.stringify(o), { status: status || 200, headers: {
    "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
}
async function handleGallery(request, env, url) {
  const path = url.pathname.replace(/^\/api\/gal\/?/, "");

  if (path === "auth") {
    let body = {};
    try { body = await request.json(); } catch (e) {}
    const ok = String(body.p || "") === GAL_HASH;
    return galJson(ok ? { ok: true, t: GAL_HASH } : { ok: false }, ok ? 200 : 401);
  }

  if (!galOk(request, url)) return galJson({ error: "нет доступа" }, 401);

  if (path === "list") {
    const out = [];
    let cursor;
    do {
      const r = await env.PLAN.list({ prefix: GAL_PREFIX, cursor, limit: 1000 });
      for (const k of r.keys) out.push(Object.assign({ key: k.name }, k.metadata || {}));
      cursor = r.list_complete ? null : r.cursor;
    } while (cursor);
    out.sort((a, b) => String(a.d || "").localeCompare(String(b.d || "")));
    return galJson({ items: out, count: out.length });
  }

  if (path === "up" && request.method === "POST") {
    const name = url.searchParams.get("n") || "file";
    const ct = url.searchParams.get("ct") || "application/octet-stream";
    const d = url.searchParams.get("d") || new Date().toISOString();
    const kind = ct.indexOf("video") === 0 ? "video" : "photo";
    const buf = await request.arrayBuffer();
    if (!buf.byteLength) return galJson({ error: "пустой файл" }, 400);
    if (buf.byteLength > 24 * 1024 * 1024) return galJson({ error: "файл больше 24 МБ" }, 413);
    const key = GAL_PREFIX + d.slice(0, 19).replace(/[:T]/g, "-") + "_" +
                Math.random().toString(36).slice(2, 8);
    await env.PLAN.put(key, buf, { metadata: { n: name.slice(0, 120), ct, d, k: kind, s: buf.byteLength } });
    return galJson({ ok: true, key });
  }

  if (path === "rm" && request.method === "POST") {
    const key = url.searchParams.get("k") || "";
    if (key.indexOf(GAL_PREFIX) !== 0) return galJson({ error: "нет такого файла" }, 400);
    await env.PLAN.delete(key);
    return galJson({ ok: true });
  }

  if (path.indexOf("f/") === 0) {
    const key = decodeURIComponent(path.slice(2));
    if (key.indexOf(GAL_PREFIX) !== 0) return galJson({ error: "нет такого файла" }, 400);
    const r = await env.PLAN.getWithMetadata(key, { type: "arrayBuffer" });
    if (!r || !r.value) return galJson({ error: "файл не найден" }, 404);
    const m = r.metadata || {};
    const h = { "content-type": m.ct || "application/octet-stream", "cache-control": "private, max-age=86400" };
    if (url.searchParams.get("dl")) h["content-disposition"] = 'attachment; filename="' + encodeURIComponent(m.n || "file") + '"';
    return new Response(r.value, { headers: h });
  }

  return galJson({ error: "неизвестный запрос" }, 404);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === "/dz_kz.js") {
      const cache = caches.default;
      const noCache = url.searchParams.has("nocache");
      let resp = noCache ? null : await cache.match(CACHE_KEY);
      if (!resp) {
        const js = await buildJs();
        resp = new Response(js, {
          headers: {
            "content-type": "application/javascript; charset=utf-8",
            "cache-control": `public, max-age=${CACHE_TTL}`,
          },
        });
        ctx.waitUntil(cache.put(CACHE_KEY, resp.clone()));
      }
      return resp;
    }
    if (url.pathname === "/api/plan") {
      return handlePlan(request, env);
    }
    if (url.pathname === "/sales_live.js") {
      return salesJs(env, url);
    }
    if (url.pathname === "/sales_core.json") {
      return salesCore(env, url);
    }
    if (url.pathname === "/sku_live.js") {
      return skuJs(env, url);
    }
    if (url.pathname === "/sku_totals.json") {
      const p = JSON.parse((await env.PLAN.get(SKU_KEY)) || "null");
      const out = { updated: p?.meta?.pulled, through: p?.meta?.through,
                    sku_count: p?.skus?.length || 0,
                    selfcheck: p?.meta?.selfcheck || null, changes: p?.meta?.changes || [],
                    mo_labels: p?.mo_labels || [], months: {} };
      if (p) p.mo_labels.forEach((lab, i) => {
        out.months[lab] = {
          rev: p.skus.reduce((s, x) => s + (x.monthly_rev[i] || 0), 0),
          vp: p.skus.reduce((s, x) => s + (x.monthly_vp[i] || 0), 0),
        };
      });
      return new Response(JSON.stringify(out), { headers: {
        "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
    }
    if (url.pathname === "/sales_week") {
      return salesWeek(env, url).catch((e) =>
        new Response("error," + String(e).slice(0, 120), { status: 500,
          headers: { "content-type": "text/csv; charset=utf-8" } }));
    }
    if (url.pathname === "/sales_totals.json") {
      const yNow = new Date(Date.now() - 86400000).getUTCFullYear();
      const p = JSON.parse((await env.PLAN.get(salesKey(yNow))) || "null");
      const out = { updated: p?.meta?.pulled, through: p?.meta?.through, months: {} };
      if (p) for (const k of Object.keys(p.DS)) {
        if (!/^\d{4}-\d{2}$/.test(k)) continue;
        const m = p.DS[k];
        out.months[k] = { label: m.label, rev: m.total_rev, gp: m.total_gp,
                          cogs: m.total_cogs || null, sku: m.sku_count };
      }
      return new Response(JSON.stringify(out), { headers: {
        "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
    }
    if (url.pathname.indexOf("/api/gal") === 0) {
      return handleGallery(request, env, url).catch((e) =>
        new Response(JSON.stringify({ error: String(e).slice(0, 160) }), { status: 500,
          headers: { "content-type": "application/json; charset=utf-8" } }));
    }
    if (url.pathname === "/api/halal") {
      return handleHalal(request, env);
    }
    if (url.pathname === "/track") return handleTrack(url, request, env, ctx);
    if (url.pathname === "/mstats") return handleStats(url, env);
    if (url.pathname === "/mlabel") return handleLabel(url, env);
    // отдаём статику, а в HTML тихо вставляем счётчик просмотров
    const _res = await env.ASSETS.fetch(request);
    const _ct = _res.headers.get("content-type") || "";
    // Свежесть: страницы (HTML) и все файлы данных не кэшируем на edge,
    // иначе Cloudflare может «залипнуть» на старой версии после деплоя,
    // а дашборд будет рисовать вчерашние цифры со свежей датой обновления.
    const _noStore = _ct.includes("text/html")
      || DATA_FILES.has(url.pathname)
      || /_meta\.js$/.test(url.pathname);
    if (_ct.includes("text/html")) {
      const _t = new HTMLRewriter()
        .on("head", { element(e) { e.append(METRICS_BEACON, { html: true }); } })
        .transform(_res);
      const _r = new Response(_t.body, _t);
      _r.headers.set("cache-control", "no-store, must-revalidate");
      return _r;
    }
    if (_noStore) {
      const _r = new Response(_res.body, _res);
      _r.headers.set("cache-control", "no-store, must-revalidate");
      return _r;
    }
    return _res;
  },

  async scheduled(event, env, ctx) {
    // 03:00 UTC = 08:00 по Алматы — обновляем продажи из айко
    if (event.cron === "0 3 * * *") {
      ctx.waitUntil(buildSales(env).catch((e) => console.error("продажи:", String(e))));
      ctx.waitUntil(buildSku(env).catch((e) => console.error("sku:", String(e))));
      return;
    }
    ctx.waitUntil((async () => {
      const js = await buildJs();
      const resp = new Response(js, {
        headers: {
          "content-type": "application/javascript; charset=utf-8",
          "cache-control": `public, max-age=${CACHE_TTL}`,
        },
      });
      await caches.default.put(CACHE_KEY, resp);
    })());
  },
};

/* ══════════════════════════════════════════════════════════════════
   ПРОДАЖИ ИЗ АЙКО — обновление прямо в облаке, без компьютера.

   Берём OLAP-отчёт по проводкам (TRANSACTIONS), тип «Выручка расходной
   накладной» (OUTGOING_INVOICE_REVENUE) — это то же, что «I Отчет ПРОДАЖИ».
   Важно: айко считает верхнюю дату периода исключительно, поэтому конец
   периода задаём следующим днём.

   Валовой прибыли в этом отчёте нет — она приходит из учёта, поэтому
   переносим её из предыдущего расчёта, а для незакрытого месяца оцениваем
   по средней марже двух последних закрытых месяцев (как и раньше).
   ══════════════════════════════════════════════════════════════════ */
const IIKO = { url: "https://fudzavod.iiko.it", login: "GerassimenkoO", pass: "1234" };
const salesKey = (y) => `sales-live-${y}`;   // хранение по годам, история не теряется
const RU_MONTHS = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                   "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
// ВП по месяцам из учёта (в отчёте продаж её нет). Обновляется при пересчёте.
const GP_SEED = { "2026-05": 136665071, "2026-06": 141938558 };

async function sha1hex(s) {
  const b = await crypto.subtle.digest("SHA-1", new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

/* ── Отладчик OLAP (временный): узнать поля/значения и калибровать запрос. */
async function iikoProbe(url) {
  const J = (o, st = 200) => new Response(JSON.stringify(o, null, 1), {
    status: st, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
  try {
    const token = await iikoAuth();
    const cols = url.searchParams.get("cols");
    if (cols) {
      const r = await fetch(`${IIKO.url}/resto/api/v2/reports/olap/columns?reportType=${encodeURIComponent(cols)}`,
        { headers: { Cookie: `key=${token}` } });
      const t = await r.text(); let p; try { p = JSON.parse(t); } catch { p = t; }
      return J({ status: r.status, columns: p });
    }
    const q = url.searchParams.get("q");
    if (q) {
      const body = JSON.parse(decodeURIComponent(escape(atob(q.replace(/-/g, "+").replace(/_/g, "/")))));
      const r = await fetch(`${IIKO.url}/resto/api/v2/reports/olap`, {
        method: "POST", headers: { Cookie: `key=${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body) });
      const t = await r.text(); let p; try { p = JSON.parse(t); } catch { p = t; }
      const data = p && p.data;
      const sum = Array.isArray(data)
        ? data.reduce((s, x) => { for (const k in x) if (typeof x[k] === "number") (s[k] = (s[k] || 0) + x[k]); return s; }, {})
        : null;
      return J({ status: r.status, rows: Array.isArray(data) ? data.length : null, sums: sum,
                 sample: Array.isArray(data) ? data.slice(0, 120) : p });
    }
    return J({ hint: "?cols=TRANSACTIONS | ?q=<base64url olap>" });
  } catch (e) { return J({ error: String(e && e.stack || e) }, 500); }
}

async function iikoAuth() {
  const p = await sha1hex(IIKO.pass);
  const r = await fetch(`${IIKO.url}/resto/api/auth?login=${encodeURIComponent(IIKO.login)}&pass=${p}`);
  if (!r.ok) throw new Error("авторизация айко: " + r.status);
  return (await r.text()).trim().replace(/^"|"$/g, "");
}

async function iikoMonth(token, from, toExcl) {
  const r = await fetch(`${IIKO.url}/resto/api/v2/reports/olap`, {
    method: "POST",
    headers: { Cookie: `key=${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      reportType: "TRANSACTIONS",
      buildSummary: "true",
      groupByRowFields: ["Counteragent.Name", "Product.Name"],
      aggregateFields: ["Amount", "Sum.Incoming"],
      filters: {
        "DateTime.DateTyped": { filterType: "DateRange", periodType: "CUSTOM",
                                from, to: toExcl, includeLow: true, includeHigh: true },
        TransactionType: { filterType: "IncludeValues", values: ["OUTGOING_INVOICE_REVENUE"] },
      },
    }),
  });
  if (!r.ok) throw new Error(`OLAP ${r.status}: ${(await r.text()).slice(0, 200)}`);
  return (await r.json()).data || [];
}

/* Себестоимость отгрузок за период: тот же отчёт по проводкам,
   тип «Расходная накладная» (OUTGOING_INVOICE) — списание со склада. */
async function iikoCogs(token, from, toExcl) {
  const r = await fetch(`${IIKO.url}/resto/api/v2/reports/olap`, {
    method: "POST",
    headers: { Cookie: `key=${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      reportType: "TRANSACTIONS",
      buildSummary: "true",
      groupByRowFields: ["TransactionType"],
      aggregateFields: ["Sum.Incoming"],
      filters: {
        "DateTime.DateTyped": { filterType: "DateRange", periodType: "CUSTOM",
                                from, to: toExcl, includeLow: true, includeHigh: true },
        TransactionType: { filterType: "IncludeValues", values: ["OUTGOING_INVOICE"] },
      },
    }),
  });
  if (!r.ok) return null;
  const d = (await r.json()).data || [];
  return d.reduce((s, x) => s + (x["Sum.Incoming"] || 0), 0);
}

/* Классификатор категорий — держать синхронно с skuCat() в sku_analytics.js */
function skuCatW(name) {
  const n = String(name).toUpperCase();
  const has = (...w) => w.some((x) => n.includes(x));
  if (has("КОМПОТ","МОРС","ЛИМОНАД","СОК ","ЧАЙ ","КОФЕ","ВОДА","НАПИТ","СМУЗИ","АЙРАН","КВАС")) return "Напитки";
  if (has("ТОРТ","БЕНТО")) return "Торты";
  if (has("КИМПАБ","ОНИГИР","УДОН","РАМЕН","СУШИ","ГИОЗА","ПОКЕ","ЯПОН","ВОК ","ЯННЕМ","ТОКПОК")) return "Япония";
  if (has("БЛИН","СЫРНИК","КАША","ОМЛЕТ","ЗАВТРАК","ГРАНОЛА","ХЛОПЬ")) return "Завтраки";
  if (has("САЛАТ","ШУБА","ВИНЕГРЕТ")) return "Салаты";
  if (has("СЭНДВИЧ","СЕНДВИЧ","БУРГЕР","ХОТ-ДОГ","ХОТДОГ","ДОГ (","ШАУРМА","ЧИАБАТТА","БАГЕТ С","ТОСТ")) return "Сэндвичи";
  if (has("ЧИЗКЕЙК","ТИРАМИСУ","БРАУНИ","МЕДОВИК","НАПОЛЕОН","ПИРОЖН","ЭКЛЕР","ДЕСЕРТ","ЧИА ",
          "ПУДДИНГ","ПУДИНГ","МАФФИН","КУКИС","ОРЕШКИ","СИННАБОН","МОРОЖ","ШАРЛОТКА","ПАХЛАВА",
          "ЗЕФИР","МАКАРУН")) return "Десерты";
  if (has("СОСИСКА В ТЕСТЕ","ПИРОЖОК","ПИРОГ","САМСА","СЛОЙК","КРУАССАН","БУЛОЧК","ХЛЕБ","ЛАВАШ",
          "БРЕЦЕЛЬ","СОЧНИК","ЛЕПЁШ","ЛЕПЕШ","ХАЧАПУРИ","ВЫПЕЧК","БАГЕТ","ШТРУДЕЛЬ","РУЛЕТ")) return "Выпечка";
  if (has("П/Ф","ПП*","КУРИЦ","ГОВЯД","СВИН","ИНДЕЙК","КОТЛЕТ","ШНИЦЕЛЬ","МАНТЫ","ПЛОВ","ПАСТА",
          "ПЕННЕ","ФУЗИЛЛИ","ЛАГМАН","ГУЙРУ","ЦОМЯН","ПЕЛЬМЕН","ВАРЕНИК","ТЕФТЕЛ","БРИЗОЛЬ","ЛЮЛЯ",
          "БЕФСТРОГ","ЗРАЗ","СУП ","БОРЩ","ТОМ ЯМ","КРЫЛЬЯ","ЗАПЕКАНК","ПЮРЕ","ГРЕЧК","РИС ","РАГУ",
          "ЖАРЕН","БИФШТЕКС","ГУЛЯШ","ТУЧИКЕН","ГАРНИР","ГОЛУБЦ","ФАРШ","ШАШЛЫК","СТЕЙК","НАГГЕТС",
          "КАРТОФ")) return "Горячее";
  return "Прочее";
}
const isMagnumW = (n) => /MAGNUM|МАГНУМ/i.test(String(n));

function buildMonth(items) {
  const cat = {}; let total = 0;
  for (const [name, v] of items) {
    const c = skuCatW(name);
    total += v.rev;
    (cat[c] ||= { rev: 0, qty: 0, count: 0 });
    cat[c].rev += v.rev; cat[c].qty += v.qty; cat[c].count++;
  }
  const categories = Object.entries(cat)
    .sort((a, b) => b[1].rev - a[1].rev)
    .map(([c, x]) => ({ cat: c, rev: Math.round(x.rev), qty: Math.round(x.qty),
                        count: x.count, pct: total ? +(x.rev / total * 100).toFixed(1) : 0 }));
  const ranked = [...items].sort((a, b) => b[1].rev - a[1].rev);
  const top20 = ranked.slice(0, 20).map(([n, v]) => ({
    name: n, cat: skuCatW(n), rev: Math.round(v.rev), qty: Math.round(v.qty), magnum: isMagnumW(n) }));
  const mag = ranked.filter(([n]) => isMagnumW(n));
  const magRev = mag.reduce((s, [, v]) => s + v.rev, 0);
  return {
    total_rev: Math.round(total),
    mag_rev: Math.round(magRev),
    mag_pct: total ? +(magRev / total * 100).toFixed(1) : 0,
    sku_count: items.size,
    categories, top20,
    magnum_items: mag.slice(0, 30).map(([n, v]) => ({ name: n, rev: Math.round(v.rev), qty: Math.round(v.qty) })),
  };
}

/* Список контрагентов в том же виде, что раньше отдавал contractor_items.js:
   [{num, name, rev, pct, points, items:[{n,q,r}]}] — sku_analytics.js ждёт массив. */
function ctrList(map, monthRev) {
  return Object.values(map)
    .sort((a, b) => b.rev - a.rev)
    .map((c) => ({
      num: c.num,
      name: c.name,
      rev: Math.round(c.rev),
      pct: monthRev ? +((c.rev / monthRev) * 100).toFixed(1) : 0,
      points: c.pts.size,
      items: Object.values(c.items)
        .sort((a, b) => b.r - a.r)
        .map((i) => ({ n: i.n, q: Math.round(i.q), r: Math.round(i.r) })),
    }));
}

const ctrKey = (name) => {
  const m = String(name).match(/^\s*(\d+)/);
  return m ? m[1] : String(name).trim();
};

/* Продажи по контрагентам за неделю (CSV для Google-таблицы: IMPORTDATA+ВПР).
   Формат ответа: строки "префикс,сумма". Префикс = ведущее число имени
   контрагента (тот же ctrKey, по которому сходится сверка).
   Параметры: ?from=YYYY-MM-DD&to=YYYY-MM-DD (включительно), &t=токен. */
async function salesWeek(env, url) {
  const p = url.searchParams;
  if (p.get("t") !== "fzw2026")
    return new Response("forbidden", { status: 403 });
  const isoD = (d) => d.toISOString().slice(0, 10);
  let from = p.get("from"), to = p.get("to");
  if (!from || !to) {
    // последняя завершённая неделя сб–пт относительно вчера
    const y = new Date(Date.now() - 86400000);
    const dow = y.getUTCDay();                 // 0=вс..6=сб; пятница=5
    const back = (dow - 5 + 7) % 7;            // до ближайшей прошедшей пятницы
    const fri = new Date(Date.UTC(y.getUTCFullYear(), y.getUTCMonth(), y.getUTCDate() - back));
    const sat = new Date(fri.getTime() - 6 * 86400000);
    from = isoD(sat); to = isoD(fri);
  }
  const toExcl = isoD(new Date(Date.parse(to) + 86400000));
  const token = await iikoAuth();
  const rows = await iikoMonth(token, from, toExcl);
  const agg = {};
  for (const r of rows) {
    const ca = String(r["Counteragent.Name"] || "").trim();
    if (!ca) continue;
    agg[ctrKey(ca)] = (agg[ctrKey(ca)] || 0) + (r["Sum.Incoming"] || 0);
  }
  let csv = `prefix,sum\nПЕРИОД:${from}..${to},0\n`;
  for (const [k, v] of Object.entries(agg))
    if (Math.round(v) !== 0) csv += `${k},${Math.round(v)}\n`;
  return new Response(csv, { headers: {
    "content-type": "text/csv; charset=utf-8",
    "cache-control": "public, max-age=1800",
    "access-control-allow-origin": "*" } });
}

async function buildSales(env) {
  const token = await iikoAuth();
  const now = new Date();
  const lastFull = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  lastFull.setUTCDate(lastFull.getUTCDate() - 1);          // последний полный день
  const iso = (d) => d.toISOString().slice(0, 10);

  const YEAR = lastFull.getUTCFullYear();            // год берём от даты, не прибит гвоздями
  const prev = JSON.parse((await env.PLAN.get(salesKey(YEAR))) || "null") || {};
  const DS = {}, CTR = {}, yearItems = new Map();
  const yearCtr = {};

  for (let m = 1; m <= 12; m++) {
    const d1 = new Date(Date.UTC(YEAR, m - 1, 1));
    if (d1 > lastFull) break;
    const eom = new Date(Date.UTC(YEAR, m, 0));
    const d2 = eom < lastFull ? eom : lastFull;
    const rows = await iikoMonth(token, iso(d1), iso(new Date(d2.getTime() + 86400000)));
    if (!rows.length) continue;

    const items = new Map(), ctr = {};
    for (const r of rows) {
      const nm = String(r["Product.Name"] || "").trim();
      const ca = String(r["Counteragent.Name"] || "").trim();
      if (!nm) continue;
      const rev = r["Sum.Incoming"] || 0, qty = Math.abs(r["Amount"] || 0);
      if (!items.has(nm)) items.set(nm, { rev: 0, qty: 0 });
      const it = items.get(nm); it.rev += rev; it.qty += qty;
      if (!yearItems.has(nm)) yearItems.set(nm, { rev: 0, qty: 0 });
      const yi = yearItems.get(nm); yi.rev += rev; yi.qty += qty;
      const key = ctrKey(ca);
      (ctr[key] ||= { num: key, name: ca, rev: 0, pts: new Set(), items: {} });
      ctr[key].rev += rev; ctr[key].pts.add(ca);
      (ctr[key].items[nm] ||= { n: nm, q: 0, r: 0 });
      ctr[key].items[nm].q += qty; ctr[key].items[nm].r += rev;
      (yearCtr[key] ||= { num: key, name: ca, rev: 0, pts: new Set(), items: {} });
      yearCtr[key].rev += rev; yearCtr[key].pts.add(ca);
      (yearCtr[key].items[nm] ||= { n: nm, q: 0, r: 0 });
      yearCtr[key].items[nm].q += qty; yearCtr[key].items[nm].r += rev;
    }

    const mk = `${YEAR}-${String(m).padStart(2, "0")}`;
    const md = buildMonth(items);
    const partial = d2 < eom;
    md.label = partial ? `${RU_MONTHS[m]} (1–${d2.getUTCDate()})` : RU_MONTHS[m];
    md.partial = partial;
    md.days = d2.getUTCDate();
    md.dim = eom.getUTCDate();
    // себестоимость и валовая прибыль — из того же отчёта по проводкам
    const cogs = await iikoCogs(token, iso(d1), iso(new Date(d2.getTime() + 86400000)));
    if (cogs && cogs > 0) {
      md.total_cogs = Math.round(cogs);
      md.total_gp = Math.round(md.total_rev - cogs);
      md.gp_margin = md.total_rev ? +((md.total_gp / md.total_rev) * 100).toFixed(1) : 0;
      md.gp_source = "отчёт";
    } else {
      md.total_gp = (prev.DS?.[mk]?.gp_est ? 0 : prev.DS?.[mk]?.total_gp) || GP_SEED[mk] || 0;
    }
    md.contractors = Object.values(ctr)
      .sort((a, b) => b.rev - a.rev)
      .map((c) => ({ name: c.name, rev: Math.round(c.rev) }));
    DS[mk] = md;
    CTR[mk] = ctrList(ctr, md.total_rev);
  }

  // валовая прибыль незакрытого месяца — по марже двух последних закрытых
  const keys = Object.keys(DS).sort();
  const closed = keys.filter((k) => !DS[k].partial && DS[k].total_gp && DS[k].total_rev);
  const base = closed.slice(-2);
  if (base.length) {
    const margin = base.reduce((s, k) => s + DS[k].total_gp, 0) /
                   base.reduce((s, k) => s + DS[k].total_rev, 0);
    for (const k of keys) {
      if (!DS[k].total_gp && DS[k].total_rev) {
        DS[k].total_gp = Math.round(DS[k].total_rev * margin);
        DS[k].gp_est = true;
        DS[k].gp_margin = +(margin * 100).toFixed(1);
      }
    }
  }

  const ya = buildMonth(yearItems);
  ya.label = `Год ${YEAR}`;
  ya.is_year = true;
  ya.total_gp = keys.reduce((s, k) => s + (DS[k].total_gp || 0), 0);
  ya.total_cogs = keys.reduce((s, k) => s + (DS[k].total_cogs || 0), 0);
  ya.gp_margin = ya.total_rev ? +((ya.total_gp / ya.total_rev) * 100).toFixed(1) : 0;
  ya.contractors = Object.values(yearCtr).sort((a, b) => b.rev - a.rev)
    .map((c) => ({ name: c.name, rev: Math.round(c.rev) }));
  DS.year = ya;
  CTR.year = ctrList(yearCtr, ya.total_rev);

  // Обнаружение расхождений: сравниваем свежую выручку каждого месяца
  // с прошлым расчётом. Если закрытый месяц изменился — значит в айке
  // правили документы задним числом; фиксируем это, чтобы было видно.
  const curMk = `${YEAR}-${String(lastFull.getUTCMonth() + 1).padStart(2, "0")}`;
  const changes = [];
  for (const k of keys) {
    const was = Math.round(prev.DS?.[k]?.total_rev || 0);
    const now = Math.round(DS[k].total_rev || 0);
    if (was && Math.abs(now - was) >= 1) {
      changes.push({ mk: k, label: DS[k].label, was, now, delta: now - was,
                     closed: k !== curMk });
    }
  }

  const meta = {
    pulled: (() => {                       // время по Алматы, формат дд.мм.гггг чч:мм
      const t = new Date(Date.now() + 5 * 3600e3);
      const p = (x) => String(x).padStart(2, "0");
      return `${p(t.getUTCDate())}.${p(t.getUTCMonth() + 1)}.${t.getUTCFullYear()} ` +
             `${p(t.getUTCHours())}:${p(t.getUTCMinutes())}`;
    })(),
    through: `${String(lastFull.getUTCDate()).padStart(2, "0")}.${String(lastFull.getUTCMonth() + 1).padStart(2, "0")}.${lastFull.getUTCFullYear()}`,
    source: "iiko",
    report: "I Отчет ПРОДАЖИ · выручка расходных накладных (обновление в облаке)",
    fullPeriod: true,          // каждое утро пересобираются все месяцы года
    changes,                   // что изменилось против прошлого расчёта
  };
  const payload = { DS, CTR, meta };
  await env.PLAN.put(salesKey(YEAR), JSON.stringify(payload));
  return payload;
}

/* ══════════════════════════════════════════════════════════════════
   SKU-АНАЛИЗ ГОТОВОЙ ПРОДУКЦИИ — «Отчёт о продажах за период» из айко,
   помесячно 2025→текущий, склады готовой продукции (ГП), прямо в облаке.

   Выручка   = проводки «Выручка расходной накладной» (OUTGOING_INVOICE_REVENUE)
   Себестоим = проводки «Расходная накладная» (OUTGOING_INVOICE, списание)
   ВП        = выручка − себестоимость,  наценка = ВП/выручка.
   Фильтр по складам ГП и по типу транзакции. Категории сырья/упаковки/цехов
   исключаем — это готовая продукция (как в исходном отчёте).
   ══════════════════════════════════════════════════════════════════ */
const SKU_KEY = "sku-live";
const SKU_START_YEAR = 2025;
const GP_STORES = ["Склад ГП ФЗ", "Склад ГП -25 C° ФЗ"];
const RU_SHORT = ["", "янв", "фев", "мар", "апр", "май", "июн",
                  "июл", "авг", "сен", "окт", "ноя", "дек"];
// не готовая продукция — в SKU-анализ не берём
const SKU_SKIP_CAT = new Set(["", "сырье", "сырьё", "несъедобные", "упаковка",
  "мясной цех", "овощной цех", "общий цех", "фасовочный цех", "тара"]);

async function olapTx(token, { from, toExcl, ttypes, group, agg }) {
  const r = await fetch(`${IIKO.url}/resto/api/v2/reports/olap`, {
    method: "POST",
    headers: { Cookie: `key=${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      reportType: "TRANSACTIONS", buildSummary: "false",
      groupByRowFields: group, aggregateFields: agg,
      filters: {
        "DateTime.DateTyped": { filterType: "DateRange", periodType: "CUSTOM",
                                from, to: toExcl, includeLow: true, includeHigh: true },
        TransactionType: { filterType: "IncludeValues", values: ttypes },
        Store: { filterType: "IncludeValues", values: GP_STORES },
      },
    }),
  });
  if (!r.ok) throw new Error(`OLAP ${r.status}: ${(await r.text()).slice(0, 150)}`);
  return (await r.json()).data || [];
}

function skuTrend(rev) {                       // импульс: последние 3 мес vs предыдущие 3
  const nz = rev.map((v, i) => [i, v]).filter(([, v]) => v > 0);
  if (nz.length < 2) return 0;
  const idx = nz.map(([i]) => i);
  const last3 = idx.slice(-3), prev3 = idx.slice(-6, -3);
  const s = (arr) => arr.reduce((a, i) => a + rev[i], 0) / (arr.length || 1);
  const a = s(prev3), b = s(last3);
  if (!a) return 0;
  return Math.round((b - a) / a * 100);
}

async function buildSku(env) {
  const token = await iikoAuth();
  const now = new Date();
  const lastFull = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  lastFull.setUTCDate(lastFull.getUTCDate() - 1);
  const iso = (d) => d.toISOString().slice(0, 10);
  const prev = JSON.parse((await env.PLAN.get(SKU_KEY)) || "null") || {};

  const months = [];
  for (let y = SKU_START_YEAR; y <= lastFull.getUTCFullYear(); y++) {
    for (let m = 1; m <= 12; m++) {
      const d1 = new Date(Date.UTC(y, m - 1, 1));
      if (d1 > lastFull) break;
      const eom = new Date(Date.UTC(y, m, 0));
      const d2 = eom < lastFull ? eom : lastFull;
      months.push({ y, m, d1, d2, eom, partial: d2 < eom });
    }
  }
  const N = months.length;
  const skus = new Map();
  const ensure = (name, cat) => {
    let o = skus.get(name);
    if (!o) { o = { name, cat: cat || "—", rev: Array(N).fill(0), cost: Array(N).fill(0),
                    qty: Array(N).fill(0) }; skus.set(name, o); }
    if (cat && (o.cat === "—" || !o.cat)) o.cat = cat;
    return o;
  };

  for (let i = 0; i < N; i++) {
    const { d1, d2 } = months[i];
    const toExcl = iso(new Date(d2.getTime() + 86400000));
    const [rev, cost] = await Promise.all([
      olapTx(token, { from: iso(d1), toExcl, ttypes: ["OUTGOING_INVOICE_REVENUE"],
                      group: ["Product.Category", "Product.Name"], agg: ["Sum.Incoming", "Amount"] }),
      olapTx(token, { from: iso(d1), toExcl, ttypes: ["OUTGOING_INVOICE"],
                      group: ["Product.Name"], agg: ["Sum.Incoming"] }),
    ]);
    for (const row of rev) {
      const nm = String(row["Product.Name"] || "").trim();
      const cat = String(row["Product.Category"] || "").trim();
      if (!nm) continue;
      if (SKU_SKIP_CAT.has(cat.toLowerCase())) continue;
      const o = ensure(nm, cat || "—");
      o.rev[i] += row["Sum.Incoming"] || 0;
      o.qty[i] += Math.abs(row["Amount"] || 0);
    }
    for (const row of cost) {
      const nm = String(row["Product.Name"] || "").trim();
      if (!nm || !skus.has(nm)) continue;       // себестоимость только для позиций с выручкой
      skus.get(nm).cost[i] += row["Sum.Incoming"] || 0;
    }
  }

  const mo_labels = months.map(({ y, m }) => `${RU_SHORT[m]}'${String(y).slice(2)}`);
  const arr = [];
  for (const o of skus.values()) {
    const monthly_rev = o.rev.map((x) => Math.round(x));
    const monthly_qty = o.qty.map((x) => Math.round(x));
    const monthly_vp = o.rev.map((r, i) => Math.round(r - (o.cost[i] || 0)));
    const total_rev = monthly_rev.reduce((s, x) => s + x, 0);
    if (total_rev <= 0) continue;
    const total_vp = monthly_vp.reduce((s, x) => s + x, 0);
    const total_qty = monthly_qty.reduce((s, x) => s + x, 0);
    const active_months = monthly_rev.filter((x) => x > 0).length;
    const margin = total_rev ? +((total_vp / total_rev) * 100).toFixed(1) : 0;
    arr.push({ name: o.name, cat: o.cat, total_rev, total_vp, total_qty, margin,
               active_months, trend: skuTrend(monthly_rev), monthly_rev, monthly_vp, monthly_qty });
  }
  arr.sort((a, b) => b.total_rev - a.total_rev);

  // ── помесячные итоги построенного набора
  const builtByMo = mo_labels.map((_, i) => Math.round(arr.reduce((s, x) => s + x.monthly_rev[i], 0)));
  const builtTotal = builtByMo.reduce((s, x) => s + x, 0);

  // ── САМОПРОВЕРКА №1: независимый пересчёт всей суммы одним запросом к iiko
  //    (другая группировка — по категории за весь период). Если сходится с
  //    построчной сборкой — значит цикл не потерял и не задвоил ни одного месяца.
  let selfcheck = { ok: true, built: builtTotal, control: builtTotal, diff: 0 };
  try {
    const ctrlRows = await olapTx(token, {
      from: iso(months[0].d1),
      toExcl: iso(new Date(months[months.length - 1].d2.getTime() + 86400000)),
      ttypes: ["OUTGOING_INVOICE_REVENUE"], group: ["Product.Category"], agg: ["Sum.Incoming"] });
    let control = 0;
    for (const r of ctrlRows) {
      const cat = String(r["Product.Category"] || "").trim();
      if (SKU_SKIP_CAT.has(cat.toLowerCase())) continue;
      control += r["Sum.Incoming"] || 0;
    }
    control = Math.round(control);
    const diff = builtTotal - control;
    selfcheck = { ok: Math.abs(diff) <= Math.max(50, control * 0.005), built: builtTotal, control, diff,
                  pct: control ? +(diff / control * 100).toFixed(2) : 0 };
  } catch (e) { selfcheck = { ok: null, error: String(e).slice(0, 120), built: builtTotal }; }

  // ── САМОПРОВЕРКА №2: сравнение с прошлым снимком. Если закрытый месяц
  //    изменился — значит в iiko правили документы задним числом. Показываем.
  const changes = [];
  if (prev && Array.isArray(prev.skus) && Array.isArray(prev.mo_labels)) {
    const prevByLabel = {};
    prev.mo_labels.forEach((lab, i) => {
      prevByLabel[lab] = Math.round(prev.skus.reduce((s, x) => s + (x.monthly_rev[i] || 0), 0));
    });
    const lastLabel = mo_labels[mo_labels.length - 1];   // текущий (незакрытый) месяц
    mo_labels.forEach((lab, i) => {
      const was = prevByLabel[lab];
      const nowV = builtByMo[i];
      if (was != null && Math.abs(nowV - was) >= 1) {
        changes.push({ mo: lab, was, now: nowV, delta: nowV - was, closed: lab !== lastLabel });
      }
    });
  }

  const almaty = new Date(Date.now() + 5 * 3600e3);
  const p2 = (x) => String(x).padStart(2, "0");
  const meta = {
    pulled: `${p2(almaty.getUTCDate())}.${p2(almaty.getUTCMonth() + 1)}.${almaty.getUTCFullYear()} ` +
            `${p2(almaty.getUTCHours())}:${p2(almaty.getUTCMinutes())}`,
    through: `${p2(lastFull.getUTCDate())}.${p2(lastFull.getUTCMonth() + 1)}.${lastFull.getUTCFullYear()}`,
    source: "iiko", report: "Отчёт о продажах · склады ГП · готовая продукция (обновление в облаке 08:00)",
    partial_last: months.length ? months[months.length - 1].partial : false,
    selfcheck, changes,
  };
  const payload = { skus: arr, mo_labels, meta };
  await env.PLAN.put(SKU_KEY, JSON.stringify(payload));
  return payload;
}

async function skuJs(env, url) {
  let p = JSON.parse((await env.PLAN.get(SKU_KEY)) || "null");
  if (!p || url.searchParams.get("rebuild") === "1") {
    try { p = await buildSku(env); }
    catch (e) { return new Response(`/* sku build error: ${String(e)} */`, {
      status: 200, headers: { "content-type": "application/javascript; charset=utf-8" } }); }
  }
  const js = `window.SKU_DATA_LIVE=${JSON.stringify({ skus: p.skus, mo_labels: p.mo_labels })};\n` +
             `window.SKU_LIVE_META=${JSON.stringify(p.meta)};\n`;
  return new Response(js, { headers: {
    "content-type": "application/javascript; charset=utf-8", "cache-control": "no-store" } });
}

/* Ядро ассортимента месяца: позиции, дающие первые 80% выручки.
   Считаем на сервере и отдаём компактный JSON — для выгрузки в Excel. */
async function salesCore(env, url) {
  const yNow = new Date(Date.now() - 86400000).getUTCFullYear();
  const p = JSON.parse((await env.PLAN.get(salesKey(yNow))) || "null");
  if (!p) return new Response("{}", { headers: { "content-type": "application/json; charset=utf-8" } });
  const mk = url.searchParams.get("mk") ||
             Object.keys(p.DS).filter((k) => /^\d{4}-\d{2}$/.test(k)).sort().pop();
  const share = +(url.searchParams.get("share") || "0.8");
  const items = {};
  for (const c of (p.CTR[mk] || [])) {
    for (const it of c.items) {
      (items[it.n] ||= { n: it.n, q: 0, r: 0 });
      items[it.n].q += it.q; items[it.n].r += it.r;
    }
  }
  const arr = Object.values(items).sort((a, b) => b.r - a.r);
  const total = arr.reduce((s, x) => s + x.r, 0);
  // tail=1 — вернуть «хвост»: позиции ЗА пределами доли share (последние 100-share% выручки)
  const tail = url.searchParams.get("tail") === "1";
  let cum = 0, coreEnd = 0;
  for (const x of arr) { cum += x.r; coreEnd++; if (cum >= total * share) break; }
  const slice = tail ? arr.slice(coreEnd) : arr.slice(0, coreEnd);
  let run = tail ? (cum - (arr.slice(coreEnd - 0, coreEnd).length ? 0 : 0)) : 0;
  // накопительный процент считаем от начала всего списка
  cum = 0; const rows = [];
  arr.forEach((x, idx) => {
    cum += x.r;
    if (tail ? idx >= coreEnd : idx < coreEnd) {
      rows.push({ rank: idx + 1, n: x.n, cat: skuCatW(x.n),
                  q: Math.round(x.q), r: Math.round(x.r),
                  pct: total ? +((x.r / total) * 100).toFixed(3) : 0,
                  cum: total ? +((cum / total) * 100).toFixed(1) : 0,
                  avg: x.q ? Math.round(x.r / x.q) : 0 });
    }
  });
  const off = +(url.searchParams.get("off") || "0");
  const lim = +(url.searchParams.get("lim") || "0");
  const page = lim ? rows.slice(off, off + lim) : rows;
  const out = { mk, label: p.DS[mk]?.label || mk, total: Math.round(total),
                all: arr.length, share, tail, coreCount: coreEnd,
                partCount: rows.length, off, lim,
                partRev: rows.reduce((s, x) => s + x.r, 0),
                meta: p.meta, rows: page };
  return new Response(JSON.stringify(out), {
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" } });
}

async function salesJs(env, url) {
  const yNow = new Date(Date.now() - 86400000).getUTCFullYear();
  let p = JSON.parse((await env.PLAN.get(salesKey(yNow))) || "null");
  if (!p || url.searchParams.has("rebuild")) {
    try { p = await buildSales(env); }
    catch (e) { return new Response(`/* обновление продаж: ${String(e)} */`, {
      headers: { "content-type": "application/javascript; charset=utf-8" } }); }
  }
  const js = `window.DS_LIVE=${JSON.stringify(p.DS)};\n` +
             `window.CTR_LIVE=${JSON.stringify(p.CTR)};\n` +
             `window.SALES_META=${JSON.stringify(p.meta)};\n`;
  return new Response(js, {
    headers: { "content-type": "application/javascript; charset=utf-8",
               "cache-control": "public, max-age=120" },
  });
}

/* ── Общий план бюджета: заявки подразделений и решения директора ──
   Хранится в Cloudflare KV, поэтому виден всем сразу.               */
const PLAN_KEY = "plan-2026-08";

// ── ☪ ХАЛАЛ: ручные пометки статуса сырья (KV) ──
const HALAL_KEY = "halal-overrides-v1";
const HALAL_ST = ["ok", "meat", "warn", "risk"];

async function handleHalal(request, env) {
  if (request.method === "OPTIONS") return jsonResp({ ok: true });
  const KV = env.PLAN;
  if (!KV) return jsonResp({ error: "Хранилище не подключено" }, 500);

  if (request.method === "GET") {
    const s = await KV.get(HALAL_KEY);
    return jsonResp(s ? JSON.parse(s) : { items: {}, log: [], seen: [], updated: null });
  }

  if (request.method === "POST") {
    let body;
    try { body = await request.json(); }
    catch (e) { return jsonResp({ error: "Некорректные данные" }, 400); }

    const raw = await KV.get(HALAL_KEY);
    const cur = raw ? JSON.parse(raw) : { items: {}, log: [], seen: [] };
    cur.items = cur.items || {}; cur.log = cur.log || []; cur.seen = cur.seen || [];
    const ts = new Date().toISOString();
    const fio = (body.fio || "").toString().trim();
    const action = (body.action || "set").toString();

    // отметить текущий список сырья как «просмотренный» (для подсветки новинок)
    if (action === "seen") {
      const names = Array.isArray(body.names) ? body.names.map((x) => String(x)) : [];
      cur.seen = Array.from(new Set(names));
      cur.updated = ts;
      await KV.put(HALAL_KEY, JSON.stringify(cur));
      return jsonResp({ ok: true, seen: cur.seen.length, updated: ts });
    }

    const product = (body.product || "").toString().trim();
    if (!product) return jsonResp({ error: "Не указан товар" }, 400);
    if (!fio) return jsonResp({ error: "Не указано ФИО" }, 400);

    // снять ручную пометку (вернуть авто-статус)
    if (action === "remove") {
      delete cur.items[product];
      cur.log.push({ product, fio, ts, action: "remove" });
      if (cur.log.length > 800) cur.log = cur.log.slice(cur.log.length - 800);
      cur.updated = ts;
      await KV.put(HALAL_KEY, JSON.stringify(cur));
      return jsonResp({ ok: true, updated: ts });
    }

    // задать/изменить статус (+ сертификат и срок)
    const status = (body.status || "").toString().trim();
    if (HALAL_ST.indexOf(status) < 0) return jsonResp({ error: "Неверный статус" }, 400);
    const supplier = (body.supplier || "").toString().trim();
    const cert = (body.cert || "").toString().trim();
    const expiry = (body.expiry || "").toString().trim();
    cur.items[product] = { status, supplier, fio, ts, cert, expiry };
    cur.log.push({ product, supplier, status, fio, ts, cert, expiry });
    if (cur.log.length > 800) cur.log = cur.log.slice(cur.log.length - 800);
    cur.updated = ts;
    await KV.put(HALAL_KEY, JSON.stringify(cur));
    return jsonResp({ ok: true, updated: ts });
  }

  return jsonResp({ error: "Метод не поддерживается" }, 405);
}

function jsonResp(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "content-type",
      "access-control-allow-methods": "GET,POST,OPTIONS",
    },
  });
}

async function handlePlan(request, env) {
  if (request.method === "OPTIONS") return jsonResp({ ok: true });
  const KV = env.PLAN;
  if (!KV) return jsonResp({ error: "Хранилище не подключено" }, 500);

  if (request.method === "GET") {
    const s = await KV.get(PLAN_KEY);
    return jsonResp(s ? JSON.parse(s) : { dept: {}, obu: {}, updated: null });
  }

  if (request.method === "POST") {
    let body;
    try { body = await request.json(); }
    catch (e) { return jsonResp({ error: "Некорректные данные" }, 400); }

    const raw = await KV.get(PLAN_KEY);
    const cur = raw ? JSON.parse(raw) : { dept: {}, obu: {} };
    cur.dept = cur.dept || {};

    if (body.kind === "dept" && body.dept) {
      // Подразделение сохраняет только свои строки.
      // Решение директора остаётся в силе, пока суть строки не изменилась;
      // если поменяли наименование, цену или количество — решение сбрасывается,
      // строка снова уходит на рассмотрение.
      const old = cur.dept[body.dept] || [];
      const inc = body.rows || [];
      const sameQ = (a, b) => JSON.stringify(a || []) === JSON.stringify(b || []);
      inc.forEach((r, i) => {
        const o = old[i];
        const same = o && (o.nom || "") === (r.nom || "")
                       && String(o.price || "") === String(r.price || "")
                       && sameQ(o.q, r.q);
        if (same) { r.dec = o.dec || ""; r.cmt = o.cmt || ""; r.orig = o.orig; }
        else { r.dec = ""; r.cmt = o ? (o.cmt || "") : ""; delete r.orig; }
      });
      cur.dept[body.dept] = inc;

    } else if (body.kind === "decisions") {
      // Директор меняет решение, комментарий, а также цену и количество по неделям
      const inD = body.dept || {};
      Object.keys(inD).forEach((k) => {
        const inc = inD[k] || [], old = cur.dept[k] || [];
        if (!old.length) { cur.dept[k] = inc; return; }
        inc.forEach((r, i) => {
          const o = old[i];
          if (!o) return;
          o.dec = r.dec || ""; o.cmt = r.cmt || "";
          if (r.orig) { o.orig = r.orig; o.price = r.price; o.q = r.q; }
          else if (o.orig) { delete o.orig; o.price = r.price; o.q = r.q; }
        });
        cur.dept[k] = old;
      });

    } else if (body.kind === "obu") {
      cur.obu = body.obu || {};

    } else {
      return jsonResp({ error: "Неизвестный тип запроса" }, 400);
    }

    cur.updated = new Date().toISOString();
    await KV.put(PLAN_KEY, JSON.stringify(cur));
    return jsonResp({ ok: true, updated: cur.updated });
  }

  return jsonResp({ error: "Метод не поддерживается" }, 405);
}

async function buildJs() {
  try {
    const [kzRows, dzRows] = await Promise.all([fetchCsv(KZ_GID), fetchCsv(DZ_GID)]);
    const kz = parseKz(kzRows);
    const dz = parseDz(dzRows);
    const result = {
      updated: nowStr(),
      kz: kz || { total: 0, date: "", dynamics: [], top: [] },
      dz: dz || { total: 0, date: "", dynamics: [], top: [] },
    };
    return "window.DZ_KZ = " + JSON.stringify(result) + ";\n";
  } catch (e) {
    return "window.DZ_KZ = null; /* error: " + String(e).replace(/\*\//g, "") + " */\n";
  }
}

async function fetchCsv(gid) {
  const u = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/export?format=csv&gid=${gid}`;
  const r = await fetch(u, { cf: { cacheTtl: 0 } });
  if (!r.ok) throw new Error("csv " + gid + " status " + r.status);
  let text = await r.text();
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  return parseCsv(text);
}

function parseCsv(t) {
  const R = []; let row = [], cur = "", q = false;
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if (q) {
      if (c === '"') { if (t[i + 1] === '"') { cur += '"'; i++; } else q = false; }
      else cur += c;
    } else {
      if (c === '"') q = true;
      else if (c === ",") { row.push(cur); cur = ""; }
      else if (c === "\n") { row.push(cur); R.push(row); row = []; cur = ""; }
      else if (c === "\r") {}
      else cur += c;
    }
  }
  if (cur !== "" || row.length) { row.push(cur); R.push(row); }
  return R;
}

function num(v) {
  if (v == null) return null;
  let s = String(v).replace(/[\s ]/g, "").replace(/,/g, ".").trim();
  if (s === "") return null;
  const f = parseFloat(s);
  return isNaN(f) ? null : f;
}

function fmtDate(s) {
  s = String(s).trim().replace(/\.+$/, "");
  const p = s.split(".");
  if (p.length === 3) {
    let [d, m, y] = p;
    if (y.trim().length === 2) y = "20" + y.trim();
    return `${d.padStart(2, "0")}.${m.padStart(2, "0")}.${y}`;
  }
  return s;
}

function dateKey(lbl) {
  const p = lbl.split(".");
  if (p.length === 3) {
    let [d, m, y] = p; if (y.length === 2) y = "20" + y;
    const yi = +y, mi = +m, di = +d;
    if (!isNaN(yi) && !isNaN(mi) && !isNaN(di)) return yi * 10000 + mi * 100 + di;
  }
  return 0;
}

function isCompany(name) {
  if (!name || !name.trim() || name.trim().length < 3) return false;
  const skip = ["итого", "всего", "поставщик", "кредит", "ставят", "стоп",
    "нам должны", "мы должны", "дебитор", "статус", "---"];
  const nl = name.toLowerCase();
  return !skip.some((k) => nl.includes(k));
}

function findHeaderRow(rows, rx, maxScan = 15) {
  for (let i = 0; i < Math.min(maxScan, rows.length); i++) {
    if (rows[i].some((c) => rx.test(String(c)))) return [i, rows[i]];
  }
  return [null, null];
}

function parseKz(rows) {
  let [hi, header] = findHeaderRow(rows, /задолженность\s+на/i);
  if (header === null) [hi, header] = findHeaderRow(rows, /задолж/i);
  if (header === null) [hi, header] = findHeaderRow(rows, /кз\s+на\s+\d/i);
  if (header === null) return null;
  const data = rows.slice(hi + 1);

  let itogo = null;
  for (const row of data) {
    if (row && String(row[0]).trim().toUpperCase() === "ИТОГО") { itogo = row; break; }
  }

  const debtCols = [];
  header.forEach((cell, i) => {
    const c = String(cell).trim();
    let m = null;
    if (/задолженность\s+на\s+\d/i.test(c)) m = c.match(/(\d{1,2}\.\d{2}\.\d{2,4})/);
    else if (/кз\s+на\s+\d/i.test(c)) m = c.match(/(\d{1,2}\.\d{2}\.\d{2,4})/);
    if (m) debtCols.push([i, fmtDate(m[1])]);
  });
  if (!debtCols.length) return null;
  debtCols.sort((a, b) => dateKey(a[1]) - dateKey(b[1]));

  const itogoTotal = (ci) => {
    if (itogo && ci < itogo.length) {
      const v = num(itogo[ci]);
      if (v != null && Math.abs(v) > 1000000) return Math.abs(v);
    }
    return null;
  };

  const dynCand = [];
  for (const [ci, lbl] of debtCols) {
    const t = itogoTotal(ci);
    if (t && t > 50000000) dynCand.push([ci, lbl, t]);
  }
  const dynCols = dynCand.slice(-8);
  const dynamics = dynCols.map(([, lbl, t]) => ({ date: lbl, total: Math.round(t) }));

  let latestTotal = 0, lastDate = debtCols[debtCols.length - 1][1];
  let lastCol = debtCols[debtCols.length - 1][0];
  if (dynCols.length) { [lastCol, lastDate, latestTotal] = dynCols[dynCols.length - 1]; }
  else {
    for (const row of data) {
      if (!isCompany(row[0] || "")) continue;
      const v = lastCol < row.length ? num(row[lastCol]) : null;
      if (v && v > 0) latestTotal += v;
    }
  }

  const kzOnly = debtCols.filter(([i]) => /кз\s+на/i.test(header[i]));
  const topCol = kzOnly.length ? kzOnly[kzOnly.length - 1][0] : lastCol;

  // Кредиторка = ОТРИЦАТЕЛЬНЫЕ остатки (мы должны). Положительные — авансы, не КЗ.
  const top = [];
  for (const row of data) {
    const name = (row[0] || "").trim();
    if (!isCompany(name)) continue;
    const v = topCol < row.length ? num(row[topCol]) : null;
    if (v && v < 0) top.push({ name, debt: Math.round(-v) });
  }
  top.sort((a, b) => b.debt - a.debt);

  return { total: Math.round(latestTotal), date: lastDate, dynamics, top: top.slice(0, 30) };
}

function parseDz(rows) {
  let [hi, header] = findHeaderRow(rows, /дз\s+на|д\/з\s+на|д\.з\.\s+на/i);
  if (header === null) [hi, header] = findHeaderRow(rows, /дз|д\/з/i);
  if (header === null) return null;

  const dzCols = [];
  header.forEach((cell, i) => {
    const c = String(cell).trim();
    if (/дз\s+на|д\/з\s+на|д\.з\.\s*на/i.test(c)) {
      const m = c.match(/(\d{1,2}\.\d{2}\.\d{2,4})/);
      dzCols.push([i, m ? fmtDate(m[1]) : c.slice(0, 20)]);
    }
  });
  if (!dzCols.length) return null;
  const data = rows.slice(hi + 1);

  const dynCols = dzCols.slice(-8);
  const dynamics = [];
  for (const [ci, lbl] of dynCols) {
    let total = 0;
    for (const row of data) {
      if (!isCompany(row[0] || "")) continue;
      const v = ci < row.length ? num(row[ci]) : null;
      if (v && v > 0) total += v;
    }
    if (total > 0) dynamics.push({ date: lbl, total: Math.round(total) });
  }

  const [lastCol, lastDate] = dzCols[dzCols.length - 1];
  const top = []; let latestTotal = 0;
  for (const row of data) {
    const name = (row[0] || "").trim();
    if (!isCompany(name)) continue;
    const v = lastCol < row.length ? num(row[lastCol]) : null;
    if (v && v > 0) { latestTotal += v; top.push({ name, debt: Math.round(v) }); }
  }
  top.sort((a, b) => b.debt - a.debt);

  // ---- Консигнация: остаток ДЗ (14 дней) + отгрузка/оплата последней недели ----
  // Структура листа ДЗ по каждому периоду: [ДЗ на prev][Отгрузка нед][Поступление нед][ДЗ на now].
  // Консигнация каждого контрагента = ДЗ на последнюю дату (вся непогашенная задолженность
  // в 14-дневном окне). Отдельно даём отгрузку и оплату последней недели.
  const li = dzCols.length - 1;
  const lastDzCol = dzCols[li][0];
  const prevDzCol = li > 0 ? dzCols[li - 1][0] : -1;
  const prevDzCol2 = li > 1 ? dzCols[li - 2][0] : -1;
  let shipCol = -1, payCol = -1, shipPrevCol = -1, shipLabel = "", payLabel = "";
  header.forEach((cell, i) => {
    const c = String(cell);
    if (i > prevDzCol && i < lastDzCol) {
      if (/отгрузк/i.test(c)) { shipCol = i; shipLabel = c.trim(); }
      if (/поступл/i.test(c)) { payCol = i; payLabel = c.trim(); }
    }
    if (i > prevDzCol2 && i < prevDzCol && /отгрузк/i.test(c)) shipPrevCol = i;
  });
  const cell = (row, ci) => (ci >= 0 && ci < row.length ? num(row[ci]) : null);
  const consign = [];
  for (const row of data) {
    const name = (row[0] || "").trim();
    if (!isCompany(name)) continue;
    const dz = cell(row, lastDzCol) || 0;
    const dzPrev = cell(row, prevDzCol) || 0;
    const ship = cell(row, shipCol) || 0;
    const pay = cell(row, payCol) || 0;
    const shipPrev = cell(row, shipPrevCol) || 0;
    if (dz <= 0 && ship <= 0 && pay <= 0) continue;
    consign.push({
      name,
      dz: Math.round(dz),
      dzPrev: Math.round(dzPrev),
      ship: Math.round(ship),
      pay: Math.round(pay),
      shipPrev: Math.round(shipPrev),
    });
  }
  consign.sort((a, b) => b.dz - a.dz);
  const prevDate = prevDzCol >= 0 ? dzCols[li - 1][1] : "";
  const consignMeta = { date: lastDate, prevDate, shipLabel, payLabel };

  return {
    total: Math.round(latestTotal), date: lastDate, dynamics, top: top.slice(0, 30),
    consign: consign.slice(0, 60), consignMeta,
  };
}

function nowStr() {
  const d = new Date(Date.now() + 5 * 3600 * 1000); // Алматы UTC+5
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getUTCDate())}.${p(d.getUTCMonth() + 1)}.${d.getUTCFullYear()} ${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`;
}

// ── Метрики посещений: запись просмотра и выдача статистики ──
/* Один и тот же отчёт приходит под разными адресами: Cloudflare отдаёт
   ассеты без «.html» (страница открыта как /путеводитель.html, а браузер
   показывает /путеводитель), а главная — то «/», то «/index.html». Без
   приведения к одному виду один отчёт разъезжался в метриках на две строки
   с разными цифрами. */
function normPath(raw) {
  let p = String(raw || "/").split("?")[0].split("#")[0];
  if (!p.startsWith("/")) p = "/" + p;
  if (p.length > 1 && p.endsWith("/")) p = p.slice(0, -1);
  if (p === "" || p === "/") return "/index.html";
  const last = p.slice(p.lastIndexOf("/") + 1);
  if (last && last.indexOf(".") < 0) p += ".html";
  return p;
}

async function handleTrack(url, request, env, ctx) {
  const p = normPath(url.searchParams.get("p")).slice(0, 160);
  const ua = request.headers.get("user-agent") || "";
  if (/bot|crawl|spider|slurp|preview|monitor|headless|curl|wget|python-requests|facebookexternalhit|whatsapp|telegrambot/i.test(ua)) {
    return new Response("", { status: 204 });
  }
  ctx.waitUntil(recordView(p, request, env, url).catch(() => {}));
  // Client hints (модель телефона, версия системы, разрядность) браузер
  // присылает только после заголовка Accept-CH, и просить их надо у того
  // ответа, который реально проходит через воркер: статику Cloudflare
  // отдаёт мимо скрипта, поэтому ставим заголовок здесь. Настройка живёт
  // на весь домен, так что следующий заход придёт уже с подробностями.
  return new Response("", { status: 204, headers: {
    "cache-control": "no-store",
    "access-control-allow-origin": "*",
    "accept-ch": "sec-ch-ua, sec-ch-ua-mobile, sec-ch-ua-platform, sec-ch-ua-platform-version, sec-ch-ua-model, sec-ch-ua-arch, sec-ch-ua-bitness",
  } });
}

/* Разбор User-Agent: марка браузера, система, модель. Библиотеку сюда тянуть
   не за чем — на завод заходят с пяти-шести устройств, и этих правил хватает.
   Порядок проверок важен: Яндекс.Браузер и Edge представляются Chrome, а
   Chrome на айфоне — Safari, поэтому частное проверяем раньше общего. */
function parseUA(ua) {
  const u = String(ua || "");
  let os = "", osv = "", model = "", br = "", bv = "", kind = "компьютер", eng = "";
  let m;
  if ((m = u.match(/iPhone OS (\d+[_\d]*)/))) { os = "iOS"; osv = m[1].replace(/_/g, "."); model = "iPhone"; kind = "телефон"; }
  else if (/iPad/.test(u)) { os = "iPadOS"; model = "iPad"; kind = "планшет";
    if ((m = u.match(/CPU OS (\d+[_\d]*)/))) osv = m[1].replace(/_/g, "."); }
  else if ((m = u.match(/Android (\d+(?:\.\d+)*)/))) {
    os = "Android"; osv = m[1]; kind = /Mobile/.test(u) ? "телефон" : "планшет";
    const mm = u.match(/;\s*([^;()]+?)\s+Build\//) || u.match(/Android [^;]+;\s*([^;()]+?)\)/);
    if (mm) model = mm[1].trim();
  }
  else if ((m = u.match(/Windows NT ([\d.]+)/))) {
    os = "Windows"; osv = { "10.0": "10 или 11", "6.3": "8.1", "6.2": "8", "6.1": "7" }[m[1]] || m[1];
  }
  else if ((m = u.match(/Mac OS X (\d+[_\d]*)/))) { os = "macOS"; osv = m[1].replace(/_/g, "."); model = "Mac"; }
  else if (/CrOS/.test(u)) { os = "ChromeOS"; }
  else if (/Linux/.test(u)) { os = "Linux"; }

  if ((m = u.match(/YaBrowser\/([\d.]+)/))) { br = "Яндекс.Браузер"; bv = m[1]; }
  else if ((m = u.match(/(?:OPR|OPiOS|Opera)\/([\d.]+)/))) { br = "Opera"; bv = m[1]; }
  else if ((m = u.match(/Edg(?:iOS|A)?\/([\d.]+)/))) { br = "Edge"; bv = m[1]; }
  else if ((m = u.match(/SamsungBrowser\/([\d.]+)/))) { br = "Samsung Internet"; bv = m[1]; }
  else if ((m = u.match(/(?:CriOS|Chrome)\/([\d.]+)/))) { br = "Chrome"; bv = m[1]; }
  else if ((m = u.match(/(?:FxiOS|Firefox)\/([\d.]+)/))) { br = "Firefox"; bv = m[1]; }
  else if ((m = u.match(/Version\/([\d.]+)[^)]*Safari/))) { br = "Safari"; bv = m[1]; }
  else if (/Safari/.test(u)) { br = "Safari"; }

  if (/Firefox|FxiOS/.test(u)) eng = "Gecko";
  else if (/Chrome|CriOS|Edg|OPR|YaBrowser|SamsungBrowser/.test(u)) eng = "Blink";
  else if (/AppleWebKit/.test(u)) eng = "WebKit";

  return { os, osv, model, br, bv, eng, kind };
}

async function recordView(p, request, env, trackUrl) {
  const now = new Date();
  const alm = new Date(now.getTime() + 5 * 3600 * 1000); // Алматы UTC+5
  const day = alm.toISOString().slice(0, 10);
  const hour = alm.getUTCHours();
  const cf = request.cf || {};
  const country = cf.country || "??";
  // Город даёт Cloudflare по адресу посетителя. Иногда его нет — тогда «—».
  const city = String(cf.city || "").trim() || "—";
  const ua = request.headers.get("user-agent") || "";
  const isMob = /Mobile|Android|iPhone|iPad|iPod|Opera Mini|IEMobile/i.test(ua);

  // «Компьютер» считаем как связку адреса и браузера. Храним только короткий
  // хэш: сам IP в базу не попадает, а одинаковые заходы с одной машины
  // схлопываются в одну запись за день.
  const ip = request.headers.get("cf-connecting-ip") || "";
  const ipHash = (await sha256hex("pulse|" + ip)).slice(0, 8);
  // Постоянный номер из localStorage надёжнее связки «адрес + браузер»:
  // у телефона адрес меняется по дороге, и одна и та же трубка распадалась
  // на три разных «устройства» за день. Если номера нет (старая вкладка,
  // приватный режим) — как раньше, по хэшу адреса и браузера.
  const qs = (trackUrl && trackUrl.searchParams) || new URLSearchParams();
  const did = String(qs.get("d") || "").slice(0, 40).replace(/[^A-Za-z0-9_-]/g, "");
  const vid = did ? "d" + did.slice(0, 11)
                  : (await sha256hex("pulse|" + ip + "|" + ua)).slice(0, 12);

  const raw = await env.PLAN.get(M_KEY);
  const m = raw ? JSON.parse(raw) : { pages: {}, days: {}, updated: "" };
  if (!m.days) m.days = {};

  // ── разрез по страницам (как было) ──────────────────────────────
  const pg = m.pages[p] || (m.pages[p] = { t: 0, d: {}, h: new Array(24).fill(0), c: {}, dev: { m: 0, d: 0 }, last: "" });
  if (!pg.h || pg.h.length !== 24) pg.h = new Array(24).fill(0);
  pg.t = (pg.t || 0) + 1;
  pg.d[day] = (pg.d[day] || 0) + 1;
  pg.h[hour] = (pg.h[hour] || 0) + 1;
  pg.c[country] = (pg.c[country] || 0) + 1;
  if (isMob) pg.dev.m = (pg.dev.m || 0) + 1; else pg.dev.d = (pg.dev.d || 0) + 1;
  pg.last = now.toISOString();

  // ── разрез по дням: устройства, страницы, города ────────────────
  const dd = m.days[day] || (m.days[day] = { v: 0, u: [], p: {}, city: {}, ctry: {}, h: new Array(24).fill(0), dev: { m: 0, d: 0 } });
  if (!dd.h || dd.h.length !== 24) dd.h = new Array(24).fill(0);
  if (!Array.isArray(dd.u)) dd.u = [];
  dd.v = (dd.v || 0) + 1;
  if (dd.u.indexOf(vid) < 0 && dd.u.length < 5000) dd.u.push(vid);
  dd.p[p] = (dd.p[p] || 0) + 1;
  dd.city[city] = (dd.city[city] || 0) + 1;
  // Сколько РАЗНЫХ устройств открывало каждую страницу и заходило из каждого
  // города. Раньше по странице считались только открытия, и было не понять:
  // девятнадцать заходов — это девятнадцать человек или один, обновлявший
  // страницу. Храним те же короткие хэши, что и в dd.u, — адреса в базу
  // по-прежнему не попадают.
  if (!dd.pu) dd.pu = {};
  if (!dd.cu) dd.cu = {};
  // Момент, с которого в этот день считаются устройства по страницам. В день
  // включения разбивка охватывает не все сутки, и без этой отметки цифры
  // выглядят противоречиво: «за день 3 устройства», а по страницам одно.
  if (!dd.puFrom) dd.puFrom = now.toISOString();
  const pl = dd.pu[p] || (dd.pu[p] = []);
  if (pl.indexOf(vid) < 0 && pl.length < 300) pl.push(vid);
  const cl = dd.cu[city] || (dd.cu[city] = []);
  if (cl.indexOf(vid) < 0 && cl.length < 300) cl.push(vid);
  if (!dd.ctry) dd.ctry = {};
  dd.ctry[country] = (dd.ctry[country] || 0) + 1;
  dd.h[hour] = (dd.h[hour] || 0) + 1;
  if (isMob) dd.dev.m = (dd.dev.m || 0) + 1; else dd.dev.d = (dd.dev.d || 0) + 1;

  // ── ПАСПОРТ УСТРОЙСТВА ──────────────────────────────────────────
  // Сводные счётчики отвечали «сколько заходов», но не «кто именно смотрел».
  // Здесь на каждое устройство копится карточка: что за техника, какой
  // браузер, экран, откуда заходит и какие отчёты открывает.
  if (!m.devs) m.devs = {};
  const P = parseUA(ua);
  const n0 = (v) => { const x = parseFloat(v); return isFinite(x) && x > 0 ? x : 0; };
  const st = (v, lim) => String(v || "").slice(0, lim || 40);
  const ch = (h) => st(request.headers.get(h) || "", 60).replace(/^"|"$/g, "");
  const dv = m.devs[vid] || (m.devs[vid] = { name: "", first: now.toISOString(), n: 0, pages: {}, days: {} });
  dv.n = (dv.n || 0) + 1;
  dv.last = now.toISOString();
  dv.pages[p] = (dv.pages[p] || 0) + 1;
  dv.days[day] = (dv.days[day] || 0) + 1;
  dv.kind = P.kind; dv.os = P.os; dv.osv = P.osv; dv.model = P.model;
  dv.br = P.br; dv.bv = P.bv; dv.eng = P.eng;
  dv.ua = st(ua, 300);
  dv.mob = isMob;
  dv.stable = !!did;                       // номер из localStorage, а не хэш адреса
  dv.ipHash = ipHash;                      // сам адрес в базу не попадает
  // то, что прислала страница о себе
  const sw = n0(qs.get("sw")), sh = n0(qs.get("sh"));
  if (sw && sh) { dv.sw = sw; dv.sh = sh; }
  const vw = n0(qs.get("vw")), vh = n0(qs.get("vh"));
  if (vw && vh) { dv.vw = vw; dv.vh = vh; }
  const dpr = n0(qs.get("dpr")); if (dpr) dv.dpr = Math.round(dpr * 100) / 100;
  const cd = n0(qs.get("cd")); if (cd) dv.cd = cd;
  const cc = n0(qs.get("cc")); if (cc) dv.cc = cc;
  const dm = n0(qs.get("dm")); if (dm) dv.dm = dm;
  const tp = n0(qs.get("tp")); if (tp || tp === 0) dv.tp = tp;
  const pf = st(qs.get("pf"), 40); if (pf) dv.pf = pf;
  const lg = st(qs.get("lg"), 20); if (lg) dv.lg = lg;
  const tz = st(qs.get("tz"), 40); if (tz) dv.tz = tz;
  const rf = st(qs.get("rf"), 120); if (rf) dv.rf = rf;
  // client hints — точнее User-Agent там, где браузер их отдаёт
  const chModel = ch("sec-ch-ua-model"); if (chModel) dv.chModel = chModel;
  const chPlat = ch("sec-ch-ua-platform"); if (chPlat) dv.chPlat = chPlat;
  const chPlatV = ch("sec-ch-ua-platform-version"); if (chPlatV) dv.chPlatV = chPlatV;
  const chArch = ch("sec-ch-ua-arch"); if (chArch) dv.chArch = chArch;
  const chBits = ch("sec-ch-ua-bitness"); if (chBits) dv.chBits = chBits;
  // сеть и география — от Cloudflare
  dv.city = city; dv.ctry = country;
  const reg = st(cf.region || "", 40); if (reg) dv.region = reg;
  const isp = st(cf.asOrganization || "", 60); if (isp) dv.isp = isp;
  if (cf.asn) dv.asn = cf.asn;
  const colo = st(cf.colo || "", 8); if (colo) dv.colo = colo;
  const proto = st(cf.httpProtocol || "", 12); if (proto) dv.proto = proto;
  const tls = st(cf.tlsVersion || "", 12); if (tls) dv.tls = tls;
  const al = st(request.headers.get("accept-language") || "", 40); if (al) dv.al = al;

  // ── ЖУРНАЛ: во сколько какое устройство какую страницу открыло ───
  // Пишем компактно: минута от начала суток и номера в словарях дня.
  // Развёрнутые строки за две недели раздули бы запись в KV в разы.
  if (!dd.dv) dd.dv = [];
  if (!dd.pv) dd.pv = [];
  if (!dd.ev) dd.ev = [];
  let di = dd.dv.indexOf(vid); if (di < 0) { dd.dv.push(vid); di = dd.dv.length - 1; }
  let pi = dd.pv.indexOf(p); if (pi < 0) { dd.pv.push(p); pi = dd.pv.length - 1; }
  // Потолок на день: запись в KV читается и пишется на каждый просмотр,
  // и раздувать её ради тысячного открытия одной и той же страницы незачем.
  if (dd.ev.length < 2500) dd.ev.push([hour * 60 + alm.getUTCMinutes(), di, pi]);

  // Подробный журнал держим десять дней: он нужен, чтобы разобрать «кто что
  // смотрел вчера», а не для истории. Сводные цифры по дням живут полгода.
  const evKeep = Object.keys(m.days).sort().slice(-10);
  Object.keys(m.days).forEach(function (k) {
    if (evKeep.indexOf(k) < 0 && m.days[k]) { delete m.days[k].ev; delete m.days[k].dv; delete m.days[k].pv; }
  });
  // Устройства, не заходившие два месяца, из списка убираем.
  const cut = new Date(now.getTime() - 60 * 86400 * 1000).toISOString();
  Object.keys(m.devs).forEach(function (k) {
    const o = m.devs[k];
    if ((o.last || "") < cut) { delete m.devs[k]; return; }
    // у активного устройства список дней иначе рос бы бесконечно
    if (o.days) {
      const dk = Object.keys(o.days).sort();
      if (dk.length > 90) { const t = {}; dk.slice(-90).forEach(function (x) { t[x] = o.days[x]; }); o.days = t; }
    }
  });

  // держим полгода, чтобы запись в KV не разрасталась
  const keep = Object.keys(m.days).sort().slice(-180);
  if (keep.length < Object.keys(m.days).length) {
    const trimmed = {};
    keep.forEach(function (k) { trimmed[k] = m.days[k]; });
    m.days = trimmed;
  }

  m.updated = now.toISOString();
  await env.PLAN.put(M_KEY, JSON.stringify(m));
}
async function sha256hex(s) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
/* Назвать устройство своими словами: «мой айфон», «ноут бухгалтерии».
   Без этого в списке стоят обезличенные номера, и понять, чьё устройство
   смотрело отчёт, нельзя. Пароль тот же, что и на саму страницу метрик. */
async function handleLabel(url, env) {
  const key = url.searchParams.get("key") || "";
  if ((await sha256hex(key)) !== METRICS_HASH) return jsonResp({ error: "Неверный пароль" }, 401);
  const vid = String(url.searchParams.get("vid") || "").slice(0, 40);
  const name = String(url.searchParams.get("name") || "").slice(0, 40).trim();
  if (!vid) return jsonResp({ error: "Не указано устройство" }, 400);
  const raw = await env.PLAN.get(M_KEY);
  const m = raw ? JSON.parse(raw) : null;
  if (!m || !m.devs || !m.devs[vid]) return jsonResp({ error: "Устройство не найдено" }, 404);
  m.devs[vid].name = name;
  await env.PLAN.put(M_KEY, JSON.stringify(m));
  return jsonResp({ ok: true, vid: vid, name: name });
}

async function handleStats(url, env) {
  const key = url.searchParams.get("key") || "";
  const h = await sha256hex(key);
  if (h !== METRICS_HASH) return jsonResp({ error: "Неверный пароль" }, 401);
  const raw = await env.PLAN.get(M_KEY);
  return jsonResp(raw ? JSON.parse(raw) : { pages: {}, updated: "" });
}
