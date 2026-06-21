from typing import List, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ..interceptors.auth_interceptor import get_current_user_id
from ..dependencies import get_db_session
from ...notebook_infra.models.notebook_orm import NotebookORM, FlashcardORM, MessageORM, ChatORM, FileORM
from ...assessment_infra.models.assessment_orm import IntentoExamenORM

router = APIRouter(prefix="/progress", tags=["Progreso"])

# --- Endpoints ---

@router.get("/metrics", status_code=status.HTTP_200_OK)
async def obtener_metricas(
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retorna el promedio de calificaciones y cantidad de examenes resueltos.
    """
    stmt = select(IntentoExamenORM).where(IntentoExamenORM.usuario_id == current_user_id)
    result = await session.execute(stmt)
    intentos = result.scalars().all()
    
    if intentos:
        avg_score = sum(float(i.score) for i in intentos) / len(intentos)
    else:
        avg_score = 0.0
        
    return {
        "total_exams_completed": len(intentos),
        "average_score": round(avg_score, 2)
    }

@router.get("/pending-cards", status_code=status.HTTP_200_OK)
async def listar_tarjetas_pendientes(
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retorna las flashcards asociadas a los cuadernos del usuario.
    """
    stmt = select(FlashcardORM).join(NotebookORM).where(NotebookORM.usuario_id == current_user_id)
    result = await session.execute(stmt)
    flashcards = result.scalars().all()
    
    return [
        {
            "id": f.id,
            "question": f.question,
            "answer": f.answer,
            "notebook_id": f.notebook_id,
            "created_at": f.created_at
        } for f in flashcards
    ]

@router.get("/daily-activity", status_code=status.HTTP_200_OK)
async def obtener_actividad_diaria(
    current_user_id: int = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Retorna la actividad diaria consolidando mensajes, intentos de examen y archivos subidos.
    """
    # 1. Mensajes
    stmt_messages = (
        select(MessageORM.created_at)
        .join(ChatORM, MessageORM.chat_id == ChatORM.id)
        .join(NotebookORM, ChatORM.notebook_id == NotebookORM.id)
        .where(NotebookORM.usuario_id == current_user_id, MessageORM.role == "user")
    )
    result_m = await session.execute(stmt_messages)
    message_dates = [dt.date() for dt in result_m.scalars().all()]
    
    # 2. Intentos de examen
    stmt_attempts = (
        select(IntentoExamenORM.completed_at)
        .where(IntentoExamenORM.usuario_id == current_user_id)
    )
    result_a = await session.execute(stmt_attempts)
    attempt_dates = [dt.date() for dt in result_a.scalars().all()]
    
    # 3. Archivos subidos
    stmt_files = (
        select(FileORM.created_at)
        .join(NotebookORM, FileORM.notebook_id == NotebookORM.id)
        .where(NotebookORM.usuario_id == current_user_id)
    )
    result_f = await session.execute(stmt_files)
    file_dates = [dt.date() for dt in result_f.scalars().all()]
    
    # Consolidacion
    activity_by_date = {}
    for d in message_dates + attempt_dates + file_dates:
        d_str = d.isoformat()
        activity_by_date[d_str] = activity_by_date.get(d_str, 0) + 1
        
    daily_activity = [
        {"date": d, "events_count": count} for d, count in sorted(activity_by_date.items())
    ]
    return daily_activity
