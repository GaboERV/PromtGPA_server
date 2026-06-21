import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.web.routers.user_router import router as user_router
from src.infrastructure.web.routers.notebook_router import router as notebook_router
from src.infrastructure.web.routers.study_room_router import router as study_room_router
from src.infrastructure.web.routers.assessment_router import router as assessment_router
from src.infrastructure.web.routers.progress_router import router as progress_router
from src.infrastructure.web.routers.api_key_router import router as api_key_router
from src.infrastructure.web.routers.webhook_router import router as webhook_router
from src.infrastructure.web.routers.admin_router import router as admin_router
from src.infrastructure.web.routers.health_router import router as health_router

from src.infrastructure.web.errors.error_handlers import register_error_handlers
from src.infrastructure.core.database import engine, Base



# Import all ORM models to ensure they are registered in SQLAlchemy metadata before create_all
from src.infrastructure.user_infra.models.user_orm import UserORM
from src.infrastructure.notebook_infra.models.notebook_orm import NotebookORM, FileORM, ChatORM, MessageORM, FlashcardORM
from src.infrastructure.study_room_infra.models.study_room_orm import SalaEstudioORM, ParticipanteSalaORM
from src.infrastructure.assessment_infra.models.assessment_orm import ExamenORM, PreguntaExamenORM, IntentoExamenORM, RespuestaUsuarioORM

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea automáticamente la base de datos al iniciar la aplicación."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="PromptGPT API",
    description="Backend en FastAPI con Arquitectura Hexagonal limpia",
    version="0.2.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
# Lee los orígenes permitidos desde la variable de entorno ALLOWED_ORIGINS
# (valores separados por coma). Por defecto apunta a localhost para desarrollo.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
)
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,       # Permite cookies cross-origin
    allow_methods=["*"],
    allow_headers=["*"],
)
# ─────────────────────────────────────────────────────────────────────────────

# Registrar manejadores de excepciones globales del dominio
register_error_handlers(app)

# Registrar controladores
app.include_router(user_router)
app.include_router(notebook_router)
app.include_router(study_room_router)
app.include_router(assessment_router)
app.include_router(progress_router)
app.include_router(api_key_router)
app.include_router(webhook_router)
app.include_router(admin_router)
app.include_router(health_router)

@app.on_event("startup")
async def startup():
    """
    Inicializa automáticamente la base de datos y crea todas las tablas físicas
    en SQLite si no existen previamente.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
def read_root():
    return {
        "status": "online", 
        "message": "Servidor PromptGPT activo y funcionando con todos los contextos (Usuarios, Cuadernos, Salas de Estudio y Evaluaciones)",
        "docs_url": "/docs"
    }