(function(){
  // счётчик просмотров для вкладки «Метрики»
  try{ fetch("/track?p="+encodeURIComponent(location.pathname),{method:"GET",keepalive:true}); }catch(e){}
  var pages=[
    {href:'index.html',icon:'🏠',label:'Главная'},
    {href:'дашборд_ддс_прямой.html',icon:'💧',label:'ДДС · деньги'},
    {href:'дз_кз.html',icon:'🧾',label:'ДЗ / КЗ'},
    {href:'продажи_2026.html',icon:'🛒',label:'Продажи'},
    {href:'дашборд_sku_iiko.html',icon:'🔍',label:'SKU 360'},
    {href:'себестоимость_маржа.html',icon:'💰',label:'Себестоимость · маржа'},
    {href:'metrics.html',icon:'🔒',label:'Метрики'}
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
    +'.topbar,.topbar-new{position:sticky!important;top:0!important;z-index:10000!important;margin-left:-56px!important;width:calc(100% + 56px)!important;box-sizing:border-box!important;padding-left:72px!important}'
    +'@media(max-width:640px){#pnav{width:46px!important}#pnav:hover{width:46px!important}#pnav a{padding:11px 0!important;justify-content:center!important}#pnav .nl{display:none!important}#pnav .ni{width:100%!important}body{padding-left:46px!important}.topbar,.topbar-new{margin-left:-46px!important;width:calc(100% + 46px)!important;padding-left:56px!important}}'
    +'@media(max-width:640px){html,body{overflow-x:hidden!important}.pnav-tw{overflow-x:auto!important;-webkit-overflow-scrolling:touch;max-width:100%}.pnav-tw>table{min-width:max-content}}'
    +'@media(max-width:640px){svg{max-width:100%!important;min-width:0!important;height:auto}canvas{max-width:100%!important}}';
  document.head.appendChild(s);
  var h='';
  for(var i=0;i<pages.length;i++){var p=pages[i];var a=(p.href===cur)?' active':'';h+='<a href="'+p.href+'"class="'+a+'"><span class="ni">'+p.icon+'</span><span class="nl">'+p.label+'</span></a>';}
  var n=document.createElement('nav');n.id='pnav';n.innerHTML=h;
  document.body.insertBefore(n,document.body.firstChild);
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
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',positionNav);}
  else{positionNav();}

  // ── Подпись / автор внизу страницы (на всех дашбордах) ──
  function addSig(){
    if(document.getElementById('psig'))return;
    var f=document.createElement('footer');f.id='psig';
    f.style.cssText='text-align:center;color:#475569;font-size:12px;line-height:1.7;padding:22px 16px 34px;border-top:1px solid #1e293b;margin-top:22px;font-family:Inter,-apple-system,sans-serif';
    f.innerHTML='Система «Пульс» · Фуд завод (Мастерская Сегодня)<br><b style="color:#94a3b8">Ольга Герасименко</b> · финансовый директор · данные из iiko, обновляются ежедневно<br><a href="/metrics.html" style="color:#a78bfa;text-decoration:none;font-weight:600">🔒 Аналитика посещений</a>';
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