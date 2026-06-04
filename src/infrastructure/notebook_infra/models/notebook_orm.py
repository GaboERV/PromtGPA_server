from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.database import Base

class NotebookORM(Base):
    __tablename__ = "notebooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relación muchos-a-uno: Varios cuadernos pertenecen a un usuario.
    # El tipo se anota como string "UserORM" para evitar acoplamiento de importación circular directa.
    usuario: Mapped["UserORM"] = relationship("UserORM", back_populates="notebooks")
