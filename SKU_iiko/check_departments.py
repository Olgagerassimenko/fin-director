# -*- coding: utf-8 -*-
import requests, hashlib, warnings, json
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

s = requests.Session()
sha1 = hashlib.sha1(PASS.encode()).hexdigest()
r = s.get(f"{URL}/resto/api/auth", params={"login": LOGIN, "pass": sha1},
          verify=False, timeout=30)
token = r.text.strip().strip('"')
print(f"Авторизация OK, токен: {token[:16]}...")
print()

headers = {"Cookie": f"key={token}"}

endpoints = [
    "/resto/api/corporation/departments",
    "/resto/api/corporation/stores",
    "/resto/api/departments",
    "/resto/api/stores",
    "/resto/api/v2/entities/restaurants?revisionFrom=-1",
]

for ep in endpoints:
    r = s.get(f"{URL}{ep}", headers=headers, verify=False, timeout=30)
    print(f"--- {ep} : HTTP {r.status_code} ---")
    if r.ok:
        try:
            data = r.json()
            items = (data if isinstance(data, list)
                     else data.get("corporateItemDtos",
                          data.get("items",
                          data.get("restaurantDtos", data))))
            if isinstance(items, list):
                for d in items[:20]:
                    if isinstance(d, dict):
                        uid  = d.get("id","?")
                        name = d.get("name") or d.get("departmentName") or d.get("restaurantName","?")
                        typ  = d.get("type","")
                        print(f"  [{typ}] {name}  ({uid})")
            else:
                print(f"  {str(data)[:300]}")
        except Exception as e:
            print(f"  JSON error: {e}")
            print(f"  Raw: {r.text[:300]}")
    else:
        print(f"  {r.text[:100]}")
    print()
