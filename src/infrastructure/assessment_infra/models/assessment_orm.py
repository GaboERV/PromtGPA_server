from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, ForeignKey, Integer, DateTime, Numeric, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.database import Base

class ExamenORM(Base):
    __tablename__ = "examenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notebook_id: Mapped[int] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    sala_id: Mapped[Optional[int]] = mapped_column(ForeignKey("salas_estudio.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    notebook: Mapped["NotebookORM"] = relationship("NotebookORM", back_populates="examenes")
    sala: Mapped[Optional["SalaEstudioORM"]] = relationship("SalaEstudioORM", back_populates="examenes")
    preguntas: Mapped[List["PreguntaExamenORM"]] = relationship("PreguntaExamenORM", back_populates="examen", cascade="all, delete-orphan")
    intentos: Mapped[List["IntentoExamenORM"]] = relationship("IntentoExamenORM", back_populates="examen", cascade="all, delete-orphan")

class PreguntaExamenORM(Base):
    __tablename__ = "preguntas_examen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    examen_id: Mapped[int] = mapped_column(ForeignKey("examenes.id", ondelete="CASCADE"), nullable=False)
    question_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    opciones: Mapped[dict] = mapped_column(JSON, nullable=False)  # Diccionario mapeado a JSON (ej. {"A": "opc1", "B": "opc2"})
    correct_answer: Mapped[str] = mapped_column(String(10), nullable=False)

    # Relación
    examen: Mapped[ExamenORM] = relationship(ExamenORM, back_populates="preguntas")
    respuestas_usuarios: Mapped[List["RespuestaUsuarioORM"]] = relationship("RespuestaUsuarioORM", back_populates="pregunta", cascade="all, delete-orphan")

class IntentoExamenORM(Base):
    __tablename__ = "intentos_examen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    examen_id: Mapped[int] = mapped_column(ForeignKey("examenes.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    participante_sala_id: Mapped[Optional[int]] = mapped_column(ForeignKey("participantes_sala.id", ondelete="SET NULL"), nullable=True)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # Guarda decimales (ej. 85.50)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    examen: Mapped[ExamenORM] = relationship(ExamenORM, back_populates="intentos")
    usuario: Mapped["UserORM"] = relationship("UserORM")
    respuestas: Mapped[List["RespuestaUsuarioORM"]] = relationship("RespuestaUsuarioORM", back_populates="intento", cascade="all, delete-orphan")

class RespuestaUsuarioORM(Base):
    __tablename__ = "respuestas_usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    intento_id: Mapped[int] = mapped_column(ForeignKey("intentos_examen.id", ondelete="CASCADE"), nullable=False)
    pregunta_id: Mapped[int] = mapped_column(ForeignKey("preguntas_examen.id", ondelete="CASCADE"), nullable=False)
    user_answer: Mapped[str] = mapped_column(String(10), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Relaciones
    intento: Mapped[IntentoExamenORM] = relationship(IntentoExamenORM, back_populates="respuestas")
    pregunta: Mapped[PreguntaExamenORM] = relationship(PreguntaExamenORM, back_populates="respuestas_usuarios")
