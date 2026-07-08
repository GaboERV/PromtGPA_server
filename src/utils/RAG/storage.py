"""
Storage de archivos. Por ahora local; pensado para migrar a S3.
Patrón Strategy: LocalStorage / S3Storage.
"""
import os
import shutil
from pathlib import Path
from uuid import UUID, uuid4
from abc import ABC, abstractmethod


class IStorage(ABC):
    @abstractmethod
    async def save(self, file_bytes: bytes, organization_id: UUID, filename: str) -> str:
        ...

    @abstractmethod
    async def read(self, file_path: str) -> bytes:
        ...

    @abstractmethod
    async def delete(self, file_path: str) -> None:
        ...


class LocalStorage(IStorage):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, file_bytes: bytes, organization_id: UUID, filename: str) -> str:
        org_dir = self.base_path / str(organization_id)
        org_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(filename).suffix
        unique_name = f"{uuid4()}{ext}"
        file_path = org_dir / unique_name
        file_path.write_bytes(file_bytes)
        return str(file_path.relative_to(self.base_path))

    async def read(self, file_path: str) -> bytes:
        full_path = self.base_path / file_path
        return full_path.read_bytes()

    async def delete(self, file_path: str) -> None:
        full_path = self.base_path / file_path
        if full_path.exists():
            full_path.unlink()


def get_storage() -> IStorage:
    if os.getenv("STORAGE_BACKEND") == "local":
        return LocalStorage(os.getenv("STORAGE_LOCAL_PATH"))
    raise NotImplementedError(f"Storage backend {os.getenv('STORAGE_BACKEND')} no implementado")
