---
name: db-migration
description: 为本项目添加新数据库模型或修改现有模型，并使用 Alembic 生成和运行数据库迁移脚本。
---

# 数据库模型与迁移规范

## 项目数据库架构

- **ORM**: SQLAlchemy (Async)
- **迁移工具**: Alembic
- **数据库**: PostgreSQL (生产) / SQLite (开发)
- **模型目录**: `backend/app/models/`
- **迁移目录**: `backend/alembic/versions/`

## 创建新模型

### 1. 在 `backend/app/models/` 创建模型文件

```python
# backend/app/models/resource.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base_class import Base

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # 外键关联示例
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # 时间戳 (自动管理)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # 关系
    project = relationship("Project", back_populates="resources")
    owner = relationship("User", back_populates="resources")
```

### 2. 在 `backend/app/models/__init__.py` 注册模型

```python
from app.models.resource import Resource
```

### 3. 确保模型在 Alembic 的 `env.py` 中被导入

检查 `backend/alembic/env.py` 中是否已导入新的模型，确保 Alembic 能检测到变更。

## 生成和运行迁移

### 生成迁移脚本

```bash
cd backend
# 自动生成迁移 (基于模型变更)
uv run alembic revision --autogenerate -m "add_resource_table"

# 生成空白迁移 (手动编写)
uv run alembic revision -m "custom_migration"
```

### 检查生成的迁移文件

生成后必须检查 `backend/alembic/versions/` 中的新文件：

```python
# 典型的迁移文件结构
def upgrade() -> None:
    op.create_table(
        'resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        # ...
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_resources_id'), 'resources', ['id'], unique=False)
    op.create_index(op.f('ix_resources_name'), 'resources', ['name'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_resources_name'), table_name='resources')
    op.drop_index(op.f('ix_resources_id'), table_name='resources')
    op.drop_table('resources')
```

### 运行迁移

```bash
cd backend
# 升级到最新
uv run alembic upgrade head

# 降级一个版本
uv run alembic downgrade -1

# 查看当前版本
uv run alembic current

# 查看迁移历史
uv run alembic history --verbose
```

## 修改现有模型

修改现有列时，生成的迁移可能不完整，需手动补全：

```python
# 常用操作
op.add_column('table_name', sa.Column('new_col', sa.String(100)))
op.drop_column('table_name', 'old_col')
op.alter_column('table_name', 'col_name', type_=sa.String(500))
op.create_foreign_key('fk_name', 'from_table', 'to_table', ['fk_col'], ['id'])
```

## 规范要点

- **每次模型变更必须生成迁移**，不要直接修改数据库
- **迁移消息要清晰**: `-m "add_email_to_users"` 而非 `-m "update"`
- **迁移前备份**: 生产环境迁移前务必备份数据
- **双向可逆**: `upgrade()` 和 `downgrade()` 都要实现
- **命名约定**: 外键约束使用有意义的名称 `fk_{from}_{to}_{col}`
- **索引**: 常用于查询、过滤的字段添加 `index=True`
