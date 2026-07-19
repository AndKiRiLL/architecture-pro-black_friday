# ADR: Выявление и устранение «горячих» шардов

**Контекст:** Перегрузка шарда из-за категории «Электроника» (70% запросов)

---

## 1. Метрики мониторинга

| Метрика | Описание | Команда |
|---------|----------|---------|
| **Размер данных на шарде** | Объём данных (GB) | `sh.status()` |
| **Количество чанков** | Число чанков на шард | `sh.status(true)` |
| **Нагрузка на чтение/запись** | Операции в секунду | `mongostat` |
| **Коэффициент дисбаланса** | Max размер / Min размер | `sh.status()` |
| **Задержки (latency)** | Время выполнения запросов | `db.collection.stats()` |

### Команды для сбора метрик

```javascript
// Статистика по шардам
sh.status()

// Размер коллекции на каждом шарде
db.collection.getShardDistribution()

// Активные операции
db.currentOp()
```

---

## 2. Механизмы автоматического перераспределения

- ### Настройка балансировщика

```javascript
// Включить балансировку
sh.enableBalancing("mobile_world.products")

// Установить размер чанка (по умолчанию 64 МБ)
use config
db.settings.update(
  { _id: "balancer" },
  { $set: { "chunkSize": 128 } }
)

// Задать окно балансировки (ночное время)
db.settings.update(
  { _id: "balancer" },
  { $set: { "activeWindow": { "start": "02:00", "stop": "06:00" } } }
)
```

- ### Зональное шардирование (для популярных категорий)

```javascript
// Назначить зоны
sh.addShardToZone("shard1", "ELECTRONICS")
sh.addShardToZone("shard2", "ELECTRONICS")
sh.addShardToZone("shard3", "OTHER")

// Разбить категорию Электроника на диапазоны
sh.updateZoneKeyRange(
  "mobile_world.products",
  { "category": "Электроника", "product_id": "PRD-0000" },
  { "category": "Электроника", "product_id": "PRD-5000" },
  "ELECTRONICS"
)

sh.updateZoneKeyRange(
  "mobile_world.products",
  { "category": "Электроника", "product_id": "PRD-5000" },
  { "category": "Электроника", "product_id": "PRD-ZZZZ" },
  "ELECTRONICS"
)
```

- ### Ручное разбиение чанков

```javascript
// Сплит чанков популярной категории
sh.splitAt(
  "mobile_world.products",
  { "category": "Электроника", "product_id": "PRD-1000" }
)
sh.splitAt(
  "mobile_world.products",
  { "category": "Электроника", "product_id": "PRD-2000" }
)

// Миграция на разные шарды
sh.moveChunk(
  "mobile_world.products",
  { "category": "Электроника", "product_id": "PRD-0" },
  "shard2"
)
```

## Сводная таблица решений

| Проблема | Решение | Команда |
|----------|---------|---------|
| Дисбаланс чанков | Автоматическая балансировка | `sh.enableBalancing()` |
| Популярная категория | Зональное шардирование | `sh.updateZoneKeyRange()` |
| Перегрузка шарда | Миграция чанков | `sh.moveChunk()` |
| Рост нагрузки | Добавление шарда | `sh.addShard()` |
