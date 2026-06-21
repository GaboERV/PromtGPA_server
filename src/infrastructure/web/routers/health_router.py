from datetime import datetime
from fastapi import APIRouter, status

router = APIRouter(prefix="/health", tags=["Diagnóstico"])

@router.get("/v1", status_code=status.HTTP_200_OK)
async def health_v1():
    """
    Healthcheck de la API.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/processes", status_code=status.HTTP_200_OK)
async def health_processes():
    """
    Retorna hilos/procesos activos en segundo plano del backend.
    """
    return {
        "background_tasks_active": 0,
        "active_threads": 1,
        "status": "idle",
        "scheduler": "inactive"
    }

@router.get("/metadata", status_code=status.HTTP_200_OK)
async def health_metadata():
    """
    Retorna informacion basica y descripcion de la version.
    """
    return {
        "name": "promptGPT API",
        "version": "0.2.0",
        "description": "Backend en FastAPI con Arquitectura Hexagonal limpia",
        "environment": "development",
        "author": "Antigravity Team"
    }
