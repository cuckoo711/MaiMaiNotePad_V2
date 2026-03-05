#!/bin/bash
# 数据库备份脚本
#
# 用法：./backup_database.sh [备份名称]
# 示例：./backup_database.sh before_tags_migration

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 备份目录
BACKUP_DIR="$PROJECT_ROOT/backups"
mkdir -p "$BACKUP_DIR"

# 备份名称（默认使用时间戳）
BACKUP_NAME="${1:-backup_$(date +%Y%m%d_%H%M%S)}"
BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}.sql"

echo "=========================================="
echo "数据库备份脚本"
echo "=========================================="
echo "备份文件: $BACKUP_FILE"
echo ""

# 从 Django 配置读取数据库信息
cd "$PROJECT_ROOT/backend"

# 激活 conda 环境并获取数据库配置
DB_INFO=$(conda run -n mai_notebook python -c "
import os
import sys
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')

import django
django.setup()

from django.conf import settings
db = settings.DATABASES['default']

print(f\"{db['ENGINE']}|{db['NAME']}|{db.get('USER', '')}|{db.get('PASSWORD', '')}|{db.get('HOST', 'localhost')}|{db.get('PORT', '5432')}\")
")

# 解析数据库信息
IFS='|' read -r DB_ENGINE DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT <<< "$DB_INFO"

echo "数据库引擎: $DB_ENGINE"
echo "数据库名称: $DB_NAME"
echo "数据库主机: $DB_HOST"
echo "数据库端口: $DB_PORT"
echo ""

# 根据数据库类型执行备份
if [[ "$DB_ENGINE" == *"postgresql"* ]]; then
    echo "执行 PostgreSQL 备份..."
    
    if [ -n "$DB_PASSWORD" ]; then
        export PGPASSWORD="$DB_PASSWORD"
    fi
    
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -F c -f "$BACKUP_FILE"
    
    if [ -n "$DB_PASSWORD" ]; then
        unset PGPASSWORD
    fi
    
elif [[ "$DB_ENGINE" == *"mysql"* ]]; then
    echo "执行 MySQL 备份..."
    
    MYSQL_PWD="$DB_PASSWORD" mysqldump -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
    
elif [[ "$DB_ENGINE" == *"sqlite"* ]]; then
    echo "执行 SQLite 备份..."
    
    cp "$DB_NAME" "$BACKUP_FILE"
    
else
    echo "错误: 不支持的数据库类型 $DB_ENGINE"
    exit 1
fi

echo ""
echo "=========================================="
echo "备份完成！"
echo "=========================================="
echo "备份文件: $BACKUP_FILE"
echo "文件大小: $(du -h "$BACKUP_FILE" | cut -f1)"
echo ""
echo "恢复命令（PostgreSQL）："
echo "  pg_restore -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c $BACKUP_FILE"
echo ""
