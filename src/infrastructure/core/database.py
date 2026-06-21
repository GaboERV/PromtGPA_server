import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

# URL de conexión asíncrona a SQLite con aiosqlite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./prompt_gpt.db")

IS_TESTING = os.getenv("IS_TESTING", "false").lower() == "true"
engine_kwargs = {"echo": True}
if IS_TESTING:
    engine_kwargs["poolclass"] = NullPool

# Crear el motor asíncrono
engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Crear fábrica de sesiones asíncronas
async_session_maker = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Base declarativa para modelos ORM
class Base(DeclarativeBase):
    pass

# Generador asíncrono de sesión (Dependency para FastAPI / inyectores)
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
