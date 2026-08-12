# -*- coding: utf-8 -*-
"""
bitrix_report.py — отчёт «Битрикс · Оплаты» (только чтение) для системы Пульс.
Запускается в пайплайне каждые 3 часа; вебхук берётся из секрета BITRIX_WEBHOOK.

Собирает то, что доступно вебхуку: смарт-процессы «Заявки на оплату» (если созданы
и у вебхука есть права), иначе — сделки CRM. Пишет:
    bitrix_log.txt              — что нашёл / диагностика прав
    bitrix_отчёт_оплаты.html    — красивый отчёт в стиле Пульса
"""
import os, json, urllib.request, urllib.error, datetime, re, sys

WH = (os.environ.get("BITRIX_WEBHOOK") or "").strip().rstrip("/")
if "/rest/" in WH:
    _base, _rest = WH.split("/rest/", 1)
    _parts = [x for x in _rest.split("/") if x]
    if len(_parts) >= 2:
        WH = _base + "/rest/" + _parts[0] + "/" + _parts[1]
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = open(os.path.join(HERE, "bitrix_log.txt"), "w", encoding="utf-8")
def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

def call(method, params=None):
    if not WH:
        return None, "нет BITRIX_WEBHOOK"
    url = WH + "/" + method + ".json"
    body = json.dumps(params or {}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.loads(r.read().decode("utf-8"))
            return j.get("result"), j.get("error_description") or j.get("error")
    except urllib.error.HTTPError as e:
        try: j = json.loads(e.read().decode("utf-8")); return None, j.get("error_description") or f"HTTP {e.code}"
        except Exception: return None, f"HTTP {e.code}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def num(v):
    try: return float(str(v).replace(" ", "").replace(",", ".") or 0)
    except Exception: return 0.0

def main():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5)  # Алматы UTC+5
    today = now.date()
    log(f"Битрикс · оплаты · {now:%d.%m.%Y %H:%M} (Алматы)")
    state = {"portal": "—", "scope": [], "conn": False, "admin": None}
    payments = []          # нормализованные заявки на оплату
    source = None          # откуда взяли (смарт-процесс / сделки)
    diag = []              # что доступно/недоступно

    if not WH:
        log("[!] Секрет BITRIX_WEBHOOK не задан.")
        write_html(now, state, payments, source, diag); return
    state["portal"] = WH.split("/rest/")[0] if "/rest/" in WH else "—"

    prof, err = call("profile")
    if prof:
        state["conn"] = True
        state["admin"] = prof.get("ADMIN")
        log("profile: ok ·", prof.get("NAME"), prof.get("LAST_NAME"), "· admin=", prof.get("ADMIN"))
    else:
        log("profile: ошибка —", err)
    scope, err = call("scope")
    state["scope"] = scope if isinstance(scope, list) else []
    log("scope:", state["scope"] or err)

    # 1) Смарт-процессы «Заявки на оплату» (основной источник)
    types, err = call("crm.type.list")
    if types and isinstance(types, dict) and types.get("types"):
        for t in types["types"]:
            title = t.get("title") or ""
            etid = t.get("entityTypeId")
            log(f"смарт-процесс: entityTypeId={etid} «{title}»")
            if re.search(r"оплат|заявк|платеж", title, re.I):
                items, e2 = call("crm.item.list", {"entityTypeId": etid, "start": 0})
                arr = items.get("items", []) if isinstance(items, dict) else []
                if arr:
                    source = f"Смарт-процесс «{title}»"
                    for it in arr:
                        payments.append({
                            "id": it.get("id"),
                            "title": it.get("title") or ("Заявка #" + str(it.get("id"))),
                            "sum": num(it.get("opportunity") or it.get("ufCrm_SUM") or 0),
                            "stage": it.get("stageId") or "",
                            "created": (it.get("createdTime") or "")[:10],
                        })
                    break
        diag.append("Смарт-процессы: доступны")
    else:
        diag.append("Смарт-процессы: нет доступа (" + str(err) + ")")
        log("смарт-процессы: нет/нет доступа —", err)

    # 2) Фолбэк — сделки CRM за 60 дней (что вебхук точно может)
    if not payments:
        frm = (today - datetime.timedelta(days=60)).isoformat()
        deals, err = call("crm.deal.list", {
            "filter": {">=DATE_CREATE": frm}, "order": {"DATE_CREATE": "DESC"},
            "select": ["ID", "TITLE", "OPPORTUNITY", "STAGE_ID", "DATE_CREATE"]})
        if isinstance(deals, list) and deals:
            source = "Сделки CRM (за 60 дней)"
            for d in deals:
                payments.append({"id": d.get("ID"), "title": d.get("TITLE") or ("Сделка #" + str(d.get("ID"))),
                                 "sum": num(d.get("OPPORTUNITY")), "stage": d.get("STAGE_ID") or "",
                                 "created": (d.get("DATE_CREATE") or "")[:10]})
            diag.append(f"Сделки: {len(deals)} за 60 дней")
        elif err:
            diag.append("Сделки: " + str(err))
            log("crm.deal.list:", err)
        else:
            diag.append("Сделки: за 60 дней нет")

    write_html(now, state, payments, source, diag)
    log(f"\nГотово · записей: {len(payments)} · источник: {source or '—'}")

def write_html(now, state, payments, source, diag):
    html = build_html(now, state, payments, source, diag)
    with open(os.path.join(HERE, "bitrix_отчёт_оплаты.html"), "w", encoding="utf-8") as f:
        f.write(html)

def fmt(v):
    return ("{:,.0f}".format(v)).replace(",", " ")

def build_html(now, state, payments, source, diag):
    total = sum(p["sum"] for p in payments)
    cnt = len(payments)
    # разбивка по стадии
    by_stage = {}
    for p in payments:
        by_stage[p["stage"]] = by_stage.get(p["stage"], {"n": 0, "s": 0.0})
        by_stage[p["stage"]]["n"] += 1; by_stage[p["stage"]]["s"] += p["sum"]

    conn_badge = ('<span style="color:#34d399">● подключено</span>' if state["conn"]
                  else '<span style="color:#fb7185">● нет связи</span>')
    scope_txt = ", ".join(state["scope"]) or "—"
    admin_note = ("" if state.get("admin") else
                  " · <span style=\"color:#fbbf24\">пользователь не админ — часть прав может быть ограничена</span>")

    # KPI
    kpi = f'''<div class="kpi">
      <div class="c"><div class="l">💳 Заявок / записей</div><div class="v">{cnt}</div><div class="s">источник: {source or '—'}</div></div>
      <div class="c"><div class="l">💰 Сумма</div><div class="v">{fmt(total)} <span style="font-size:15px">₸</span></div><div class="s">по всем записям</div></div>
      <div class="c"><div class="l">🔌 Подключение</div><div class="v" style="font-size:17px">{conn_badge}</div><div class="s">права вебхука: {scope_txt}{admin_note}</div></div>
    </div>'''

    if payments:
        rows = ""
        for p in sorted(payments, key=lambda x: -x["sum"])[:100]:
            rows += (f'<tr><td class="l">{p["title"]}</td><td>{p["created"]}</td>'
                     f'<td>{p["stage"]}</td><td class="r"><b>{fmt(p["sum"])} ₸</b></td></tr>')
        stage_rows = ""
        for st, d in sorted(by_stage.items(), key=lambda x: -x[1]["s"]):
            stage_rows += f'<tr><td class="l">{st or "—"}</td><td class="r">{d["n"]}</td><td class="r"><b>{fmt(d["s"])} ₸</b></td></tr>'
        body = f'''
      <div class="card"><h3>📊 По стадиям</h3>
        <table class="z"><thead><tr><th class="l">Стадия</th><th class="r">Кол-во</th><th class="r">Сумма</th></tr></thead><tbody>{stage_rows}</tbody></table></div>
      <div class="card"><h3>📋 Записи ({cnt})</h3>
        <table class="z"><thead><tr><th class="l">Наименование</th><th>Создано</th><th>Стадия</th><th class="r">Сумма</th></tr></thead><tbody>{rows}</tbody></table></div>'''
    else:
        body = f'''
      <div class="card note">
        <h3>⏳ Данных по оплатам пока нет</h3>
        <p>Вебхук подключён (права: <b>{scope_txt}</b>), но структурированных заявок на оплату не найдено. Чтобы отчёт наполнялся, нужно два шага:</p>
        <ol>
          <li><b>Создать смарт-процесс «Заявки на оплату»</b> в Bitrix24 (CRM → Смарт-процессы) с полями <i>Подразделение, Статья, Сумма, Срок, Стадия</i>. Тогда каждая оплата — это карточка, которую отчёт читает.</li>
          <li><b>Дать вебхуку права на смарт-процессы</b> (сейчас только «crm»). Нужен вебхук с доступом к CRM-смарт-процессам (или локальное приложение) — иначе REST их не видит («Доступ запрещён»).</li>
        </ol>
        <p style="color:#8798ab">Диагностика: {" · ".join(diag) or "—"}. Полный лог — в <code>bitrix_log.txt</code>.</p>
      </div>'''

    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Битрикс · Оплаты · {now:%d.%m.%Y}</title>
<style>
:root{{--ink:#f4f7fb;--ink2:#b9c5d3;--mut:#8798ab;--line:rgba(255,255,255,.10);--line2:rgba(255,255,255,.06)}}
*{{box-sizing:border-box}}body{{font-family:-apple-system,Segoe UI,Arial,sans-serif;background:#080d16;color:var(--ink);margin:0;padding:0}}
.wrap{{max-width:1000px;margin:0 auto;padding:22px 18px 40px}}
.hdr{{background:linear-gradient(135deg,#2563eb,#1e3a8a);border-radius:16px;padding:20px 24px;border-top:3px solid rgba(255,255,255,.5);box-shadow:0 16px 42px -24px rgba(37,99,235,.7)}}
.hdr h1{{margin:0;font-size:23px;font-weight:800;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.hdr .sub{{color:#dbeafe;font-size:13px;margin-top:5px}}
.upd{{display:inline-flex;align-items:center;gap:7px;background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.35);padding:5px 12px;border-radius:999px;font-size:12.5px;font-weight:700;margin-top:11px}}
.kpi{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0}}
@media(max-width:640px){{.kpi{{grid-template-columns:1fr}}}}
.c{{background:linear-gradient(162deg,#0f1b29,#0b141f);border:1px solid var(--line);border-radius:14px;padding:14px 16px}}
.c .l{{font-size:12px;color:var(--ink2);font-weight:700}}.c .v{{font-size:26px;font-weight:800;margin-top:3px}}.c .s{{font-size:11px;color:var(--mut);margin-top:3px}}
.card{{background:linear-gradient(162deg,#0f1b29,#0b141f);border:1px solid var(--line);border-radius:14px;padding:14px 18px;margin-bottom:16px}}
.card h3{{margin:2px 0 10px;font-size:15px}}
.note ol{{margin:8px 0 0;padding-left:20px;line-height:1.6}}.note li{{margin-bottom:6px}}
table.z{{width:100%;border-collapse:collapse;font-size:13px}}
table.z th{{text-align:right;color:var(--mut);font-weight:700;font-size:11.5px;padding:6px 10px;border-bottom:1px solid var(--line)}}
table.z td{{text-align:right;padding:8px 10px;border-bottom:1px solid var(--line2);white-space:nowrap}}
table.z .l{{text-align:left;white-space:normal}}table.z .r{{text-align:right}}
</style></head>
<body><div class="wrap">
  <div class="hdr"><h1>💳 Битрикс · Оплаты</h1>
    <div class="sub">Мастерская Сегодня · согласование и контроль оплат из Bitrix24 · только чтение</div>
    <div class="upd">🔄 обновлено {now:%d.%m.%Y %H:%M} · Битрикс · автообновление каждые 3 часа</div>
  </div>
  {kpi}
  {body}
  <p style="color:#64748b;font-size:11.5px;margin-top:8px">Система «Пульс» · робот по оплатам (только чтение) · портал: {state["portal"]}</p>
</div></body></html>'''

if __name__ == "__main__":
    main()
