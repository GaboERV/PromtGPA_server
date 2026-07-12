from datetime import datetime
from typing import List, Optional
from ...domain.notebook_context.entities.cuaderno import Cuaderno
from ...domain.notebook_context.entities.archivo import Archivo
from ...domain.notebook_context.entities.chat import Chat, Mensaje
from ...domain.notebook_context.entities.resumen import Resumen
from ...domain.notebook_context.interfaces.cuaderno_repository import CuadernoRepository
from ...domain.assessment_context.services.rag_engine_service import RAGEngineService
from ...domain.exceptions import CuadernoNoEncontradoError, PermisoDenegadoError

class NotebookService:
    def __init__(self, repository: CuadernoRepository, rag_engine: Optional[RAGEngineService] = None):
        self.repository = repository
        self.rag_engine = rag_engine

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
    async def crear_chat(self, title: str, notebook_id: int, usuario_id: int) -> int:
        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()

        chat = Chat(
            id=None,
            title=title,
            notebook_id=notebook_id,
            usuario_id=usuario_id,
            created_at=datetime.utcnow()
        )
        await self.repository.save_chat(chat)
        return chat.id

    async def listar_chats(self, notebook_id: int, usuario_id: int) -> List[Chat]:
        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()
        return await self.repository.list_chats_by_notebook_id(notebook_id, usuario_id)

    async def eliminar_chat(self, chat_id: int, usuario_id: int) -> None:
        chat = await self.repository.get_chat_by_id(chat_id)
        if chat is None or chat.usuario_id != usuario_id:
            raise PermisoDenegadoError()
        await self.repository.delete_chat(chat_id)

    # --- Mensajes Paginados ---
    async def listar_mensajes_paginados(self, chat_id: int, usuario_id: int, limit: int = 20, page: int = 1) -> List[Mensaje]:
        chat = await self.repository.get_chat_by_id(chat_id)
        if chat is None or chat.usuario_id != usuario_id:
            raise PermisoDenegadoError()
        
        offset = (page - 1) * limit
        return await self.repository.get_messages_paginated(chat_id, limit, offset)

    async def agregar_mensaje_usuario(self, chat_id: int, content: str, usuario_id: int) -> List[Mensaje]:
        chat = await self.repository.get_chat_by_id(chat_id)
        if chat is None or chat.usuario_id != usuario_id:
            raise PermisoDenegadoError()
            
        # Guardar mensaje de usuario
        mensaje = Mensaje(
            id=None,
            chat_id=chat_id,
            role="user",
            content=content,
            created_at=datetime.utcnow()
        )
        await self.repository.save_message(mensaje)

        mensajes_resultado = [mensaje]

        # Generar respuesta de IA si el motor está disponible
        if self.rag_engine:
            chat = await self.repository.get_chat_by_id(chat_id)
            if chat:
                archivos = await self.repository.list_archivos_by_notebook_id(chat.notebook_id)
                texto_crudo = "\n\n".join([a.content for a in archivos if a.content])
                
                # Obtener historial reciente para el contexto del bot (últimos 10 mensajes)
                historial_db = await self.repository.get_messages_paginated(chat_id, limit=10, offset=0)
                # Invertir para orden cronológico
                historial_db.reverse()
                historial = [{"role": m.role, "content": m.content} for m in historial_db if m.id != mensaje.id]

                respuesta_ai_texto = await self.rag_engine.generar_respuesta_chat(content, historial, texto_crudo)
                
                mensaje_ai = Mensaje(
                    id=None,
                    chat_id=chat_id,
                    role="assistant",
                    content=respuesta_ai_texto,
                    created_at=datetime.utcnow()
                )
                await self.repository.save_message(mensaje_ai)
                mensajes_resultado.append(mensaje_ai)

        return mensajes_resultado

    # --- Resumenes ---
    async def generar_y_guardar_resumen(self, notebook_id: int, archivo_id: Optional[int] = None) -> int:
        if not self.rag_engine:
            raise Exception("Motor RAG no está disponible para generar resúmenes.")

        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()

        texto_crudo = ""
        if archivo_id:
            archivo = await self.repository.get_archivo_by_id(archivo_id)
            if archivo and archivo.notebook_id == notebook_id:
                texto_crudo = archivo.content
        else:
            archivos = await self.repository.list_archivos_by_notebook_id(notebook_id)
            texto_crudo = "\n\n".join([a.content for a in archivos if a.content])

        if not texto_crudo.strip():
            raise Exception("No hay contenido suficiente para resumir.")

        resumen_texto = await self.rag_engine.generar_resumen_por_contexto(texto_crudo)

        resumen = Resumen(
            id=None,
            content=resumen_texto,
            notebook_id=notebook_id,
            archivo_id=archivo_id,
            created_at=datetime.utcnow()
        )
        await self.repository.save_resumen(resumen)
        return resumen.id

    async def listar_resumenes(self, notebook_id: int) -> List[Resumen]:
        cuaderno = await self.repository.get_by_id(notebook_id)
        if cuaderno is None:
            raise CuadernoNoEncontradoError()
        return await self.repository.list_resumenes_by_notebook_id(notebook_id)

    async def eliminar_resumen(self, resumen_id: int) -> None:
        await self.repository.delete_resumen(resumen_id)
