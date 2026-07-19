FROM dh-mirror.gitverse.ru/mongo:latest

# Установка дополнительных утилит если нужно
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY init-sharding.sh /init-sharding.sh
RUN chmod +x /init-sharding.sh

ENTRYPOINT ["/bin/bash", "/init-sharding.sh"]