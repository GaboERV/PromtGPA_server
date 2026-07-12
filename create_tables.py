import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from src.infrastructure.notebook_infra.models.notebook_orm import Base as NotebookBase

engine = create_async_engine("sqlite+aiosqlite:///prompt_gpt.db")

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(NotebookBase.metadata.create_all)
        print("Tablas sincronizadas.")

if __name__ == "__main__":
    asyncio.run(main())
