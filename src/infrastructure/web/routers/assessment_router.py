from typing import List, Optional, Dict
from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from ..interceptors.auth_interceptor import get_current_user_id
from ..dependencies import get_assessment_service
from ....app.assessment_cases.assessment_services import AssessmentService

router = APIRouter(prefix="/assessments", tags=["Evaluaciones"])


# --- Schemas ---
class FlashcardGenerateSchema(BaseModel):
    notebook_id: int
    prompt: str
    cantidad: Optional[int] = 5
    archivo_ids: Optional[List[int]] = None

class FlashcardResponseSchema(BaseModel):
    id: int
    question: str
    answer: str
    notebook_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ExamGenerateSchema(BaseModel):
    notebook_id: int
    prompt: str
    sala_id: Optional[int] = None
    archivo_ids: Optional[List[int]] = None

class OptionSchema(BaseModel):
    letra: str
    texto: str

class PreguntaExamenResponseSchema(BaseModel):
    id: int
    question_text: str
    opciones: List[OptionSchema]

    class Config:
        from_attributes = True

class ExamenResponseSchema(BaseModel):
    id: int
    title: str
    notebook_id: int
    sala_id: Optional[int]
    created_at: datetime
    preguntas: List[PreguntaExamenResponseSchema]

    class Config:
        from_attributes = True

class RespuestaSubmitSchema(BaseModel):
    pregunta_id: int
    opcion: str

class SubmitExamSchema(BaseModel):
    respuestas: List[RespuestaSubmitSchema]
    participante_sala_id: Optional[int] = None

class RespuestaDetalleSchema(BaseModel):
    id: int
    pregunta_id: int
    opcion: str
    is_correct: bool

    class Config:
        from_attributes = True

class IntentoExamenResponseSchema(BaseModel):
    id: int
    examen_id: int
    usuario_id: int
    participante_sala_id: Optional[int]
    score: float
    completed_at: datetime
    respuestas: List[RespuestaDetalleSchema]

    class Config:
        from_attributes = True


# --- Mapeadores de Dominio a Respuestas de API ---

def map_examen_to_response(examen) -> dict:
    return {
        "id": examen.id,
        "title": examen.title,
        "notebook_id": examen.notebook_id,
        "sala_id": examen.sala_id,
        "created_at": examen.created_at,
        "preguntas": [
            {
                "id": p.id,
                "question_text": p.question_text,
                "opciones": [
                    {"letra": k, "texto": v} for k, v in p.opciones.items()
                ]
            }
            for p in examen.preguntas
        ]
    }

def map_intento_to_response(intento) -> dict:
    return {
        "id": intento.id,
        "examen_id": intento.examen_id,
        "usuario_id": intento.usuario_id,
        "participante_sala_id": intento.participante_sala_id,
        "score": float(intento.score),
        "completed_at": intento.completed_at,
        "respuestas": [
            {
                "id": r.id,
                "pregunta_id": r.pregunta_id,
                "opcion": r.user_answer,
                "is_correct": r.is_correct
            }
            for r in intento.respuestas
        ]
    }


# --- Endpoints Flashcards ---

@router.post("/flashcards", response_model=List[FlashcardResponseSchema], status_code=status.HTTP_201_CREATED)
async def generar_flashcards(
    schema: FlashcardGenerateSchema,
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    return await assessment_service.generar_flashcards(
        notebook_id=schema.notebook_id,
        user_id=current_user_id,
        prompt=schema.prompt,
        cantidad=schema.cantidad,
        archivo_ids=schema.archivo_ids
    )

@router.get("/flashcards/{notebook_id}", response_model=List[FlashcardResponseSchema], status_code=status.HTTP_200_OK)
async def listar_flashcards(
    notebook_id: int,
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    return await assessment_service.listar_flashcards(notebook_id, current_user_id)


# --- Endpoints Exámenes ---

@router.post("/exam", response_model=ExamenResponseSchema, status_code=status.HTTP_201_CREATED)
async def generar_examen(
    schema: ExamGenerateSchema,
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    examen = await assessment_service.generar_examen(
        notebook_id=schema.notebook_id,
        user_id=current_user_id,
        prompt=schema.prompt,
        sala_id=schema.sala_id,
        archivo_ids=schema.archivo_ids
    )
    return map_examen_to_response(examen)

@router.get("/exam/{examen_id}", response_model=ExamenResponseSchema, status_code=status.HTTP_200_OK)
async def obtener_examen(
    examen_id: int,
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    examen = await assessment_service.obtener_examen(examen_id, current_user_id)
    return map_examen_to_response(examen)

@router.get("/exam/notebook/{notebook_id}", response_model=List[ExamenResponseSchema], status_code=status.HTTP_200_OK)
async def listar_examenes_por_cuaderno(
    notebook_id: int,
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    examenes = await assessment_service.listar_examenes_por_cuaderno(notebook_id, current_user_id)
    return [map_examen_to_response(e) for e in examenes]

@router.get("/exam/sala/{sala_id}", response_model=List[ExamenResponseSchema], status_code=status.HTTP_200_OK)
async def listar_examenes_por_sala(
    sala_id: int,
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    examenes = await assessment_service.listar_examenes_por_sala(sala_id)
    return [map_examen_to_response(e) for e in examenes]


from fastapi import BackgroundTasks
import uuid
from ...core.memory_state import add_webhook_attempt, deliver_webhook_async

@router.post("/exam/{examen_id}/submit", response_model=IntentoExamenResponseSchema, status_code=status.HTTP_201_CREATED)
async def resolver_examen(
    examen_id: int,
    schema: SubmitExamSchema,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    respuestas_dict = {r.pregunta_id: r.opcion for r in schema.respuestas}
    intento = await assessment_service.resolver_examen(
        examen_id=examen_id,
        usuario_id=current_user_id,
        respuestas_usuario=respuestas_dict,
        participante_sala_id=schema.participante_sala_id
    )
    
    # --- Disparar Webhooks Asincronos si aplica ---
    try:
        examen = await assessment_service.obtener_examen(examen_id)
        if examen and examen.sala_id:
            # Buscar suscripciones para esta sala (org_id)
            from ...core.memory_state import get_webhook_subscriptions_by_org
            subs = await get_webhook_subscriptions_by_org(examen.sala_id)
            if subs:
                payload = {
                    "event": "exam.completed",
                    "org_id": examen.sala_id,
                    "intento_id": intento.id,
                    "examen_id": examen_id,
                    "usuario_id": current_user_id,
                    "score": float(intento.score),
                    "completed_at": intento.completed_at.isoformat()
                }
                for sub in subs:
                    attempt_id = str(uuid.uuid4())
                    attempt = {
                        "id": attempt_id,
                        "subscription_id": sub["id"],
                        "url": sub["url"],
                        "payload": payload,
                        "status_code": None,
                        "response_body": None,
                        "timestamp": datetime.utcnow(),
                        "success": False
                    }
                    await add_webhook_attempt(attempt)
                    background_tasks.add_task(
                        deliver_webhook_async,
                        attempt_id,
                        sub["url"],
                        payload
                    )
    except Exception as e:
        # Los errores de webhook no deben interrumpir la experiencia principal del usuario
        pass
        
    return map_intento_to_response(intento)

@router.get("/attempts", response_model=List[IntentoExamenResponseSchema], status_code=status.HTTP_200_OK)
async def listar_intentos_usuario(
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    intentos = await assessment_service.listar_intentos_usuario(usuario_id=current_user_id)
    return [map_intento_to_response(i) for i in intentos]

@router.get("/attempts/{intento_id}", response_model=IntentoExamenResponseSchema, status_code=status.HTTP_200_OK)
async def obtener_intento(
    intento_id: int,
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    intento = await assessment_service.obtener_intento(intento_id)
    return map_intento_to_response(intento)

@router.get("/attempts/exam/{examen_id}", response_model=List[IntentoExamenResponseSchema], status_code=status.HTTP_200_OK)
async def listar_intentos_examen(
    examen_id: int,
    current_user_id: int = Depends(get_current_user_id),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    intentos = await assessment_service.listar_intentos_examen(examen_id)
    return [map_intento_to_response(i) for i in intentos]
