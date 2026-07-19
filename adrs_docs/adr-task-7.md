# ADR: Проектирование схем и шард-ключей для MongoDB

**Контекст:** Онлайн-магазин «Мобильный мир» — коллекции `orders`, `products`, `carts`

## 1. Коллекция `orders`

### Схема

```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439011"),
  "order_id": "ORD-2025-001234",
  "user_id": ObjectId("507f1f77bcf86cd799439012"),
  "created_at": ISODate("2025-07-08T10:30:00Z"),
  "items": [
    {
      "product_id": ObjectId("507f1f77bcf86cd799439013"),
      "quantity": 1,
      "price": 599.99
    },
    {
      "product_id": ObjectId("507f1f77bcf86cd799439014"),
      "quantity": 2,
      "price": 45.00
    }
  ],
  "status": "delivered",
  "total_amount": 689.99,
  "geo_zone": "MOSCOW"
}
```

### Шард-ключ и стратегия

```javascript
{ "user_id": "hashed" }  // Hashed Sharding
```

### Обоснование

| Критерий | Обоснование |
|----------|-------------|
| Основные операции | История заказов пользователя, статус заказа - запросы по `user_id` |
| Кардинальность | Высокая (много пользователей), равномерное распределение |
| Записи | Нет "горячих" шардов при создании заказов (хеширование) |
| Чтения | Данные одного пользователя на одном шарде |

## 2. Коллекция `products`

### Схема

```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439015"),
  "product_id": "PRD-1001",
  "name": "Смартфон X",
  "category": "Электроника",
  "price": 599.99,
  "stock": {
    "MOSCOW": 150,
    "EKATERINBURG": 50,
    "KALININGRAD": 30
  },
  "attributes": {
    "color": "Black",
    "size": "6"
  }
}
```

### Шард-ключ и стратегия

```javascript
{ "category": 1, "product_id": 1 }  // Ranged Sharding
```

### Обоснование

| Критерий | Обоснование |
|----------|-------------|
| Основные операции | Поиск по категориям, фильтрация по цене - range scan в одной категории |
| Кардинальность | Средняя (~20-50 категорий), распределение по категориям |
| Обновления | Точечные обновления остатков по `product_id` |

## 3. Коллекция `carts`

### Схема

```javascript
{
  "_id": ObjectId("507f1f77bcf86cd799439016"),
  "user_id": ObjectId("507f1f77bcf86cd799439017"),
  "session_id": "SESSION-ABC123",
  "items": [
    {
      "product_id": ObjectId("507f1f77bcf86cd799439018"),
      "quantity": 1
    },
    {
      "product_id": ObjectId("507f1f77bcf86cd799439019"),
      "quantity": 2
    }
  ],
  "status": "active",
  "created_at": ISODate("2025-07-08T09:00:00Z"),
  "updated_at": ISODate("2025-07-08T09:30:00Z"),
  "expires_at": ISODate("2025-07-09T09:00:00Z")
}
```

### Шард-ключ и стратегия

```javascript
{ "user_id": "hashed" }  // Hashed Sharding
```

### Обоснование

| Критерий | Обоснование |
|----------|-------------|
| Основные операции | Получение корзины по `user_id` или `session_id`, точечный запрос |
| Кардинальность | Высокая (много пользователей/сессий) - равномерное распределение |
| Обновления | Частые обновления корзины - равномерная нагрузка |
| Гости | `user_id = null`, хеширование по `session_id` как fallback |

## Команды для внедрения

```javascript
// Включить шардирование
sh.enableSharding("mobile_world")

// orders
sh.shardCollection("mobile_world.orders", { "user_id": "hashed" })

// products
sh.shardCollection("mobile_world.products", { "category": 1, "product_id": 1 })

// carts
sh.shardCollection("mobile_world.carts", { "user_id": "hashed" })
```

## Альтернативы

| Коллекция | Отклонённый ключ | Причина |
|-----------|------------------|---------|
| orders | `{ "geo_zone": 1 }` | Низкая кардинальность (мало геозон), дисбаланс |
| products | `{ "product_id": "hashed" }` | Запросы по категориям — scatter-gather по всем шардам |
| carts | `{ "status": 1 }` | Низкая кардинальность (всего 3 статуса) |
