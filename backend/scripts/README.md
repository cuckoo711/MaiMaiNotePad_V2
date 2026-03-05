# 运维脚本说明

本目录包含后端项目的运维和管理脚本。

## 📜 脚本列表

### full_reset.py

**用途**：全量删档清库脚本

**功能**：
- 删除并重建 PostgreSQL 数据库
- 清空 Redis 缓存
- 删除上传文件和日志
- 清理迁移文件
- 重新生成 SECRET_KEY
- 执行数据库迁移
- 初始化基础数据（菜单、角色、部门、用户等）

**使用方法**：
```bash
conda activate mai_notebook
cd backend

# 基础重置
python scripts/full_reset.py

# 包含测试用户
python scripts/full_reset.py --test
```

**注意事项**：
- 此操作不可逆，会删除所有数据
- 生产环境禁止使用
- 执行前会要求确认

---

### setup_config.py

**用途**：交互式配置生成脚本

**功能**：
- 收集邮件 SMTP 配置
- 收集 AI 审核 API Key
- 自动生成数据库和 Redis 密码
- 生成 `conf/env.py` 配置文件

**使用方法**：
```bash
# 交互式生成配置
python scripts/setup_config.py

# 指定密码生成配置
python scripts/setup_config.py --pg-pass <密码> --redis-pass <密码>

# 仅生成随机密码（供脚本调用）
python scripts/setup_config.py --gen-password
```

**配置项**：
- 邮件 SMTP 服务器配置
- AI 内容审核 API Key（硅基流动）
- 前端地址
- 调试模式开关

---

### backup_database.sh

**用途**：数据库备份脚本

**功能**：
- 自动读取 Django 配置中的数据库信息
- 支持 PostgreSQL、MySQL、SQLite
- 生成带时间戳的备份文件
- 提供恢复命令提示

**使用方法**：
```bash
# 使用时间戳作为备份名称
./scripts/backup_database.sh

# 指定备份名称
./scripts/backup_database.sh before_migration
```

**备份位置**：
- 备份文件存储在项目根目录的 `backups/` 目录
- PostgreSQL 使用自定义格式（.sql）

**恢复方法**：
```bash
# PostgreSQL
pg_restore -h localhost -p 5432 -U mai_notebook -d mai_notebook -c backups/backup_name.sql

# MySQL
mysql -h localhost -P 3306 -u mai_notebook -p mai_notebook < backups/backup_name.sql

# SQLite
cp backups/backup_name.sql path/to/db.sqlite3
```

---

## 🔒 安全提示

1. **密码管理**
   - 生成的密码会写入 `conf/env.py`
   - 该文件已被 `.gitignore` 排除，不会提交到版本控制
   - 生产环境请妥善保管配置文件

2. **备份管理**
   - 定期备份数据库
   - 备份文件包含敏感数据，请妥善保管
   - 建议将备份文件存储在安全的位置

3. **重置脚本**
   - `full_reset.py` 仅用于开发和测试环境
   - 生产环境禁止使用
   - 执行前务必确认操作

## 📝 维护说明

- 所有脚本必须包含中文注释和文档字符串
- 脚本应具有良好的错误处理和用户提示
- 危险操作必须要求用户确认
- 更新脚本时同步更新本文档
