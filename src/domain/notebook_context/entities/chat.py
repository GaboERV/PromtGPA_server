from dataclasses import dataclass
from datetime import datetime

@dataclass
class ChatResumen:
    id: int
    title: str

@dataclass
class Chat:
    id: int
    title: str
    notebook_id: int
    created_at: datetime

@dataclass
class Mensaje:
    id: int
    chat_id: int
    role: str  # 'user' o 'assistant'
    content: str
    created_at: datetime
