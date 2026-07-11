import requests
import random
import string

BASE_URL = "http://localhost:8080"

# Загрузка 100 пользователей
print("Загрузка тестовых данных...")
for i in range(100):
    user = {
        "name": f"user_{i}",
        "age": random.randint(18, 80)
    }
    response = requests.post(f"{BASE_URL}/helloDoc/users", json=user)
    if response.status_code == 201:
        print(f"✓ Создан пользователь {i+1}/100: {user['name']}")
    else:
        print(f"✗ Ошибка: {response.status_code} - {response.text}")

print("\nГотово!")