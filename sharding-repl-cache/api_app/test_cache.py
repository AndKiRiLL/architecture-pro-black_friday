# test_cache.py
import requests
import time

BASE_URL = "http://localhost:8080"

def measure_time(func, *args, **kwargs):
    start = time.time()
    result = func(*args, **kwargs)
    elapsed = time.time() - start
    return result, elapsed

print("=" * 60)
print("ТЕСТ КЕШИРОВАНИЯ REDIS")
print("=" * 60)

# 1. Создаем тестовые данные
print("\n📝 Создание тестовых данных...")
for i in range(10):
    user = {"name": f"cache_test_{i}", "age": 20 + i}
    response = requests.post(f"{BASE_URL}/helloDoc/users", json=user)
    if response.status_code == 201:
        print(f"  ✓ Создан: cache_test_{i}")

# 2. Первый запрос (без кеша)
print("\n🔍 ПЕРВЫЙ ЗАПРОС (без кеша):")
_, time1 = measure_time(requests.get, f"{BASE_URL}/helloDoc/users")
print(f"  Время: {time1:.3f} сек")

# 3. Второй запрос (с кешем)
print("\n⚡ ВТОРОЙ ЗАПРОС (с кешем):")
_, time2 = measure_time(requests.get, f"{BASE_URL}/helloDoc/users")
print(f"  Время: {time2:.3f} сек")

# 4. Третий запрос (с кешем)
print("\n⚡ ТРЕТИЙ ЗАПРОС (с кешем):")
_, time3 = measure_time(requests.get, f"{BASE_URL}/helloDoc/users")
print(f"  Время: {time3:.3f} сек")

# 5. Сравнение
print("\n📊 СРАВНЕНИЕ:")
print("-" * 40)
print(f"  Без кеша: {time1:.3f} сек")
print(f"  С кешем 1: {time2:.3f} сек (ускорение x{time1/time2:.1f})")
print(f"  С кешем 2: {time3:.3f} сек (ускорение x{time1/time3:.1f})")

# 6. Проверка API статуса
print("\n📡 СТАТУС API:")
response = requests.get(f"{BASE_URL}/")
data = response.json()
print(f"  Топология: {data['mongo_topology_type']}")
print(f"  Кеш включен: {data['cache_enabled']}")
print(f"  Redis: {'✅' if data['cache_enabled'] else '❌'}")

print("=" * 60)