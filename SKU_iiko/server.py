#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iiko SKU Dashboard — локальный live-сервер.
Открывайте http://localhost:8080 в браузере.
Данные автоматически обновляются из iiko каждый час.
"""

import requests, hashlib, json, re, os, sys, time, threading
import subprocess, webbrowser, warnings
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from collections import defaultdict

warnings.filterwarnings("ignore")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR   = os.path.dirname(SCRIPT_DIR)
GENERATE_PY  = os.path.join(SCRIPT_DIR, 'generate.py')
DASHBOARD_F  = os.path.join(PARENT_DIR, 'дашборд_sku_iiko.html')
PORT         = 8080
REFRESH_SECS = 3600    # обновлять каждый час

# ── Кэш ─────────────────────────────────────
_lock       = threading.Lock()
_last_gen   = 0          # unix timestamp последней генерации
_generating = False      # флаг "сейчас идёт генерация"

def run_generate(silent=False):
    """Запускает generate.py и возвращает True при успехе."""
    global _last_gen, _generating
    with _lock:
        if _generating:
            return False
        _generating = True
    try:
        if not silent:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Обновляю данные из iiko...", flush=True)
        result = subprocess.run(
            [sys.executable, GENERATE_PY],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            _last_gen = time.time()
            if not silent:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Готово ✓", flush=True)
            return True
        else:
            print(f"[!] generate.py error:\n{result.stderr[-500:]}", flush=True)
            return False
    except Exception as e:
        print(f"[!] Ошибка генерации: {e}", flush=True)
        return False
    finally:
        with _lock:
            _generating = False

def get_dashboard_html():
    """Возвращает HTML дашборда (из файла)."""
    if not os.path.exists(DASHBOARD_F):
        return None
    with open(DASHBOARD_F, encoding='utf-8') as f:
        html = f.read()
    # Инжектируем авто-обновление браузера (каждый час)
    refresh_meta = f'<meta http-equiv="refresh" content="{REFRESH_SECS}">'
    refresh_bar  = (
        f'<div id="_server-bar" style="position:fixed;bottom:0;left:0;right:0;'
        f'background:#1e1b4b;color:#a5b4fc;font-size:11px;padding:5px 16px;'
        f'display:flex;gap:16px;z-index:9999;">'
        f'<span>⚡ Live iiko</span>'
        f'<span id="_upd-time">Обновлено: {datetime.now().strftime("%d.%m %H:%M")}</span>'
        f'<span style="margin-left:auto">'
        f'<a href="/force" style="color:#818cf8;text-decoration:none">↻ Обновить сейчас</a>'
        f'</span></div>'
    )
    html = html.replace('</head>', f'{refresh_meta}</head>')
    html = html.replace('</body>', f'{refresh_bar}</body>')
    return html

# ── Фоновый поток — обновление каждый час ────
def background_refresh():
    while True:
        time.sleep(60)  # проверяем каждую минуту
        age = time.time() - _last_gen
        if age >= REFRESH_SECS:
            run_generate(silent=False)

# ── HTTP-обработчик ───────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # выключаем стандартные access logs

    def do_GET(self):
        # Принудительное обновление
        if self.path in ('/force', '/refresh'):
            threading.Thread(target=run_generate, daemon=True).start()
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return

        # Главная страница
        if self.path in ('/', '/dashboard'):
            # Если файла ещё нет — сначала генерируем
            if not os.path.exists(DASHBOARD_F):
                run_generate()

            html = get_dashboard_html()
            if not html:
                html = '<h2 style="font-family:sans-serif;padding:40px">Генерация данных... обновите страницу через минуту.</h2>'

            content = html.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(content)
            return

        # Статус API
        if self.path == '/status':
            age = int(time.time() - _last_gen)
            info = {
                'ok': True,
                'last_updated': datetime.fromtimestamp(_last_gen).strftime('%d.%m.%Y %H:%M:%S') if _last_gen else 'никогда',
                'age_min': age // 60,
                'next_refresh_min': max(0, REFRESH_SECS - age) // 60,
            }
            content = json.dumps(info, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(content)
            return

        self.send_error(404)

# ── Запуск ────────────────────────────────────
if __name__ == '__main__':
    print("=" * 52)
    print("  iiko SKU Dashboard — live сервер")
    print("=" * 52)
    print(f"  URL:     http://localhost:{PORT}")
    print(f"  Обновление: каждые {REFRESH_SECS//60} минут из iiko")
    print()

    # Первичная генерация (если файл устарел или отсутствует)
    age = time.time() - os.path.getmtime(DASHBOARD_F) if os.path.exists(DASHBOARD_F) else 999999
    if age > REFRESH_SECS:
        print("  Первичная загрузка данных из iiko...")
        run_generate()
    else:
        print(f"  Файл актуален (возраст {int(age)//60} мин). Загрузка не нужна.")
        _last_gen = time.time() - age

    # Фоновый поток обновления
    t = threading.Thread(target=background_refresh, daemon=True)
    t.start()

    # Открываем браузер
    threading.Timer(1.2, lambda: webbrowser.open(f'http://localhost:{PORT}')).start()

    # Запускаем сервер
    try:
        httpd = HTTPServer(('localhost', PORT), Handler)
        print(f"  Сервер запущен. Браузер откроется автоматически.")
        print(f"  Нажмите Ctrl+C для остановки.\n")
        httpd.serve_forever()
    except OSError as e:
        if 'Address already in use' in str(e) or '10048' in str(e):
            print(f"  Порт {PORT} уже занят — возможно сервер уже запущен.")
            webbrowser.open(f'http://localhost:{PORT}')
        else:
            raise
