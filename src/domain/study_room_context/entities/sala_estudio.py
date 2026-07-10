from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from ...exceptions import PermisoDenegadoError
from ...notebook_context.entities.cuaderno import Cuaderno
from ...notebook_context.entities.archivo import ArchivoResumen
from ...notebook_context.entities.chat import ChatResumen, Mensaje
from ...notebook_context.interfaces.lector_contenido import LectorContenido
from ...notebook_context.interfaces.participante_interactivo import ParticipanteInteractivo

@dataclass
class ParticipanteSala:
    id: int
    sala_id: int
    usuario_id: int

@dataclass
class SalaEstudio:
    id: int
    title: str
    codigo: str
    notebook_id: int
    creado_por_id: int
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SalaEstudioAdmin:
    """
    Controlador de administración para la sala de estudio.
    Otorga acceso sin restricciones de escritura al cuaderno interno.
    """
    sala: SalaEstudio
    cuaderno: Cuaderno
    participantes: List[ParticipanteSala] = field(default_factory=list)

class SalaEstudioInvitado(LectorContenido, ParticipanteInteractivo):
    """
    Proxy de Protección que envuelve a Cuaderno.
    Expone solo capacidades de lectura e interacción. 
    Lanza PermisoDenegadoError si se intenta realizar cualquier operación de administración o escritura.
    """
    def __init__(self, sala: SalaEstudio, cuaderno_vinculado: Cuaderno, lector: LectorContenido, interactivo: ParticipanteInteractivo):
        self.sala = sala
        self._cuaderno = cuaderno_vinculado
        self._lector = lector
        self._interactivo = interactivo

    # --- Implementación de LectorContenido ---
    async def listar_archivos(self) -> List[ArchivoResumen]:
        return await self._lector.listar_archivos()

    async def listar_chats(self) -> List[ChatResumen]:
        return await self._lector.listar_chats()

    async def obtener_texto_completo(self) -> str:
        return await self._lector.obtener_texto_completo()

    # --- Implementación de ParticipanteInteractivo ---
    async def enviar_mensaje_chat(self, chat_id: int, role: str, content: str) -> List[Mensaje]:
        return await self._interactivo.enviar_mensaje_chat(chat_id, role, content)

    # --- Métodos Bloqueados del Admin ---
    async def agregar_archivo(self, filename: str, content: str, file_type: str):
        raise PermisoDenegadoError("Los participantes invitados no pueden agregar archivos a la sala de estudio.")

    async def eliminar_archivo(self, archivo_id: int):
        raise PermisoDenegadoError("Los participantes invitados no pueden eliminar archivos de la sala de estudio.")
