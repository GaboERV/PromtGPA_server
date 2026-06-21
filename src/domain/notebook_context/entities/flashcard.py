from dataclasses import dataclass
from datetime import datetime

@dataclass
class FlashcardResumen:
    id: int
    question: str

@dataclass
class Flashcard:
    id: int
    question: str
    answer: str
    notebook_id: int
    created_at: datetime
