from datetime import datetime
from typing import List, Optional
from ...domain.notebook_context.entities.cuaderno import Cuaderno
from ...domain.notebook_context.entities.archivo import Archivo
from ...domain.notebook_context.entities.chat import Chat, Mensaje
from ...domain.notebook_context.interfaces.cuaderno_repository import CuadernoRepository
from ...domain.exceptions import CuadernoNoEncontradoError

class NotebookService:
    def __init__(self, repository: CuadernoRepository):
        self.repository = repository

    async def crear_cuaderno(self, title: str, description: str, usuario_id: int) -> int:
        cuaderno = Cuaderno(
            id=None,
            title=title,
            description=description,
            usuario_id=usuario_id,
            created_at=datetime.utcnow()
        )
        await self.repository.save(cuaderno)
        return cuaderno.id

    async def listar_cuadernos(self, usuario_id: int) -> List[Cuaderno]:
        return await self.repository.list_by_usuario_id(usuario_id)

    async def obtener_cuaderno(self, notebook_id: int) -> Cuaderno:
        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()
        return cuaderno

    async def actualizar_cuaderno(self, notebook_id: int, title: str, description: Optional[str] = None) -> None:
        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()
        cuaderno.title = title
        if description is not None:
            cuaderno.description = description
        await self.repository.save(cuaderno)

    async def eliminar_cuaderno(self, notebook_id: int) -> None:
        await self.repository.delete(notebook_id)

    # --- Archivos ---
    async def subir_archivo(self, filename: str, content: str, file_type: str, notebook_id: int) -> int:
        """
        Carga el contenido de un archivo convertido a Markdown en la base de datos SQL.
        No se persiste ningún archivo físico en el servidor.
        """
        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()

        archivo = Archivo(
            id=None,
            filename=filename,
            content=content,  # Texto Markdown procesado
            file_type=file_type,
            notebook_id=notebook_id,
            created_at=datetime.utcnow()
        )
        await self.repository.save_archivo(archivo)
        return archivo.id

    async def listar_archivos(self, notebook_id: int) -> List[Archivo]:
        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()
        return await self.repository.list_archivos_by_notebook_id(notebook_id)

    async def eliminar_archivo(self, archivo_id: int) -> None:
        await self.repository.delete_archivo(archivo_id)

    # --- Chats ---
    async def crear_chat(self, title: str, notebook_id: int) -> int:
        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()

        chat = Chat(
            id=None,
            title=title,
            notebook_id=notebook_id,
            created_at=datetime.utcnow()
        )
        await self.repository.save_chat(chat)
        return chat.id

    async def listar_chats(self, notebook_id: int) -> List[Chat]:
        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()
        return await self.repository.list_chats_by_notebook_id(notebook_id)

    async def eliminar_chat(self, chat_id: int) -> None:
        await self.repository.delete_chat(chat_id)

    # --- Mensajes Paginados ---
    async def listar_mensajes_paginados(self, chat_id: int, limit: int = 20, page: int = 1) -> List[Mensaje]:
        offset = (page - 1) * limit
        return await self.repository.get_messages_paginated(chat_id, limit, offset)

    async def agregar_mensaje_usuario(self, chat_id: int, content: str) -> Mensaje:
        mensaje = Mensaje(
            id=None,
            chat_id=chat_id,
            role="user",
            content=content,
            created_at=datetime.utcnow()
        )
        await self.repository.save_message(mensaje)
        return mensaje
