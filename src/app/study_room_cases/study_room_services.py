import random
import string
from datetime import datetime
from typing import List, Union, Optional

from ...domain.exceptions import (
    SalaNoEncontradaError,
    CuadernoNoEncontradoError,
    PermisoDenegadoError
)
from ...domain.study_room_context.entities.sala_estudio import (
    SalaEstudio,
    ParticipanteSala,
    SalaEstudioAdmin,
    SalaEstudioInvitado
)
from ...domain.study_room_context.interfaces.sala_estudio_repository import SalaEstudioRepository
from ...domain.notebook_context.interfaces.cuaderno_repository import CuadernoRepository
from ...domain.notebook_context.interfaces.lector_contenido import LectorContenido
from ...domain.notebook_context.interfaces.participante_interactivo import ParticipanteInteractivo
from ...domain.notebook_context.entities.archivo import ArchivoResumen
from ...domain.notebook_context.entities.chat import ChatResumen, Mensaje
from ...domain.notebook_context.entities.resumen import Resumen
from ..notebook_cases.notebook_services import NotebookService


class RepositoryLectorContenido(LectorContenido):
    """
    Adaptador concreto que implementa LectorContenido delegando consultas al CuadernoRepository.
    """
    def __init__(self, repo: CuadernoRepository, notebook_id: int):
        self.repo = repo
        self.notebook_id = notebook_id

    async def listar_archivos(self) -> List[ArchivoResumen]:
        cuaderno = await self.repo.get_by_id(self.notebook_id)
        if not cuaderno:
            raise CuadernoNoEncontradoError()
        return cuaderno.lista_archivos

    async def listar_chats(self, usuario_id: int) -> List[ChatResumen]:
        cuaderno = await self.repo.get_by_id(self.notebook_id)
        if not cuaderno:
            raise CuadernoNoEncontradoError()
        # Filtrar solo los chats del usuario activo para mantener aislamiento en la sala
        return [c for c in cuaderno.lista_chats if c.usuario_id == usuario_id]

    async def listar_resumenes(self) -> List[Resumen]:
        return await self.repo.list_resumenes_by_notebook_id(self.notebook_id)

    async def obtener_texto_completo(self) -> str:
        archivos = await self.repo.list_archivos_by_notebook_id(self.notebook_id)
        return "\n\n".join([f.content for f in archivos if f.content])


class RepositoryParticipanteInteractivo(ParticipanteInteractivo):
    """
    Adaptador concreto que implementa ParticipanteInteractivo delegando operaciones al NotebookService.
    """
    def __init__(self, notebook_service: NotebookService):
        self.notebook_service = notebook_service

    async def enviar_mensaje_chat(self, chat_id: int, role: str, content: str, usuario_id: int) -> List[Mensaje]:
        # Ignoramos el "role" porque la IA contesta automáticamente con agregar_mensaje_usuario
        return await self.notebook_service.agregar_mensaje_usuario(chat_id, content, usuario_id)


class StudyRoomService:
    def __init__(self, sala_repository: SalaEstudioRepository, cuaderno_repository: CuadernoRepository, notebook_service: NotebookService = None):
        self.sala_repository = sala_repository
        self.cuaderno_repository = cuaderno_repository
        self.notebook_service = notebook_service

    async def crear_sala(self, title: str, notebook_id: int, creado_por_id: int) -> int:
        # Validar que el cuaderno exista
        cuaderno = await self.cuaderno_repository.get_by_id(notebook_id)
        if not cuaderno:
            raise CuadernoNoEncontradoError()

        # Generar código alfanumérico único de 6 caracteres
        while True:
            codigo = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            existe_sala = await self.sala_repository.get_by_codigo(codigo)
            if not existe_sala:
                break

        sala = SalaEstudio(
            id=None,
            title=title,
            codigo=codigo,
            notebook_id=notebook_id,
            creado_por_id=creado_por_id,
            created_at=datetime.utcnow()
        )
        await self.sala_repository.save(sala)
        return sala.id

    async def unirse_a_sala(self, codigo: str, usuario_id: int) -> int:
        sala = await self.sala_repository.get_by_codigo(codigo.strip().upper())
        if not sala:
            raise SalaNoEncontradaError()

        # Si el usuario es el creador de la sala, no necesita agregarse como participante
        if sala.creado_por_id == usuario_id:
            return sala.id

        # Verificar si ya es participante
        participante = await self.sala_repository.get_participante(sala.id, usuario_id)
        if not participante:
            participante = ParticipanteSala(
                id=None,
                sala_id=sala.id,
                usuario_id=usuario_id
            )
            await self.sala_repository.save_participante(participante)

        return sala.id

    async def obtener_sala(self, sala_id: int) -> SalaEstudio:
        sala = await self.sala_repository.get_by_id(sala_id)
        if not sala:
            raise SalaNoEncontradaError()
        return sala

    async def listar_salas_creadas(self, usuario_id: int) -> List[SalaEstudio]:
        return await self.sala_repository.list_by_usuario_id(usuario_id)

    async def listar_salas_participa(self, usuario_id: int) -> List[SalaEstudio]:
        return await self.sala_repository.list_by_participante_id(usuario_id)

    async def obtener_acceso_sala(
        self, sala_id: int, usuario_id: int
    ) -> Union[SalaEstudioAdmin, SalaEstudioInvitado]:
        sala = await self.sala_repository.get_by_id(sala_id)
        if not sala:
            raise SalaNoEncontradaError()

        cuaderno = await self.cuaderno_repository.get_by_id(sala.notebook_id)
        if not cuaderno:
            raise CuadernoNoEncontradoError()

        # Si el usuario es el creador, tiene acceso total administrativo
        if sala.creado_por_id == usuario_id:
            participantes = await self.sala_repository.list_participantes(sala.id)
            return SalaEstudioAdmin(
                sala=sala,
                cuaderno=cuaderno,
                participantes=participantes
            )

        # De lo contrario, verificar si es un participante invitado
        participante = await self.sala_repository.get_participante(sala.id, usuario_id)
        if not participante:
            raise PermisoDenegadoError("No eres miembro de esta sala de estudio.")

        # Retornar el Proxy de Protección que encapsula el Cuaderno
        lector = RepositoryLectorContenido(self.cuaderno_repository, sala.notebook_id)
        interactivo = RepositoryParticipanteInteractivo(self.notebook_service)

        return SalaEstudioInvitado(
            sala=sala,
            cuaderno_vinculado=cuaderno,
            lector=lector,
            interactivo=interactivo
        )

    async def abandonar_sala(self, sala_id: int, usuario_id: int) -> None:
        sala = await self.sala_repository.get_by_id(sala_id)
        if not sala:
            raise SalaNoEncontradaError()

        if sala.creado_por_id == usuario_id:
            raise PermisoDenegadoError("El creador de la sala no puede abandonarla. Debe eliminarla.")

        participante = await self.sala_repository.get_participante(sala_id, usuario_id)
        if not participante:
            raise PermisoDenegadoError("No eres miembro de esta sala de estudio.")

        await self.sala_repository.delete_participante(sala_id, usuario_id)
