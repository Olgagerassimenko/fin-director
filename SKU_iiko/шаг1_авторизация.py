# -*- coding: utf-8 -*-
import requests, hashlib, warnings
warnings.filterwarnings("ignore")

URL   = "https://fudzavod.iiko.it"
LOGIN = "GerassimenkoO"
PASS  = "1234"

sha1 = hashlib.sha1(PASS.encode()).hexdigest()
print(f"SHA1 хэш: {sha1}")

r = requests.get(f"{URL}/resto/api/auth",
    params={"login": LOGIN, "pass": sha1},
    verify=False, timeout=30)

print(f"HTTP: {r.status_code}")
print(f"Ответ: {r.text[:100]}")

if r.status_code == 200:
    token = r.text.strip().strip('"')
    print(f"\nТокен получен: {token[:16]}...")
    print("Авторизация OK")
else:
    print("Ошибка авторизации")
