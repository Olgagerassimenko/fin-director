# -*- coding: utf-8 -*-
"""
bitrix_report.py — робот «Битрикс · Оплаты» для системы Пульс (только чтение).

Заявки живут в бизнес-процессах «Мои процессы». Вебхуку они не отдаются:
у него область только crm, а bizproc отвечает insufficient_scope. Поэтому
работают два пути, в таком порядке:

  1) РАЗВЕДКА. Робот проверяет, не появился ли доступ — смарт-процесс CRM,
     список «Списков», задачи. Как только что-то отдаётся, это видно в логе,
     и можно включать автосборку.
  2) ВЫГРУЗКА. Пока доступа нет, отчёт обновляется файлом: положите выгрузку
     из Битрикса рядом под именем bitrix_выгрузка.csv (или .xlsx) — робот
     пересоберёт таблицу и шапку отчёта. Без файла страница не трогается.

Строка отчёта: дата≡тип≡заявитель≡город≡сумма≡статус≡комментарий≡файл
"""
import os, json, re, csv, io, datetime, urllib.request, urllib.error

WH = (os.environ.get("BITRIX_WEBHOOK") or "").strip().rstrip("/")
if "/rest/" in WH:
    _base, _rest = WH.split("/rest/", 1)
    _parts = [x for x in _rest.split("/") if x]
    if len(_parts) >= 2:
        WH = _base + "/rest/" + _parts[0] + "/" + _parts[1]
HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "bitrix_отчёт_оплаты.html")
LOG = open(os.path.join(HERE, "bitrix_log.txt"), "w", encoding="utf-8")
FEEDS = ["bitrix_выгрузка.csv", "bitrix_выгрузка.xlsx", "bitrix_выгрузка.xls"]

def log(*a):
    t = " ".join(str(x) for x in a); print(t); LOG.write(t + "\n"); LOG.flush()

def call(method, params=None):
    if not WH:
        return None, "нет вебхука"
    url = WH + "/" + method + ".json"
    body = json.dumps(params or {}).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode("utf-8"))
            return None, j.get("error_description") or j.get("error") or str(e)
        except Exception:
            return None, str(e)
    except Exception as e:
        return None, str(e)

def probe():
    """Разведка: не появился ли доступ к заявкам через API."""
    j, err = call("scope")
    log("scope:", (j.get("result") if j else None) or err)
    found = []
    for method, params, what in [
        ("crm.type.list", {}, "смарт-процессы CRM"),
        ("lists.get", {"IBLOCK_TYPE_ID": "lists"}, "универсальные списки"),
        ("bizproc.workflow.instance.list", {}, "экземпляры бизнес-процессов"),
        ("tasks.task.list", {"select": ["ID", "TITLE"], "start": 0}, "задачи"),
    ]:
        j, err = call(method, params)
        if j and j.get("result") is not None:
            res = j["result"]
            n = len(res) if isinstance(res, list) else len(res.get("types", res) or [])
            log("  %-34s доступно, записей: %s" % (method, n))
            found.append(method)
        else:
            log("  %-34s нет доступа (%s)" % (method, str(err)[:60]))
    return found

# ── чтение выгрузки ────────────────────────────────────────────
def read_feed(path):
    """Строки выгрузки -> список словарей по заголовкам первой строки."""
    if path.lower().endswith((".xlsx", ".xls")):
        try:
            import openpyxl
        except ImportError:
            log("   для xlsx нужен openpyxl; сохраните выгрузку в CSV"); return []
        ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
        rows = [[("" if c is None else str(c)) for c in r] for r in ws.iter_rows(values_only=True)]
    else:
        raw = open(path, "rb").read()
        for enc in ("utf-8-sig", "cp1251", "utf-8"):
            try:
                txt = raw.decode(enc); break
            except UnicodeDecodeError:
                continue
        else:
            log("   не удалось прочитать кодировку файла"); return []
        delim = ";" if txt.count(";") >= txt.count(",") else ","
        rows = [r for r in csv.reader(io.StringIO(txt), delimiter=delim)]
    rows = [r for r in rows if any(str(x).strip() for x in r)]
    if len(rows) < 2:
        log("   в выгрузке нет строк"); return []
    head = [str(x).strip().lower() for x in rows[0]]
    return [dict(zip(head, [str(x).strip() for x in r])) for r in rows[1:]]

def pick(d, *keys):
    """Значение по первому подходящему заголовку — названия колонок в
       выгрузках Битрикса гуляют, поэтому ищем по вхождению."""
    for k in keys:
        for h, v in d.items():
            if k in h:
                return v
    return ""

def norm_date(s):
    m = re.search(r"(\d{1,2})[.\-/](\d{1,2})", str(s))
    return "%02d.%02d" % (int(m.group(1)), int(m.group(2))) if m else ""

def norm_amount(s):
    s = re.sub(r"[^\d,.\-]", "", str(s)).replace(",", ".")
    if not s or s in (".", "-"): return ""
    try: return str(int(round(float(s))))
    except Exception: return ""

def build_rows(recs):
    out, dates = [], []
    for d in recs:
        date = norm_date(pick(d, "дата", "создан", "date"))
        if not date: continue
        typ = pick(d, "тип платеж", "тип", "процесс") or "—"
        who = pick(d, "заявител", "автор", "инициатор", "создал") or "—"
        city = pick(d, "город", "подразделен")
        amt = norm_amount(pick(d, "сумма", "общая сумма"))
        stat = pick(d, "статус", "состояни") or "—"
        opis = pick(d, "коммент", "за что", "назначен", "описан")
        fil = pick(d, "файл", "вложен", "документ")
        out.append("≡".join([date, typ, who, city, amt, stat, opis, fil]))
        dates.append(pick(d, "дата", "создан", "date"))
    return out, dates

def full_date(s):
    m = re.search(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", str(s))
    if not m: return ""
    y = m.group(3);  y = ("20" + y) if len(y) == 2 else y
    return "%02d.%02d.%s" % (int(m.group(1)), int(m.group(2)), y)

def publish(lines, dates):
    html = open(REPORT, encoding="utf-8").read()
    m = re.search(r'(<script[^>]*id="raw"[^>]*>)(.*?)(</script>)', html, re.S)
    if not m:
        log("   в отчёте не найден блок данных — ничего не меняю"); return False
    было = len([l for l in m.group(2).split("\n") if "≡" in l])
    html = html[:m.start(2)] + "\n" + "\n".join(lines) + "\n" + html[m.end(2):]
    fd = sorted([x for x in (full_date(d) for d in dates) if x],
                key=lambda s: (s[6:], s[3:5], s[:2]))
    if fd:
        html = re.sub(r'const CFG=\{[^}]*\}',
                      'const CFG={period:"%s – %s", asof:"%s"}' % (fd[0], fd[-1], fd[-1]), html)
    open(REPORT, "w", encoding="utf-8").write(html)
    log("[ok] отчёт обновлён: было %d заявок, стало %d" % (было, len(lines)))
    if fd: log("     период %s – %s" % (fd[0], fd[-1]))
    return True

def main():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=5)   # Алматы
    log("Битрикс · оплаты · %s (Алматы)" % now.strftime("%d.%m.%Y %H:%M"))
    if WH:
        j, err = call("profile")
        prof = j.get("result") if j else None
        log("profile:", ("ok · %s %s · admin=%s" % (prof.get("NAME"), prof.get("LAST_NAME"),
            prof.get("ADMIN"))) if prof else ("ошибка — %s" % err))
        probe()
    else:
        log("[i] BITRIX_WEBHOOK не задан — разведку пропускаю.")

    feed = next((os.path.join(HERE, f) for f in FEEDS if os.path.exists(os.path.join(HERE, f))), None)
    if not feed:
        log("[i] Выгрузки нет (ждём файл %s рядом со скриптом)." % " / ".join(FEEDS))
        log("[ok] Отчёт не тронут.")
        return
    log("[i] Нашлась выгрузка:", os.path.basename(feed))
    recs = read_feed(feed)
    log("   строк в файле:", len(recs))
    if recs:
        log("   колонки:", ", ".join(list(recs[0].keys())[:12]))
    lines, dates = build_rows(recs)
    if not lines:
        log("   не удалось разобрать ни одной строки — отчёт не тронут"); return
    publish(lines, dates)

if __name__ == "__main__":
    main()
