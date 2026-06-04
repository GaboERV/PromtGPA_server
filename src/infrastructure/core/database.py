import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# URL de conexión asíncrona a SQLite con aiosqlite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./prompt_gpt.db")

# Crear el motor asíncrono
engine = create_async_engine(DATABASE_URL, echo=True)

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
