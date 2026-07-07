# -*- coding: utf-8 -*-
import requests, hashlib, warnings
import xml.etree.ElementTree as ET
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1},
          verify=False, timeout=30)
token = r.text.strip().strip('"')
headers = {"Cookie": f"key={token}"}
print(f"Token OK: {token[:16]}...\n")

def parse_xml_items(text):
    """Парсим XML от iiko, возвращаем список dict."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        print(f"  XML parse error: {e}")
        return []
    items = []
    # Ищем любые дочерние элементы с тегом содержащим 'Dto' или просто все дочерние
    for child in root:
        d = {}
        for sub in child:
            tag = sub.tag.split('}')[-1]  # убираем namespace если есть
            d[tag] = (sub.text or "").strip()
        if d:
            items.append(d)
    return items

gp_stores = {}

for ep in ["/resto/api/corporation/stores", "/resto/api/corporation/departments"]:
    r = s.get(f"{URL}{ep}", headers=headers, verify=False, timeout=30)
    print(f"--- {ep} : HTTP {r.status_code} ---")
    if not r.ok:
        print(f"  {r.text[:100]}\n")
        continue

    items = parse_xml_items(r.text)
    print(f"  Всего записей: {len(items)}")
    for d in items:
        uid  = d.get("id", "")
        name = d.get("name", d.get("code", ""))
        typ  = d.get("type", "")
        if name:
            print(f"  [{typ}] {name}  ({uid})")
        if "ГП" in name and uid:
            gp_stores[uid] = name
    print()

print("=" * 60)
if gp_stores:
    print(f"Найдено складов ГП: {len(gp_stores)}")
    for uid, name in gp_stores.items():
        print(f"  {name}")
        print(f"    UUID: {uid}")
else:
    print("Склады ГП не определены автоматически.")
    print("Скопируй UUID нужных складов из списка выше.")
