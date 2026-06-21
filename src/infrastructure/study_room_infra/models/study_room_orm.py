from datetime import datetime
from typing import List
from sqlalchemy import String, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.database import Base

class SalaEstudioORM(Base):
    __tablename__ = "salas_estudio"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    notebook_id: Mapped[int] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    notebook: Mapped["NotebookORM"] = relationship("NotebookORM", back_populates="salas_estudio")
    creador: Mapped["UserORM"] = relationship("UserORM", foreign_keys=[creado_por_id])
    participantes: Mapped[List["ParticipanteSalaORM"]] = relationship("ParticipanteSalaORM", back_populates="sala", cascade="all, delete-orphan")
    examenes: Mapped[List["ExamenORM"]] = relationship("ExamenORM", back_populates="sala")

class ParticipanteSalaORM(Base):
    __tablename__ = "participantes_sala"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sala_id: Mapped[int] = mapped_column(ForeignKey("salas_estudio.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relaciones
    sala: Mapped[SalaEstudioORM] = relationship(SalaEstudioORM, back_populates="participantes")
    usuario: Mapped["UserORM"] = relationship("UserORM")
