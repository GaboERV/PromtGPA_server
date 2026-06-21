from typing import Protocol
from ..entities.chat import Mensaje

class ParticipanteInteractivo(Protocol):
    """
    Interfaz interactiva para el cuaderno.
    Permite chatear o realizar exámenes/flashcards (sin permisos de escritura en archivos).
    """
    async def enviar_mensaje_chat(self, chat_id: int, role: str, content: str) -> Mensaje: ...
