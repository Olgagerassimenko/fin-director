# -*- coding: utf-8 -*-
"""
Шаг 8: изучаем /resto/api/products и сохраняем полный текст ошибки OLAP.
"""
import requests, hashlib, warnings, json, os
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

STORE_GP_FZ = "39846ac3-3697-417b-b33f-228123ab15a3"
STORE_GP_25 = "e64f0a92-a07e-4207-866e-dac07950ae19"

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1},
          verify=False, timeout=30)
token = r.text.strip().strip('"')
H_json = {"Cookie": f"key={token}", "Content-Type": "application/json"}
H      = {"Cookie": f"key={token}"}
print("Token OK\n")

HERE = os.path.dirname(os.path.abspath(__file__))

# ── 1. Сохраняем полный текст ошибки OLAP (список валидных reportType) ────
print("=== 1. Полный текст ошибки GOODS_MOTION → файл olap_error.txt ===\n")
body = {"reportType": "GOODS_MOTION", "buildSummary": "false",
        "groupByRowFields": ["DishName"], "groupByColFields": [],
        "aggregateFields": ["DishDiscountSumInt"], "filters": {}}
r2 = s.post(f"{URL}/resto/api/v2/reports/olap",
            json=body, headers=H_json, verify=False, timeout=15)
err_file = os.path.join(HERE, "olap_error.txt")
with open(err_file, "w", encoding="utf-8") as f:
    f.write(r2.text)
print(r2.text[:500])
print(f"\n[Полный текст сохранён в olap_error.txt]\n")

# ── 2. Изучаем /resto/api/products ────────────────────────────────────────
print("=== 2. /resto/api/products ===\n")
r2 = s.get(f"{URL}/resto/api/products", headers=H, verify=False, timeout=30)
print(f"HTTP {r2.status_code} | Длина: {len(r2.text)} байт")

prod_file = os.path.join(HERE, "products_raw.txt")
with open(prod_file, "w", encoding="utf-8") as f:
    f.write(r2.text)
print(f"[Ответ сохранён в products_raw.txt]\n")

# Попробуем распарсить
try:
    import xml.etree.ElementTree as ET
    root = ET.fromstring(r2.text)
    items = list(root)
    print(f"XML: корневой тег={root.tag}, дочерних элементов={len(items)}")
    if items:
        first = items[0]
        print(f"Пример элемента: {first.tag}")
        for sub in first:
            print(f"  {sub.tag}: {sub.text or ''}[:50]")
except Exception:
    try:
        data = r2.json()
        if isinstance(data, list):
            print(f"JSON список: {len(data)} элементов")
            if data:
                print(f"Первый элемент: {json.dumps(data[0], ensure_ascii=False)[:300]}")
        else:
            print(f"JSON объект: {json.dumps(data, ensure_ascii=False)[:300]}")
    except Exception:
        print(f"Сырой текст (первые 300 символов):")
        print(r2.text[:300])

# ── 3. GET на v1 OLAP (без тела — посмотрим что отвечает) ─────────────────
print("\n=== 3. GET /resto/api/reports/olap ===\n")
r2 = s.get(f"{URL}/resto/api/reports/olap", headers=H, verify=False, timeout=15)
print(f"HTTP {r2.status_code} | {r2.text[:200]}")

# ── 4. Пробуем вариации products ──────────────────────────────────────────
print("\n=== 4. Вариации products-эндпоинтов ===\n")
for ep in [
    f"/resto/api/products?store={STORE_GP_FZ}",
    f"/resto/api/products?type=DISH",
    f"/resto/api/products?type=PRODUCT",
    f"/resto/api/v2/products",
    f"/resto/api/products/list",
]:
    r2 = s.get(f"{URL}{ep}", headers=H, verify=False, timeout=15)
    print(f"  {ep.split('?')[0]:<40} HTTP {r2.status_code} | {len(r2.text)} байт")

print("\nГотово. Проверь файлы olap_error.txt и products_raw.txt в папке SKU_iiko.")
