#!/usr/bin/env python3
"""数据库初始化 Python 脚本"""

import os
import sys
import time
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def wait_for_postgres(host, port, user, password, max_retries=30):
    """等待 PostgreSQL 就绪"""
    print(f"等待 PostgreSQL 连接 {host}:{port}...")
    
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database='postgres'
            )
            conn.close()
            print("PostgreSQL 已就绪")
            return True
        except psycopg2.OperationalError:
            print(f"PostgreSQL 不可用 - 重试 {i+1}/{max_retries}...")
            time.sleep(2)
    
    return False

def create_database(host, port, user, password, db_name):
    """创建数据库"""
    print(f"创建数据库 {db_name}...")
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database='postgres'
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # 检查数据库是否存在
    cursor.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s",
        (db_name,)
    )
    
    if cursor.fetchone():
        print(f"数据库 {db_name} 已存在")
    else:
        cursor.execute(sql.SQL("CREATE DATABASE {}").format(
            sql.Identifier(db_name)
        ))
        print(f"数据库 {db_name} 创建成功")
    
    cursor.close()
    conn.close()

def run_migrations(host, port, user, password, db_name):
    """执行迁移脚本"""
    print("执行迁移脚本...")
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db_name
    )
    cursor = conn.cursor()
    
    # 执行迁移脚本
    migration_files = sorted([
        f for f in os.listdir('db/migrations')
        if f.endswith('.sql')
    ])
    
    for migration_file in migration_files:
        print(f"执行 {migration_file}...")
        with open(f'db/migrations/{migration_file}', 'r', encoding='utf-8') as f:
            migration_sql = f.read()
            cursor.execute(migration_sql)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("迁移脚本执行完成")

def run_init_data(host, port, user, password, db_name):
    """执行初始化数据脚本"""
    print("插入初始化数据...")
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db_name
    )
    cursor = conn.cursor()
    
    with open('db/init_data.sql', 'r', encoding='utf-8') as f:
        init_sql = f.read()
        cursor.execute(init_sql)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("初始化数据插入完成")

def main():
    """主函数"""
    # 获取配置
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    user = os.getenv('POSTGRES_USER', 'gateway_user')
    password = os.getenv('POSTGRES_PASSWORD', 'gateway_pass')
    db_name = os.getenv('POSTGRES_DB', 'vehicle_iot_gateway')
    
    try:
        # 等待 PostgreSQL 就绪
        if not wait_for_postgres(host, port, user, password):
            print("错误: PostgreSQL 连接超时")
            sys.exit(1)
        
        # 创建数据库
        create_database(host, port, user, password, db_name)
        
        # 执行迁移
        run_migrations(host, port, user, password, db_name)
        
        # 插入初始化数据
        run_init_data(host, port, user, password, db_name)
        
        print("\n✅ 数据库初始化完成！")
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
