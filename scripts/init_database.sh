#!/bin/bash
# 数据库初始化脚本

set -e

echo "开始初始化数据库..."

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 设置默认值
POSTGRES_HOST=${POSTGRES_HOST:-localhost}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-vehicle_iot_gateway}
POSTGRES_USER=${POSTGRES_USER:-gateway_user}

# 检查 PostgreSQL 是否可用
echo "检查 PostgreSQL 连接..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c '\q'; do
  echo "PostgreSQL 不可用 - 等待中..."
  sleep 2
done

echo "PostgreSQL 已就绪"

# 创建数据库（如果不存在）
echo "创建数据库..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB'" | grep -q 1 || \
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB"

# 执行迁移脚本
echo "执行迁移脚本..."
for migration in db/migrations/*.sql; do
    echo "执行 $migration..."
    PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$migration"
done

# 执行初始化数据脚本
echo "插入初始化数据..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f db/init_data.sql

echo "数据库初始化完成！"
