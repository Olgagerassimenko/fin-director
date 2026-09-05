(function(){
  /* Счётчик просмотров для вкладки «Метрики».
     Живёт именно здесь, а не в воркере: Cloudflare отдаёт статику (в том
     числе HTML) в обход скрипта воркера, поэтому вставка счётчика через
     HTMLRewriter до страницы не доезжает — nav.js подключён на каждом
     дашборде и делает это надёжно.
     Кроме адреса страницы отправляем паспорт устройства: экран, ядра,
     память, язык, часовой пояс — чтобы в метриках было видно не только
     «сколько открытий», но и какое устройство что смотрело. Постоянный
     номер устройства случайный, лежит в localStorage этого браузера и
     нужен только чтобы телефон не считался новым каждый раз, когда
     оператор выдаёт другой адрес. */
  try{
    var K='pulse_did', d='';
    try{
      d = localStorage.getItem(K) || '';
      if(!d){
        d = (self.crypto && crypto.randomUUID) ? crypto.randomUUID()
            : (Date.now().toString(36) + Math.random().toString(36).slice(2));
        localStorage.setItem(K, d);
      }
    }catch(e){}
    var n = navigator, sc = screen, tzo = {};
    try{ tzo = Intl.DateTimeFormat().resolvedOptions(); }catch(e){}
    var q = 'p=' + encodeURIComponent(location.pathname)
      + '&d='  + encodeURIComponent(String(d).slice(0,40))
      + '&sw=' + (sc.width||0)  + '&sh=' + (sc.height||0)
      + '&vw=' + (window.innerWidth||0) + '&vh=' + (window.innerHeight||0)
      + '&dpr='+ (window.devicePixelRatio||1) + '&cd=' + (sc.colorDepth||0)
      + '&cc=' + (n.hardwareConcurrency||0) + '&dm=' + (n.deviceMemory||0)
      + '&tp=' + (n.maxTouchPoints||0)
      + '&pf=' + encodeURIComponent(n.platform||'')
      + '&lg=' + encodeURIComponent(n.language||'')
      + '&tz=' + encodeURIComponent(tzo.timeZone||'')
      + '&rf=' + encodeURIComponent((document.referrer||'').slice(0,120));
    fetch('/track?' + q, {method:'GET', keepalive:true});
  }catch(e){}
  var pages=[
    {href:'index.html',icon:'🏠',label:'Главная'},
    {href:'дашборд_ддс_прямой.html',icon:'💸',label:'ДДС 2026'},
    {href:'дашборд_гугл_live.html',icon:'🗓️',label:'План оплат'},
    {href:'дашборд_ддс.html',icon:'🏦',label:'Про деньги'},
    {href:'дз_кз.html',icon:'⚖️',label:'ДЗ / КЗ'},
    {href:'продажи_2026.html',icon:'🛒',label:'Продажи'},
    {href:'закуп.html',icon:'📦',label:'Закуп'},
    {href:'производство.html',icon:'🏭',label:'Производство'},
    {href:'sku360.html',icon:'🧩',label:'SKU 360'},
    {href:'себестоимость_маржа.html',icon:'👥',label:'Кто приносит прибыль'},
    {href:'дашборд_себестоимость_2025-2026.html',icon:'🧱',label:'Полная себестоимость'},
    {href:'рычаги.html',icon:'⚙️',label:'Рычаги прибыли'},
    {href:'опиу_2026.html',icon:'📊',label:'ОПиУ 2026'},
    {href:'опиу_аудит.html',icon:'🔎',label:'Аудит ОПиУ'}
  ];
  // Список страниц публикуем наружу: путеводитель берёт из него число
  // отчётов, чтобы оно не устаревало при каждом новом листе.
  try{ window.PULSE_PAGES = pages; }catch(e){}
  var cur=location.pathname.split('/').pop()||'index.html';
  var s=document.createElement('style');
  s.textContent=
    '#pnav{position:fixed;left:0;width:56px;background:#1a1035;display:flex;flex-direction:column;align-items:center;padding-top:8px;gap:4px;z-index:9999;box-shadow:3px 0 16px rgba(0,0,0,.4);transition:width .2s;overflow:hidden}'
    +'#pnav:hover{width:180px}'
    +'#pnav a{display:flex;align-items:center;gap:10px;width:100%;padding:10px 16px;color:rgba(255,255,255,.6);text-decoration:none;font-family:Inter,sans-serif;font-size:12px;font-weight:600;transition:all .15s;white-space:nowrap;overflow:hidden}'
    +'#pnav a:hover{background:rgba(255,255,255,.1);color:#fff}'
    +'#pnav a.active{background:rgba(124,58,237,.5);color:#fff;border-right:2px solid #a78bfa}'
    +'#pnav .ni{font-size:18px;flex-shrink:0;width:24px;text-align:center}'
    +'#pnav .nl{opacity:0;transition:opacity .15s .05s;font-size:11px;pointer-events:none}'
    +'#pnav:hover .nl{opacity:1}'
    +'body{padding-left:56px!important}'
    /* Меню отъедает 56px, и сетки, свёрстанные под всю ширину, начинали вылезать
       вправо горизонтальной прокруткой (ДЗ/КЗ +28px, ОПиУ 2025–2026 +36px).
       min-width:0 разрешает элементу сжаться до своей колонки — оформление
       страниц при этом не меняется, это стандартное лечение переполнения grid. */
    +'[class*=grid]>*,[class*=row]>*{min-width:0}'
    +'.topbar,.topbar-new{position:sticky!important;top:0!important;z-index:10000!important;margin-left:-56px!important;width:calc(100% + 56px)!important;box-sizing:border-box!important;padding-left:72px!important}'
    +'@media(max-width:640px){#pnav{width:46px!important}#pnav:hover{width:46px!important}#pnav a{padding:11px 0!important;justify-content:center!important}#pnav .nl{display:none!important}#pnav .ni{width:100%!important}body{padding-left:46px!important}.topbar,.topbar-new{margin-left:-46px!important;width:calc(100% + 46px)!important;padding-left:56px!important}}'
    +'@media(max-width:640px){html,body{overflow-x:hidden!important}.pnav-tw{overflow-x:auto!important;-webkit-overflow-scrolling:touch;max-width:100%}.pnav-tw>table{min-width:max-content}}'
    +'@media(max-width:640px){svg{max-width:100%!important;min-width:0!important;height:auto}canvas{max-width:100%!important}}';
  document.head.appendChild(s);
  var h='';
  for(var i=0;i<pages.length;i++){var p=pages[i];var a=(p.href===cur)?' active':'';h+='<a href="'+p.href+'"class="'+a+'"><span class="ni">'+p.icon+'</span><span class="nl">'+p.label+'</span></a>';}
  var n=document.createElement('nav');n.id='pnav';n.innerHTML=h;

  // Вкладка «Путеводитель» у правого края убрана 02.09.2026: она висела
  // поверх страниц и закрывала правую колонку таблиц (на закупе — «% выр.»).
  // Вход в путеводитель остался один — плитка на главной.

  // Скрипт может стоять в <head> — тогда document.body ещё не существует.
  function mountNav(){
    if(document.getElementById('pnav'))return;
    document.body.insertBefore(n,document.body.firstChild);
    positionNav(); stickTabs();
  }
  if(document.body){ document.body.insertBefore(n,document.body.firstChild); }
  else { document.addEventListener('DOMContentLoaded',mountNav); }
  // Position sidebar below topbar after load
  function positionNav(){
    var tb=document.querySelector('.topbar,.topbar-new');
    var nav=document.getElementById('pnav');
    if(tb&&nav){
      var h=tb.getBoundingClientRect().height;
      nav.style.top=h+'px';
      nav.style.height='calc(100vh - '+h+'px)';
    }
  }
  // Строка вкладок прилипает сразу под шапкой. Без этого при прокрутке она
  // уходит под .topbar (z-index 10000) и кнопки перестают нажиматься.
  function stickTabs(){
    var tb=document.querySelector('.topbar,.topbar-new'); if(!tb)return;
    var h=Math.round(tb.getBoundingClientRect().height);
    var bg=(getComputedStyle(document.body).backgroundColor)||'#0b1220';
    if(bg==='rgba(0, 0, 0, 0)'||bg==='transparent')bg='#0b1220';
    var list=document.querySelectorAll('.tabs');
    for(var i=0;i<list.length;i++){
      var t=list[i];
      if(t.getAttribute('data-pnav-stick')!=='1'){
        if(getComputedStyle(t).position!=='static')continue;   // страница уже сама решила, как их держать
        t.style.position='sticky'; t.style.zIndex='9998';
        t.style.background=bg; t.style.paddingTop='9px'; t.style.paddingBottom='9px';
        t.style.marginBottom='6px';
        t.setAttribute('data-pnav-stick','1');
      }
      t.style.top=h+'px';
    }
  }
  function fitAll(){ positionNav(); stickTabs(); }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',fitAll);}
  else{fitAll();}
  window.addEventListener('load',fitAll);
  window.addEventListener('resize',fitAll);

  // ── Подпись / автор внизу страницы (на всех дашбордах) ──
  function addSig(){
    if(document.getElementById('psig'))return;
    var f=document.createElement('footer');f.id='psig';
    f.style.cssText='text-align:center;color:#475569;font-size:12px;line-height:1.7;padding:22px 16px 34px;border-top:1px solid #1e293b;margin-top:22px;font-family:Inter,-apple-system,sans-serif';
    f.innerHTML='Система «Пульс» · Фуд Завод<br><b style="color:#94a3b8">Ольга Герасименко</b> · финансовый директор · данные из iiko, обновляются ежедневно<br><a href="/metrics.html" style="color:#a78bfa;text-decoration:none;font-weight:600">🔒 Аналитика посещений</a>';
    document.body.appendChild(f);
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',addSig);}else{addSig();}

  // ── Мобильная адаптация: все таблицы делаем горизонтально прокручиваемыми ──
  function _isScroll(el){try{var o=getComputedStyle(el).overflowX;return o==='auto'||o==='scroll';}catch(e){return false;}}
  function wrapTables(){
    if(window.innerWidth>640)return;
    var ts=document.querySelectorAll('table');
    for(var i=0;i<ts.length;i++){var t=ts[i];
      if(t.closest&&t.closest('.pnav-tw'))continue;
      var p=t.parentElement; if(p&&(_isScroll(p)||p.className&&/wrap|scroll|tbl/i.test(p.className)))continue;
      var w=document.createElement('div');w.className='pnav-tw';
      t.parentNode.insertBefore(w,t);w.appendChild(t);
    }
  }
  function scheduleWrap(){wrapTables();setTimeout(wrapTables,400);setTimeout(wrapTables,1200);setTimeout(wrapTables,2600);}
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',scheduleWrap);}else{scheduleWrap();}
  window.addEventListener('load',scheduleWrap);
  try{var _mo=new MutationObserver(function(){if(window.innerWidth<=640){clearTimeout(window.__pnwt);window.__pnwt=setTimeout(wrapTables,300);}});_mo.observe(document.body,{childList:true,subtree:true});}catch(e){}
})();