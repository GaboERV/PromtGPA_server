from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.database import Base

class NotebookORM(Base):
    __tablename__ = "notebooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relaciones de agregación
    usuario: Mapped["UserORM"] = relationship("UserORM", back_populates="notebooks")
    files: Mapped[List["FileORM"]] = relationship("FileORM", back_populates="notebook", cascade="all, delete-orphan")
    chats: Mapped[List["ChatORM"]] = relationship("ChatORM", back_populates="notebook", cascade="all, delete-orphan")
    flashcards: Mapped[List["FlashcardORM"]] = relationship("FlashcardORM", back_populates="notebook", cascade="all, delete-orphan")
    examenes: Mapped[List["ExamenORM"]] = relationship("ExamenORM", back_populates="notebook", cascade="all, delete-orphan")
    salas_estudio: Mapped[List["SalaEstudioORM"]] = relationship("SalaEstudioORM", back_populates="notebook", cascade="all, delete-orphan")

class FileORM(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # El contenido del archivo convertido a Markdown
    notebook_id: Mapped[int] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    notebook: Mapped[NotebookORM] = relationship(NotebookORM, back_populates="files")

class ChatORM(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notebook_id: Mapped[int] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    notebook: Mapped[NotebookORM] = relationship(NotebookORM, back_populates="chats")
    messages: Mapped[List["MessageORM"]] = relationship("MessageORM", back_populates="chat", cascade="all, delete-orphan")

class MessageORM(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # 'user' o 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    chat: Mapped[ChatORM] = relationship(ChatORM, back_populates="messages")

class FlashcardORM(Base):
    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    notebook_id: Mapped[int] = mapped_column(ForeignKey("notebooks.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    notebook: Mapped[NotebookORM] = relationship(NotebookORM, back_populates="flashcards")
