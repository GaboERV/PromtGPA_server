from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ResumenResumen:
    id: int
    content_snippet: str
    created_at: datetime

@dataclass
class Resumen:
    id: int
    content: str
    notebook_id: int
    archivo_id: Optional[int]
    created_at: datetime
