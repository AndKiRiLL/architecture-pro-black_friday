#!/bin/bash

echo "========================================="
echo "Инициализация шардирования MongoDB с репликацией"
echo "========================================="

echo "Ждем 20 секунд перед началом..."
sleep 20

# [1] Config Server
echo -e "\n[1/6] Config Server..."
mongosh --host configSrv --port 27017 --quiet <<'EOF'
rs.initiate({
    _id: "config_server",
    configsvr: true,
    members: [{ _id: 0, host: "configSrv:27017" }]
})
EOF
echo "✓ Config server initialized"
sleep 20

# [2] ИНИЦИАЛИЗАЦИЯ РЕПЛИКАЦИИ SHARD 1
echo -e "\n[2/6] Инициализация репликации Shard 1 (3 узла)..."
mongosh --host shard1-primary --port 27018 --quiet <<'EOF'
rs.initiate({
    _id: "shard1",
    members: [
        { _id: 0, host: "shard1-primary:27018", priority: 2 },
        { _id: 1, host: "shard1-secondary1:27018", priority: 1 },
        { _id: 2, host: "shard1-secondary2:27018", priority: 1 }
    ]
})
EOF
echo "✓ Репликация shard1 инициализирована"
sleep 10

# Проверка статуса репликации shard1
echo "Проверка статуса shard1..."
mongosh --host shard1-primary --port 27018 --quiet <<'EOF'
print("=== СТАТУС РЕПЛИКАЦИИ SHARD1 ===");
var status = rs.status();
print("Set: " + status.set);
print("Members:");
status.members.forEach(function(m) {
    print("  " + m.name + " - " + m.stateStr + " (health: " + m.health + ")");
});
EOF
sleep 15

# [3] ИНИЦИАЛИЗАЦИЯ РЕПЛИКАЦИИ SHARD 2
echo -e "\n[3/6] Инициализация репликации Shard 2 (3 узла)..."
mongosh --host shard2-primary --port 27019 --quiet <<'EOF'
rs.initiate({
    _id: "shard2",
    members: [
        { _id: 0, host: "shard2-primary:27019", priority: 2 },
        { _id: 1, host: "shard2-secondary1:27019", priority: 1 },
        { _id: 2, host: "shard2-secondary2:27019", priority: 1 }
    ]
})
EOF
echo "✓ Репликация shard2 инициализирована"
sleep 10

# Проверка статуса репликации shard2
echo "Проверка статуса shard2..."
mongosh --host shard2-primary --port 27019 --quiet <<'EOF'
print("=== СТАТУС РЕПЛИКАЦИИ SHARD2 ===");
var status = rs.status();
print("Set: " + status.set);
print("Members:");
status.members.forEach(function(m) {
    print("  " + m.name + " - " + m.stateStr + " (health: " + m.health + ")");
});
EOF
sleep 15

# [4] Ожидание роутера
echo -e "\n[4/6] Ожидание роутера..."
for i in {1..30}; do
    if mongosh --host mongos_router --port 27020 --quiet --eval "db.version()" &>/dev/null; then
        echo "✓ Роутер доступен"
        break
    fi
    echo "  Попытка $i/30..."
    sleep 5
done

# [5] Добавление шардов
echo -e "\n[5/6] Добавление шардов в роутер..."
mongosh --host mongos_router --port 27020 --quiet <<'EOF'
sh.addShard("shard1/shard1-primary:27018,shard1-secondary1:27018,shard1-secondary2:27018")
EOF
echo "✓ Shard1 добавлен с репликацией"

mongosh --host mongos_router --port 27020 --quiet <<'EOF'
sh.addShard("shard2/shard2-primary:27019,shard2-secondary1:27019,shard2-secondary2:27019")
EOF
echo "✓ Shard2 добавлен с репликацией"
sleep 5

# [6] Настройка шардирования
echo -e "\n[6/6] Настройка шардирования..."
mongosh --host mongos_router --port 27020 --quiet <<'EOF'
sh.enableSharding("somedb");
sh.shardCollection("somedb.helloDoc", { "name": "hashed" });
EOF
echo "✓ Шардирование настроено"

# Финальный статус
echo -e "\n=== ФИНАЛЬНЫЙ СТАТУС ==="
mongosh --host mongos_router --port 27020 --quiet <<'EOF'
print("=== СТАТУС ШАРДОВ ===");
sh.status();
EOF

echo -e "\n=== ДЕТАЛЬНАЯ ПРОВЕРКА РЕПЛИКАЦИИ ==="
echo "Shard1 узлы:"
mongosh --host shard1-primary --port 27018 --quiet --eval 'rs.status().members.forEach(function(m){print(m.name+": "+m.stateStr)})'

echo -e "\nShard2 узлы:"
mongosh --host shard2-primary --port 27019 --quiet --eval 'rs.status().members.forEach(function(m){print(m.name+": "+m.stateStr)})'

echo -e "\n========================================="
echo "✓ ГОТОВО: $(date)"
echo "========================================="