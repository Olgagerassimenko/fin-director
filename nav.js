(function(){
  // счётчик просмотров для вкладки «Метрики»
  try{ fetch("/track?p="+encodeURIComponent(location.pathname),{method:"GET",keepalive:true}); }catch(e){}
  var pages=[
    {href:'index.html',icon:'🏠',label:'Главная'},
    {href:'дашборд_ддс_прямой.html',icon:'💸',label:'ДДС 2026'},
    {href:'дашборд_гугл_live.html',icon:'🗓️',label:'План оплат'},
    {href:'дашборд_ддс.html',icon:'🏦',label:'Про деньги'},
    {href:'дз_кз.html',icon:'⚖️',label:'ДЗ / КЗ'},
    {href:'продажи_2026.html',icon:'🛒',label:'Продажи ФУД ЗАВОД'},
    {href:'закуп.html',icon:'📦',label:'Закуп'},
    {href:'производство.html',icon:'🏭',label:'Производство'},
    {href:'sku360.html',icon:'🧩',label:'SKU 360'},
    {href:'себестоимость_маржа.html',icon:'👥',label:'Кто приносит прибыль'},
    {href:'дашборд_себестоимость_2025-2026.html',icon:'🧱',label:'Полная себестоимость'},
    {href:'рычаги.html',icon:'⚙️',label:'Рычаги прибыли'},
    {href:'опиу_2026.html',icon:'📊',label:'ОПиУ 2026'},
    {href:'опиу_аудит.html',icon:'🔎',label:'Аудит ОПиУ'},
{href:'nalogi_%D0%BE%D1%82%D1%87%D1%91%D1%82.html',icon:'🧾',label:'Налоги'},
    {href:'%D0%BA%D0%B0%D0%BB%D1%8C%D0%BA%D1%83%D0%BB%D1%8F%D1%82%D0%BE%D1%80.html',icon:'🧮',label:'Калькулятор'},
    {href:'olive.html',icon:'🥒',label:'Продажи Olive'},
    {href:'%D0%B6%D1%83%D1%80%D0%BD%D0%B0%D0%BB.html',icon:'🗂',label:'Журнал изменений'},
    {href:'%D0%B7%D0%B0%D1%80%D0%BF%D0%BB%D0%B0%D1%82%D0%B0.html',icon:'👥',label:'Зарплата'},
    {href:'%D1%8D%D1%82%D0%B8%D0%BA%D0%B5%D1%82%D0%BA%D0%B8.html',icon:'🏷',label:'Этикетки'}
  ];
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

  // ── Подпись внизу страницы (на всех дашбордах). Имя убрано 22.10.2026 ──
  function addSig(){
    if(document.getElementById('psig'))return;
    var f=document.createElement('footer');f.id='psig';
    f.style.cssText='text-align:center;color:#475569;font-size:12px;line-height:1.7;padding:22px 16px 34px;border-top:1px solid #1e293b;margin-top:22px;font-family:Inter,-apple-system,sans-serif';
    f.innerHTML='Система «Пульс» · Фуд Завод<br>данные из iiko, обновляются ежедневно<br><a href="/metrics.html" style="color:#a78bfa;text-decoration:none;font-weight:600">🔒 Аналитика посещений</a>';
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

  /* ── Откуда данные: плашка внизу слева на каждой странице ──────────────
     Пульс собирается из нескольких систем, и по странице это не видно.
     SRC — что тянет именно эта страница; GAP — чего в O·ERP нет и что
     поэтому пока живёт только в айко. pulse-source-badge */
  var SRC={
    'index.html':['айко · 1С · Google · Битрикс','Сводка: продажи, закуп, деньги — айко; налоги и реализация — 1С; план оплат — Google; оплаты — Битрикс.'],
    'дашборд_ддс_прямой.html':['айко','Проводки по денежным счетам (отчёт «Транзакции»), остатки — отчёт по счетам.'],
    'дашборд_ддс.html':['айко · Google','Остатки денег из айко, план платежей — из Google-таблицы.'],
    'дашборд_гугл_live.html':['Google','Таблица «План оплат», лист текущего месяца.'],
    'дз_кз.html':['Google','Книга ДЗ/КЗ: столбцы «ДЗ на …» и «Баланс по поставщикам».'],
    'продажи_2026.html':['айко · сверка с O·ERP','Выручка расходных накладных за вычетом возвратов. С 06.11.2026 накладные заводят в O·ERP — см. блок «Сверка с O·ERP» вверху страницы.'],
    'olive.html':['айко','Контрагент 98 (O-live) отдельно от продаж завода.'],
    'закуп.html':['айко','Приходные накладные и поставщики.'],
    'производство.html':['айко','Выпуск, разделка, переработка, списания.'],
    'sku360.html':['айко','Продажи, себестоимость и остатки по позициям.'],
    'себестоимость_маржа.html':['айко','Маржа по позициям и контрагентам.'],
    'дашборд_себестоимость_2025-2026.html':['айко','ОПиУ и контрагенты.'],
    'рычаги.html':['айко','Цены, потери, ассортимент.'],
    'опиу_2026.html':['айко','Счета ОПиУ, обороты по месяцам.'],
    'опиу_аудит.html':['айко · 1С','Сверка разносок бухгалтерии с айко.'],
    'реализация.html':['1С','Регистр «Типовой», счета 6010/6020/6030, по OData.'],
    'nalogi_отчёт.html':['1С','Налоговые регистры и платежи, по OData.'],
    'nalogi_analitika_отчёт.html':['1С','Налоговая аналитика по OData.'],
    'bitrix_отчёт_оплаты.html':['Битрикс','Сделки и оплаты из CRM.'],
    'упаковка.html':['айко','Склады, движение и поставщики упаковки.'],
    'услуги.html':['айко','Акты и услуги контрагентов.'],
    'просрочка.html':['айко','Остатки со сроками годности.'],
    'передача.html':['айко','Передачи между подразделениями.'],
    'маймарт.html':['айко','Возвраты и полная себестоимость Маймарт.'],
    'азс.html':['айко','Канал 99 — РП АЗС.'],
    'дфз.html':['айко','Канал 85 — ДФЗ.'],
    'яндекс.html':['айко','Каналы Яндекс Лавка и дарксторы.'],
    'повышение_цен.html':['айко','Маржа и цены по позициям.'],
    'развитие_ассортимента.html':['айко','Ассортимент и продажи по позициям.'],
    'план.html':['Google','План оплат.'],
    'баланс.html':['1С','Оборотно-сальдовая по OData.'],
    'сальдо.html':['1С','Остатки по счетам из бухгалтерии.'],
    'калькулятор.html':['айко','Техкарты и себестоимость позиций.'],
    'зарплата.html':['айко','Счёт оплаты труда, выплаты по подразделениям.'],
    'этикетки.html':['айко','Номенклатура и сроки хранения.'],
    'склады.html':['айко','Остатки и движение по складам.'],
    'журнал.html':['репозиторий','История изменений сайта из git.']
  };
  var GAP='Чего в O·ERP нет (и это берём только из айко): техкарты и калькуляции · остатки и движение по складам · баланс по контрагентам · чеки и кассовые смены · сотрудники и выплаты · сроки и способы хранения.';
  function srcBadge(){
    try{
      if(document.getElementById('psrc'))return;
      var key=decodeURIComponent(cur), info=SRC[key]||SRC[cur];
      if(!info) info=['айко','Данные ночного прогона из айко.'];
      var ss=document.createElement('style');
      ss.textContent='#psrc{position:fixed;right:16px;bottom:12px;z-index:9998;font-family:Inter,sans-serif;display:flex;flex-direction:column;align-items:flex-end}'
        +'#psrc .pb{display:inline-flex;align-items:center;gap:6px;background:rgba(15,23,42,.92);border:1px solid #27354f;'
        +'color:#94a3b8;border-radius:999px;padding:6px 11px;font-size:11px;font-weight:700;cursor:pointer;'
        +'box-shadow:0 3px 12px rgba(0,0,0,.35)}'
        +'#psrc .pb:hover{color:#e2e8f0;border-color:#3b4a66}'
        +'#psrc .pp{display:none;max-width:330px;margin-bottom:8px;background:rgba(15,23,42,.97);border:1px solid #27354f;'
        +'border-radius:12px;padding:12px 14px;font-size:11.5px;line-height:1.6;color:#cbd5e1;box-shadow:0 8px 26px rgba(0,0,0,.5)}'
        +'#psrc.open .pp{display:block}'
        +'@media(max-width:640px){#psrc{right:8px;bottom:8px}#psrc .pp{max-width:72vw}}';
      document.head.appendChild(ss);
      var d=document.createElement('div'); d.id='psrc';
      d.innerHTML='<div class="pp"><b style="color:#e2e8f0">Источник данных</b><br>'+info[1]
        +'<div style="margin-top:8px;color:#64748b">'+GAP+'</div></div>'
        +'<div class="pb">ⓘ источник: '+info[0]+'</div>';
      d.querySelector('.pb').addEventListener('click',function(){d.classList.toggle('open');});
      document.body.appendChild(d);
    }catch(e){}
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',srcBadge);}else{srcBadge();}

})();
