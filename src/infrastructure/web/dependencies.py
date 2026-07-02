from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database import get_db_session

# User domain/infra
from ..user_infra.repositories import SqlAlchemyUsuarioRepository
from ..user_infra.services import BcryptEncryptService, JwtTokenService
from ...app.user_cases.user_services import UserService

# Notebook domain/infra
from ..notebook_infra.repositories import SqlAlchemyCuadernoRepository
from ...app.notebook_cases.notebook_services import NotebookService

# Study room domain/infra
from ..study_room_infra.repositories import SqlAlchemySalaRepository
from ...app.study_room_cases.study_room_services import StudyRoomService

# Assessment domain/infra
from ..assessment_infra.repositories import SqlAlchemyExamenRepository
from ..assessment_infra.services import RealRAGEngineService, SimulatedRAGEngineService
from ...app.assessment_cases.assessment_services import AssessmentService


# --- Autenticación y Seguridad ---
def get_encrypt_service() -> BcryptEncryptService:
    """Retorna la implementación concreta del cifrador."""
    return BcryptEncryptService()

def get_token_service() -> JwtTokenService:
    """Retorna la implementación concreta del gestor de tokens."""
    return JwtTokenService()


# --- Usuarios ---
def get_user_repository(session: AsyncSession = Depends(get_db_session)) -> SqlAlchemyUsuarioRepository:
    """Fábrica para instanciar el repositorio físico de usuarios."""
    return SqlAlchemyUsuarioRepository(session)

def get_user_service(
    repository: SqlAlchemyUsuarioRepository = Depends(get_user_repository),
    encrypt_service: BcryptEncryptService = Depends(get_encrypt_service),
    token_service: JwtTokenService = Depends(get_token_service)
) -> UserService:
    return UserService(repository, encrypt_service, token_service)


# --- Cuadernos ---
def get_notebook_repository(session: AsyncSession = Depends(get_db_session)) -> SqlAlchemyCuadernoRepository:
    """Fábrica para instanciar el repositorio físico de cuadernos."""
    return SqlAlchemyCuadernoRepository(session)

def get_notebook_service(
    repository: SqlAlchemyCuadernoRepository = Depends(get_notebook_repository)
) -> NotebookService:
    return NotebookService(repository)


# --- Salas de Estudio ---
def get_study_room_repository(session: AsyncSession = Depends(get_db_session)) -> SqlAlchemySalaRepository:
    """Fábrica para instanciar el repositorio físico de salas de estudio."""
    return SqlAlchemySalaRepository(session)

def get_study_room_service(
    sala_repository: SqlAlchemySalaRepository = Depends(get_study_room_repository),
    cuaderno_repository: SqlAlchemyCuadernoRepository = Depends(get_notebook_repository)
) -> StudyRoomService:
    return StudyRoomService(sala_repository, cuaderno_repository)


# --- Evaluaciones e IA ---
def get_examen_repository(session: AsyncSession = Depends(get_db_session)) -> SqlAlchemyExamenRepository:
    """Fábrica para instanciar el repositorio físico de exámenes."""
    return SqlAlchemyExamenRepository(session)

def get_rag_engine_service() -> RealRAGEngineService:
    """Retorna la implementación real del motor RAG."""
    return RealRAGEngineService()

# TODO: use SimulatedRAGEngineService for local development with a feature flag if needed.

def get_assessment_service(
    examen_repository: SqlAlchemyExamenRepository = Depends(get_examen_repository),
    cuaderno_repository: SqlAlchemyCuadernoRepository = Depends(get_notebook_repository),
    rag_engine: RealRAGEngineService = Depends(get_rag_engine_service)
) -> AssessmentService:
    return AssessmentService(examen_repository, cuaderno_repository, rag_engine)
