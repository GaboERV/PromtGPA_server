from dataclasses import dataclass
from datetime import datetime

@dataclass
class ArchivoResumen:
    id: int
    filename: str

@dataclass
class Archivo:
    id: int
    filename: str
    content: str  # Almacena el texto convertido a Markdown directamente en la base de datos
    file_type: str
    notebook_id: int
    created_at: datetime
