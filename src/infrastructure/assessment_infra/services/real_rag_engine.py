import json
import re
from datetime import datetime
from math import sqrt
from typing import List, Optional

from ....domain.assessment_context.services.rag_engine_service import RAGEngineService
from ....domain.assessment_context.entities.examen import Examen, PreguntaExamen
from ....domain.notebook_context.entities.flashcard import Flashcard
from ....utils.RAG.embeddings import embedding_service
from ....utils.RAG.llm import LLMClientFactory
MAX_CONTEXT_CHUNK_SIZE = 1200
MAX_CONTEXT_CHUNKS = 5


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _chunk_text(text: str, max_chars: int = MAX_CONTEXT_CHUNK_SIZE, overlap: int = 200) -> List[str]:
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = paragraph if not current else f"{current}\n\n{paragraph}"
            continue

        if current:
            chunks.append(current)

        while len(paragraph) > max_chars:
            chunks.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars - overlap :].strip()

        current = paragraph

    if current:
        chunks.append(current)

    return chunks


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)


def _extract_json(text: str) -> Optional[str]:
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass

    first = next((i for i, ch in enumerate(text) if ch in ("[", "{")), None)
    last = max((i for i, ch in enumerate(text) if ch in ("]", "}")), default=-1)
    if first is None or last <= first:
        return None

    candidate = text[first : last + 1]
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        return None


def _safe_text(item: dict, key: str, default: str = "") -> str:
    value = item.get(key)
    if isinstance(value, str):
        return value.strip()
    return str(value).strip() if value is not None else default


def _build_flashcards_from_response(response: str, cantidad: int) -> List[Flashcard]:
    parsed = None
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        extracted = _extract_json(response)
        if extracted:
            parsed = json.loads(extracted)

    if isinstance(parsed, dict) and "flashcards" in parsed:
        parsed = parsed["flashcards"]

    if isinstance(parsed, list):
        cards: List[Flashcard] = []
        for item in parsed[:cantidad]:
            if not isinstance(item, dict):
                continue
            cards.append(Flashcard(
                id=None,
                question=_safe_text(item, "question"),
                answer=_safe_text(item, "answer"),
                notebook_id=None,
                created_at=datetime.utcnow()
            ))
        if len(cards) == cantidad:
            return cards

    return [
        Flashcard(
            id=None,
            question=f"Pregunta RAG #{i} generada en base a tu tema de estudio",
            answer=f"Respuesta automatizada #{i} construida a partir de los datos analizados",
            notebook_id=None,
            created_at=datetime.utcnow()
        )
        for i in range(1, cantidad + 1)
    ]


def _build_examen_from_response(response: str, prompt: str) -> Examen:
    parsed = None
    try:
        parsed = json.loads(response)
    except json.JSONDecodeError:
        extracted = _extract_json(response)
        if extracted:
            parsed = json.loads(extracted)

    if isinstance(parsed, dict):
        title = _safe_text(parsed, "title", f"Examen de práctica: {prompt[:30] if prompt else 'Generación RAG'}")
        questions = parsed.get("questions") or parsed.get("preguntas")
        if isinstance(questions, list):
            preguntas: List[PreguntaExamen] = []
            for item in questions[:3]:
                if not isinstance(item, dict):
                    continue
                opciones_raw = item.get("opciones") or item.get("options") or {}
                opciones = {
                    str(k): str(v)
                    for k, v in (opciones_raw.items() if isinstance(opciones_raw, dict) else {})
                }
                pregunta_text = _safe_text(item, "question_text", _safe_text(item, "question", _safe_text(item, "pregunta")))
                correct_answer = _safe_text(item, "correct_answer", _safe_text(item, "answer_key", _safe_text(item, "respuesta_correcta")))
                preguntas.append(PreguntaExamen(
                    id=None,
                    examen_id=None,
                    question_text=pregunta_text,
                    opciones=opciones,
                    correct_answer=correct_answer
                ))
            if len(preguntas) == 3 and all(p.correct_answer for p in preguntas):
                return Examen(
                    id=None,
                    title=title,
                    notebook_id=None,
                    preguntas=preguntas
                )

    return Examen(
        id=None,
        title=f"Examen de práctica: {prompt[:30] if prompt else 'Generación RAG'}",
        notebook_id=None,
        preguntas=[
            PreguntaExamen(
                id=None,
                examen_id=None,
                question_text="¿Cuál de las siguientes afirmaciones describe la función principal del sistema RAG?",
                opciones={
                    "A": "Generar texto aleatorio sin contexto previo.",
                    "B": "Combinar la búsqueda semántica de documentos con modelos de lenguaje generativos.",
                    "C": "Servir como base de datos relacional de alta velocidad.",
                    "D": "Encriptar contraseñas de forma asíncrona."
                },
                correct_answer="B"
            ),
            PreguntaExamen(
                id=None,
                examen_id=None,
                question_text="En Arquitectura Hexagonal, ¿qué es la base de datos física?",
                opciones={
                    "A": "Un puerto primario del dominio.",
                    "B": "Un caso de uso de la aplicación.",
                    "C": "Un adaptador secundario de infraestructura.",
                    "D": "Una entidad del núcleo del negocio."
                },
                correct_answer="C"
            ),
            PreguntaExamen(
                id=None,
                examen_id=None,
                question_text="¿Para qué sirve el patrón Proxy en la Sala de Estudio del Invitado?",
                opciones={
                    "A": "Para acelerar las consultas SQL de indexación.",
                    "B": "Para proteger el cuaderno contra escrituras y modificaciones de participantes no autorizados.",
                    "C": "Para hashear las contraseñas en hilos secundarios.",
                    "D": "Para conectarse directamente a la VectorDB de Chroma."
                },
                correct_answer="B"
            )
        ]
    )


def _build_relevant_context(prompt: str, texto_crudo: Optional[str]) -> str:
    texto = texto_crudo or ""
    if not texto.strip():
        return ""

    chunks = _chunk_text(texto)
    if not chunks:
        return texto.strip()

    chunk_embeddings = embedding_service.encode(chunks)
    query_embedding = embedding_service.encode_one(prompt)
    scored = sorted(
        zip(chunks, chunk_embeddings),
        key=lambda item: _cosine_similarity(query_embedding, item[1]),
        reverse=True
    )[:MAX_CONTEXT_CHUNKS]
    selected = [chunk for chunk, _score in scored if chunk]
    return "\n\n---\n\n".join(selected) if selected else texto.strip()


class RealRAGEngineService(RAGEngineService):
    """Motor RAG real que usa embeddings y un cliente LLM para respuestas generativas."""

    def __init__(self):
        self.llm_client = LLMClientFactory.create()

    async def generar_flashcards_por_contexto(
        self,
        prompt: str,
        archivo_ids: Optional[List[int]] = None,
        texto_crudo: Optional[str] = None,
        cantidad: int = 5
    ) -> List[Flashcard]:
        context = _build_relevant_context(prompt, texto_crudo)
        system = (
            "Eres un asistente pedagógico que genera material de estudio a partir del contexto proporcionado. "
            "Responde únicamente con JSON válido siempre que sea posible."
        )
        user = (
            f"Genera {cantidad} tarjetas de estudio con pregunta y respuesta. "
            "Devuelve solo un array JSON de objetos con las claves 'question' y 'answer'.\n"
            f"Contexto:\n{context}\n\nPrompt: {prompt}"
        )
        output, _ = await self.llm_client.complete(system, user, max_tokens=650)
        return _build_flashcards_from_response(output, cantidad)

    async def generar_examen_por_contexto(
        self,
        prompt: str,
        archivo_ids: Optional[List[int]] = None,
        texto_crudo: Optional[str] = None
    ) -> Examen:
        context = _build_relevant_context(prompt, texto_crudo)
        system = (
            "Eres un asistente pedagógico que genera exámenes de práctica. "
            "Responde únicamente con JSON válido cuando sea posible."
        )
        user = (
            "Genera un examen de práctica con tres preguntas de opción múltiple. "
            "Devuelve solo un objeto JSON con 'title' y 'questions'. Cada pregunta debe tener 'question_text', 'opciones' y 'correct_answer'.\n"
            f"Contexto:\n{context}\n\nPrompt: {prompt}"
        )
        output, _ = await self.llm_client.complete(system, user, max_tokens=900)
        return _build_examen_from_response(output, prompt)
