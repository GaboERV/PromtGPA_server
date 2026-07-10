from typing import Protocol, List, Optional
from ..entities.examen import Examen
from ...notebook_context.entities.flashcard import Flashcard

class RAGEngineService(Protocol):
    """
    Puerto de Inteligencia Artificial para el motor RAG.
    Es flexible y acepta o bien identificadores de archivos o bien el texto en crudo estructurado.
    """
    async def generar_flashcards_por_contexto(
        self, 
        prompt: str, 
        archivo_ids: Optional[List[int]] = None, 
        texto_crudo: Optional[str] = None, 
        cantidad: int = 5
    ) -> List[Flashcard]:
        """Genera flashcards a partir del contexto textual."""
        ...

    async def generar_examen_por_contexto(
        self, 
        prompt: str, 
        archivo_ids: Optional[List[int]] = None, 
        texto_crudo: Optional[str] = None
    ) -> Examen:
        """Genera una plantilla de examen estructurada a partir del contexto textual."""
        ...

    async def generar_respuesta_chat(
        self,
        prompt: str,
        historial: List[dict],
        texto_crudo: str
    ) -> str:
        """Genera una respuesta conversacional basada en el contexto y el historial del chat."""
        ...
