from datetime import datetime
from sqlalchemy import String, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.database import Base
from typing import List

class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    # Relación uno-a-muchos: Un usuario tiene muchos cuadernos.
    # El tipo se anota como string "NotebookORM" para evitar acoplamiento de importación circular directa.
    notebooks: Mapped[List["NotebookORM"]] = relationship(
        "NotebookORM", back_populates="usuario", cascade="all, delete-orphan"
    )
