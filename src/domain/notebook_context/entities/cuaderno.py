from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from .archivo import ArchivoResumen
from .chat import ChatResumen
from .flashcard import FlashcardResumen

@dataclass
class Cuaderno:
    id: int
    title: str
    usuario_id: int
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Colecciones de resúmenes ligeros cargados bajo demanda o metadatos básicos
    lista_archivos: List[ArchivoResumen] = field(default_factory=list)
    lista_chats: List[ChatResumen] = field(default_factory=list)
    lista_flashcards: List[FlashcardResumen] = field(default_factory=list)
