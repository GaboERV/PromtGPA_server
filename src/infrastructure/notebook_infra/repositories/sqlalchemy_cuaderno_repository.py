from typing import List, Optional
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.notebook_context.interfaces.cuaderno_repository import CuadernoRepository
from ....domain.notebook_context.entities.cuaderno import Cuaderno
from ....domain.notebook_context.entities.archivo import Archivo, ArchivoResumen
from ....domain.notebook_context.entities.chat import Chat, ChatResumen, Mensaje
from ....domain.notebook_context.entities.flashcard import Flashcard, FlashcardResumen
from ..models.notebook_orm import NotebookORM, FileORM, ChatORM, MessageORM, FlashcardORM

class SqlAlchemyCuadernoRepository(CuadernoRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, orm: NotebookORM) -> Cuaderno:
        archivos = [ArchivoResumen(id=f.id, filename=f.filename) for f in orm.files]
        chats = [ChatResumen(id=c.id, title=c.title) for c in orm.chats]
        flashcards = [FlashcardResumen(id=fl.id, question=fl.question) for fl in orm.flashcards]
        return Cuaderno(
            id=orm.id,
            title=orm.title,
            usuario_id=orm.usuario_id,
            description=orm.description or "",
            created_at=orm.created_at,
            lista_archivos=archivos,
            lista_chats=chats,
            lista_flashcards=flashcards
        )

    async def get_by_id(self, notebook_id: int) -> Optional[Cuaderno]:
        stmt = (
            select(NotebookORM)
            .where(NotebookORM.id == notebook_id)
            .options(
                selectinload(NotebookORM.files),
                selectinload(NotebookORM.chats),
                selectinload(NotebookORM.flashcards)
            )
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_usuario_id(self, usuario_id: int) -> List[Cuaderno]:
        stmt = (
            select(NotebookORM)
            .where(NotebookORM.usuario_id == usuario_id)
            .options(
                selectinload(NotebookORM.files),
                selectinload(NotebookORM.chats),
                selectinload(NotebookORM.flashcards)
            )
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def save(self, cuaderno: Cuaderno) -> None:
        orm = None
        if cuaderno.id is not None:
            stmt = select(NotebookORM).where(NotebookORM.id == cuaderno.id)
            result = await self.session.execute(stmt)
            orm = result.scalar_one_or_none()

        if orm is None:
            orm = NotebookORM(
                title=cuaderno.title,
                description=cuaderno.description,
                usuario_id=cuaderno.usuario_id,
                created_at=cuaderno.created_at
            )
            self.session.add(orm)
            await self.session.flush()
            cuaderno.id = orm.id
        else:
            orm.title = cuaderno.title
            orm.description = cuaderno.description

    async def delete(self, notebook_id: int) -> None:
        stmt = select(NotebookORM).where(NotebookORM.id == notebook_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)

    # --- Archivos ---
    async def get_archivo_by_id(self, archivo_id: int) -> Optional[Archivo]:
        stmt = select(FileORM).where(FileORM.id == archivo_id)
        result = await self.session.execute(stmt)
        f = result.scalar_one_or_none()
        return Archivo(f.id, f.filename, f.content, f.file_type, f.notebook_id, f.created_at) if f else None

    async def save_archivo(self, archivo: Archivo) -> None:
        orm = None
        if archivo.id is not None:
            stmt = select(FileORM).where(FileORM.id == archivo.id)
            result = await self.session.execute(stmt)
            orm = result.scalar_one_or_none()

        if orm is None:
            orm = FileORM(
                filename=archivo.filename,
                path="",
                file_type=archivo.file_type,
                content=archivo.content,
                notebook_id=archivo.notebook_id,
                created_at=archivo.created_at
            )
            self.session.add(orm)
            await self.session.flush()
            archivo.id = orm.id
        else:
            orm.filename = archivo.filename
            orm.content = archivo.content

    async def delete_archivo(self, archivo_id: int) -> None:
        stmt = select(FileORM).where(FileORM.id == archivo_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)

    async def list_archivos_by_notebook_id(self, notebook_id: int) -> List[Archivo]:
        stmt = select(FileORM).where(FileORM.notebook_id == notebook_id)
        result = await self.session.execute(stmt)
        return [
            Archivo(f.id, f.filename, f.content, f.file_type, f.notebook_id, f.created_at)
            for f in result.scalars().all()
        ]

    # --- Chats ---
    async def get_chat_by_id(self, chat_id: int) -> Optional[Chat]:
        stmt = select(ChatORM).where(ChatORM.id == chat_id)
        result = await self.session.execute(stmt)
        c = result.scalar_one_or_none()
        return Chat(c.id, c.title, c.notebook_id, c.created_at) if c else None

    async def save_chat(self, chat: Chat) -> None:
        orm = None
        if chat.id is not None:
            stmt = select(ChatORM).where(ChatORM.id == chat.id)
            result = await self.session.execute(stmt)
            orm = result.scalar_one_or_none()

        if orm is None:
            orm = ChatORM(
                title=chat.title,
                notebook_id=chat.notebook_id,
                created_at=chat.created_at
            )
            self.session.add(orm)
            await self.session.flush()
            chat.id = orm.id
        else:
            orm.title = chat.title

    async def delete_chat(self, chat_id: int) -> None:
        stmt = select(ChatORM).where(ChatORM.id == chat_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)

    async def list_chats_by_notebook_id(self, notebook_id: int) -> List[Chat]:
        stmt = select(ChatORM).where(ChatORM.notebook_id == notebook_id)
        result = await self.session.execute(stmt)
        return [
            Chat(c.id, c.title, c.notebook_id, c.created_at)
            for c in result.scalars().all()
        ]

    # --- Mensajes Paginados ---
    async def get_messages_paginated(self, chat_id: int, limit: int, offset: int) -> List[Mensaje]:
        stmt = (
            select(MessageORM)
            .where(MessageORM.chat_id == chat_id)
            .order_by(MessageORM.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [
            Mensaje(m.id, m.chat_id, m.role, m.content, m.created_at)
            for m in result.scalars().all()
        ]

    async def save_message(self, message: Mensaje) -> None:
        orm = MessageORM(
            role=message.role,
            content=message.content,
            chat_id=message.chat_id,
            created_at=message.created_at
        )
        self.session.add(orm)
        await self.session.flush()
        message.id = orm.id

    # --- Flashcards ---
    async def save_flashcard(self, flashcard: Flashcard) -> None:
        orm = FlashcardORM(
            question=flashcard.question,
            answer=flashcard.answer,
            notebook_id=flashcard.notebook_id,
            created_at=flashcard.created_at
        )
        self.session.add(orm)
        await self.session.flush()
        flashcard.id = orm.id

    async def list_flashcards_by_notebook_id(self, notebook_id: int) -> List[Flashcard]:
        stmt = select(FlashcardORM).where(FlashcardORM.notebook_id == notebook_id)
        result = await self.session.execute(stmt)
        return [
            Flashcard(fl.id, fl.question, fl.answer, fl.notebook_id, fl.created_at)
            for fl in result.scalars().all()
        ]
