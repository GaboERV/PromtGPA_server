from typing import Protocol, List, Optional
from ..entities.chat import Mensaje
from ..entities.flashcard import Flashcard

class ParticipanteInteractivo(Protocol):
    """
    Interfaz interactiva para el cuaderno.
    Permite chatear o realizar exámenes/flashcards (sin permisos de escritura en archivos).
    """
    async def enviar_mensaje_chat(self, chat_id: int, role: str, content: str, usuario_id: int) -> List[Mensaje]: ...
    async def generar_flashcards(self, prompt: str, cantidad: int, archivo_ids: Optional[List[int]]) -> List[Flashcard]: ...
