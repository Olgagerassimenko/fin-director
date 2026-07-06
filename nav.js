(function(){
  var pages=[
    {href:'index.html',icon:'🏠',label:'ПУЛЬС'},
    {href:'дашборд_гугл_live.html',icon:'⚡',label:'ДДС Live'},
    {href:'опиу_2025_2026.html',icon:'📈',label:'ОПиУ'},
    {href:'дашборд_дддс_динамик.html',icon:'📊',label:'ДДС Excel'},
    {href:'дашборд_ДДС.html',icon:'💰',label:'ДДС'},
    {href:'дашборд_продажи.html',icon:'🛒',label:'Продажи'},
    {href:'дашборд_себестоимость_2025-2026.html',icon:'💹',label:'Себест.'},
    {href:'дашборд_sku_2025-2026.html',icon:'🔍',label:'SKU онлайн'},
    {href:'дашборд_sku_себестоимость.html',icon:'💲',label:'SKU Себест.'}
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
    +'.topbar,.topbar-new{position:sticky!important;top:0!important;z-index:10000!important;margin-left:-56px!important;width:calc(100% + 56px)!important;box-sizing:border-box!important;padding-left:72px!important}';
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
})();