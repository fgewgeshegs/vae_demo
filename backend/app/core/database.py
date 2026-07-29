"""数据库配置 - SQLAlchemy 2.0 async"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


async def get_db() -> AsyncSession:
    """获取数据库会话（依赖注入）"""
    async with async_session_factory() as session:
        try:
            yield session
            # 仅在会话事务仍活跃时提交（防止路由已手动提交导致双提交）
            if session.is_active:
                await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库表（开发环境使用）"""
    async with engine.begin() as conn:
        # 生产环境应使用 Alembic 迁移
        # 这里仅用于快速开发
        if conn.dialect.name == "postgresql":
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "postgresql":
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE")
            )
            await conn.execute(
                text("ALTER TABLE qa_records ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(36)")
            )
            await conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_qa_records_conversation_id ON qa_records(conversation_id)")
            )
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)"))
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunks_content_trgm "
                    "ON document_chunks USING gin (content gin_trgm_ops)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw "
                    "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
                )
            )
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_learning_tasks_user_id ON learning_tasks(user_id)"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_learning_tasks_status ON learning_tasks(status)"))
            if settings.admin_usernames:
                await conn.execute(
                    text("UPDATE users SET is_admin = TRUE WHERE lower(username) = ANY(:names)"),
                    {"names": list(settings.admin_usernames)},
                )


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()


async def load_runtime_configs():
    from app.core.config import apply_runtime_config
    from app.models.system_config import SystemConfig

    async with async_session_factory() as session:
        configs = (
            await session.execute(select(SystemConfig).where(SystemConfig.is_active == True))
        ).scalars().all()
        for config in configs:
            apply_runtime_config(config.config_key, config.config_value)
