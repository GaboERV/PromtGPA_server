from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional

@dataclass
class PreguntaExamen:
    id: int
    examen_id: int
    question_text: str
    opciones: Dict[str, str]  # Mapea letras como 'A', 'B', 'C', 'D' a las opciones de texto
    correct_answer: str       # Almacena el valor correcto ('A', 'B', etc.)

@dataclass
class Examen:
    id: int
    title: str
    notebook_id: int
    sala_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    preguntas: List[PreguntaExamen] = field(default_factory=list)

@dataclass
class RespuestaUsuario:
    id: int
    intento_id: int
    pregunta_id: int
    user_answer: str          # La opción escogida por el alumno ('A', 'B', etc.)
    is_correct: bool          # Evalúa si user_answer == correct_answer

@dataclass
class IntentoExamen:
    id: int
    examen_id: int
    usuario_id: int
    score: float              # Calificación decimal (de 0 a 100 o escala similar)
    participante_sala_id: Optional[int] = None
    completed_at: datetime = field(default_factory=datetime.utcnow)
    respuestas: List[RespuestaUsuario] = field(default_factory=list)
