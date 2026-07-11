#!/bin/bash

echo "========================================="
echo "Инициализация шардирования MongoDB"
echo "========================================="

# Просто пробуем выполнить все команды с задержками
# Игнорируем ошибки, так как многие команды могут выполняться повторно

echo "Ждем 30 секунд перед началом..."
sleep 30

echo -e "\n[1/5] Config Server..."
mongosh --host configSrv --port 27017 --quiet --eval "
rs.initiate({
    _id: 'config_server',
    configsvr: true,
    members: [{ _id: 0, host: 'configSrv:27017' }]
})
" 2>&1 || echo "configSrv уже инициализирован"
sleep 20

echo -e "\n[2/5] Shard 1..."
mongosh --host shard1 --port 27018 --quiet --eval "
rs.initiate({
    _id: 'shard1',
    members: [{ _id: 0, host: 'shard1:27018' }]
})
" 2>&1 || echo "shard1 уже инициализирован"
sleep 15

echo -e "\n[3/5] Shard 2..."
mongosh --host shard2 --port 27019 --quiet --eval "
rs.initiate({
    _id: 'shard2',
    members: [{ _id: 0, host: 'shard2:27019' }]
})
" 2>&1 || echo "shard2 уже инициализирован"
sleep 30

echo -e "\n[4/5] Добавление шардов..."
echo "Ожидание роутера..."
for i in {1..30}; do
    if mongosh --host mongos_router --port 27020 --quiet --eval "db.version()" &>/dev/null; then
        echo "✓ Роутер доступен"
        break
    fi
    echo "  Попытка $i/30..."
    sleep 5
done

mongosh --host mongos_router --port 27020 --quiet --eval "sh.addShard('shard1/shard1:27018')" 2>&1 || echo "shard1 уже добавлен"
sleep 3
mongosh --host mongos_router --port 27020 --quiet --eval "sh.addShard('shard2/shard2:27019')" 2>&1 || echo "shard2 уже добавлен"
sleep 5

echo -e "\n[5/5] Настройка шардирования..."
mongosh --host mongos_router --port 27020 --quiet --eval "sh.enableSharding('somedb')" 2>&1 || echo "Шардирование уже включено"
mongosh --host mongos_router --port 27020 --quiet --eval "sh.shardCollection('somedb.helloDoc', { 'name': 'hashed' })" 2>&1 || echo "Коллекция уже шардирована"

echo -e "\n========================================="
echo "✓ Готово: $(date)"
echo "========================================="

# Показываем статус
# mongosh --host mongos_router --port 27020 --quiet --eval "sh.status()" 2>&1