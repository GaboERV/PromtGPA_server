from typing import List, Optional, Union
from datetime import datetime
from fastapi import APIRouter, Depends, status, UploadFile, File
from pydantic import BaseModel

from ..interceptors.auth_interceptor import get_current_user_id
from ..dependencies import get_study_room_service, get_notebook_service, get_assessment_service
from ....app.study_room_cases.study_room_services import StudyRoomService
from ....app.notebook_cases.notebook_services import NotebookService
from ....app.assessment_cases.assessment_services import AssessmentService
from ....domain.study_room_context.entities.sala_estudio import SalaEstudioInvitado, SalaEstudioAdmin
from ....domain.exceptions import PermisoDenegadoError

# Importar schemas de otros routers
from .notebook_router import FileResponseSchema, ChatResponseSchema, MessageResponseSchema, MessageCreateSchema, ResumenResponseSchema
from .assessment_router import (
    FlashcardResponseSchema,
    ExamenResponseSchema,
    FlashcardGenerateSchema,
    ExamGenerateSchema,
    map_examen_to_response
)

router = APIRouter(prefix="/study-rooms", tags=["Salas de Estudio"])


# --- Schemas ---
class StudyRoomCreateSchema(BaseModel):
    title: str
    notebook_id: int

class StudyRoomJoinSchema(BaseModel):
    codigo: str

class StudyRoomResponseSchema(BaseModel):
    id: int
    title: str
    codigo: str
    notebook_id: int
    creado_por_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ParticipantResponseSchema(BaseModel):
    id: int
    sala_id: int
    usuario_id: int

    class Config:
        from_attributes = True

class StudyRoomAccessSchema(BaseModel):
    role: str  # "admin" o "invitado"
    sala_id: int
    title: str
    codigo: str
    notebook_id: int
    creado_por_id: int

# --- Endpoints ---

@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_sala(
    schema: StudyRoomCreateSchema,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service)
):
    sala_id = await study_room_service.crear_sala(
        title=schema.title,
        notebook_id=schema.notebook_id,
        creado_por_id=current_user_id
    )
    sala = await study_room_service.obtener_sala(sala_id)
    return {
        "id": sala.id,
        "codigo": sala.codigo,
        "message": "Sala de estudio creada exitosamente"
    }

@router.post("/join", status_code=status.HTTP_200_OK)
async def unirse_a_sala(
    schema: StudyRoomJoinSchema,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service)
):
    sala_id = await study_room_service.unirse_a_sala(
        codigo=schema.codigo,
        usuario_id=current_user_id
    )
    return {
        "id": sala_id,
        "message": "Te has unido a la sala de estudio exitosamente"
    }

@router.get("/creadas", response_model=List[StudyRoomResponseSchema], status_code=status.HTTP_200_OK)
async def listar_salas_creadas(
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service)
):
    return await study_room_service.listar_salas_creadas(usuario_id=current_user_id)

@router.get("/participa", response_model=List[StudyRoomResponseSchema], status_code=status.HTTP_200_OK)
async def listar_salas_participa(
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service)
):
    return await study_room_service.listar_salas_participa(usuario_id=current_user_id)

@router.get("/{sala_id}", response_model=StudyRoomResponseSchema, status_code=status.HTTP_200_OK)
async def obtener_sala(
    sala_id: int,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service)
):
    return await study_room_service.obtener_sala(sala_id)

@router.get("/{sala_id}/acceso", response_model=StudyRoomAccessSchema, status_code=status.HTTP_200_OK)
async def obtener_acceso_sala(
    sala_id: int,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service)
):
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    if isinstance(acceso, SalaEstudioAdmin):
        return StudyRoomAccessSchema(
            role="admin",
            sala_id=acceso.sala.id,
            title=acceso.sala.title,
            codigo=acceso.sala.codigo,
            notebook_id=acceso.sala.notebook_id,
            creado_por_id=acceso.sala.creado_por_id
        )
    else:
        return StudyRoomAccessSchema(
            role="invitado",
            sala_id=acceso.sala.id,
            title=acceso.sala.title,
            codigo=acceso.sala.codigo,
            notebook_id=acceso.sala.notebook_id,
            creado_por_id=acceso.sala.creado_por_id
        )

# --- Endpoints Protegidos por Proxy de Escritura ---

@router.post("/{sala_id}/files", status_code=status.HTTP_201_CREATED)
async def agregar_archivo_sala(
    sala_id: int,
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    # Validar acceso
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    
    filename = file.filename
    ext = filename.split(".")[-1].lower() if "." in filename else "txt"
    file_bytes = await file.read()
    
    # Extraer texto y convertir a Markdown
    if ext in ["txt", "md"]:
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = file_bytes.decode("latin-1")
    else:
        content = (
            f"# Documento: {filename}\n\n"
            f"**Tipo de archivo:** {ext.upper()}\n"
            f"**Tamaño:** {len(file_bytes)} bytes\n\n"
            f"Contenido Markdown extraído en la sala de estudio."
        )

    # Validar escritura con el proxy si es Invitado (arrojará PermisoDenegadoError)
    if isinstance(acceso, SalaEstudioInvitado):
        await acceso.agregar_archivo(filename, content, ext)
    
    # Si es Admin, subir el archivo al cuaderno
    file_id = await notebook_service.subir_archivo(
        filename=filename,
        content=content,
        file_type=ext,
        notebook_id=acceso.sala.notebook_id
    )
    
    return {"id": file_id, "filename": filename, "message": "Archivo subido exitosamente en la sala de estudio"}

@router.delete("/{sala_id}/files/{archivo_id}", status_code=status.HTTP_200_OK)
async def eliminar_archivo_sala(
    sala_id: int,
    archivo_id: int,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    
    # Validar con el proxy
    if isinstance(acceso, SalaEstudioInvitado):
        await acceso.eliminar_archivo(archivo_id)
        
    await notebook_service.eliminar_archivo(archivo_id)
    return {"message": "Archivo eliminado exitosamente de la sala de estudio"}


# --- Endpoints de Colaboración para Invitados y Admins ---

@router.get("/{sala_id}/files", response_model=List[FileResponseSchema], status_code=status.HTTP_200_OK)
async def listar_archivos_sala(
    sala_id: int,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    return await notebook_service.listar_archivos(acceso.sala.notebook_id)

@router.get("/{sala_id}/chats", response_model=List[ChatResponseSchema], status_code=status.HTTP_200_OK)
async def listar_chats_sala(
    sala_id: int,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    return await notebook_service.listar_chats(acceso.sala.notebook_id, current_user_id)

@router.get("/{sala_id}/summaries", response_model=List[ResumenResponseSchema], status_code=status.HTTP_200_OK)
async def listar_resumenes_sala(
    sala_id: int,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    # Los resúmenes son públicos para todos los participantes de la sala
    return await notebook_service.listar_resumenes(acceso.sala.notebook_id)

@router.get("/{sala_id}/chats/{chat_id}/messages", response_model=List[MessageResponseSchema], status_code=status.HTTP_200_OK)
async def listar_mensajes_paginados_sala(
    sala_id: int,
    chat_id: int,
    page: int = 1,
    limit: int = 20,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    # Valida la membresía de la sala
    await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    return await notebook_service.listar_mensajes_paginados(chat_id, current_user_id, limit, page)

@router.post(
    "/{sala_id}/chats/{chat_id}/messages",
    response_model=List[MessageResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensaje de sala y recibir respuesta de IA",
    description="Permite a administradores o invitados enviar un mensaje a la sala de estudio y devuelve tanto el mensaje enviado como la respuesta generada por la IA basándose en los documentos de la sala."
)
async def enviar_mensaje_chat_sala(
    sala_id: int,
    chat_id: int,
    schema: MessageCreateSchema,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    if isinstance(acceso, SalaEstudioInvitado):
        # Envía a través del proxy de invitado
        return await acceso.enviar_mensaje_chat(chat_id, "user", schema.content, current_user_id)
    else:
        # Creador / Admin
        return await notebook_service.agregar_mensaje_usuario(
            chat_id=chat_id,
            content=schema.content,
            usuario_id=current_user_id
        )

@router.post("/{sala_id}/flashcards", response_model=List[FlashcardResponseSchema], status_code=status.HTTP_201_CREATED)
async def generar_flashcards_sala(
    sala_id: int,
    schema: FlashcardGenerateSchema,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    # Permite a invitados y administradores generar flashcards para estudiar
    return await assessment_service.generar_flashcards(
        notebook_id=acceso.sala.notebook_id,
        prompt=schema.prompt,
        cantidad=schema.cantidad,
        archivo_ids=schema.archivo_ids
    )

@router.get("/{sala_id}/flashcards", response_model=List[FlashcardResponseSchema], status_code=status.HTTP_200_OK)
async def listar_flashcards_sala(
    sala_id: int,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    return await assessment_service.listar_flashcards(acceso.sala.notebook_id)

@router.post("/{sala_id}/exam", response_model=ExamenResponseSchema, status_code=status.HTTP_201_CREATED)
async def generar_examen_sala(
    sala_id: int,
    schema: ExamGenerateSchema,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    acceso = await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    if isinstance(acceso, SalaEstudioInvitado):
        raise PermisoDenegadoError("Solo los administradores de la sala de estudio pueden generar exámenes.")
    
    examen = await assessment_service.generar_examen(
        notebook_id=acceso.sala.notebook_id,
        prompt=schema.prompt,
        sala_id=sala_id,
        archivo_ids=schema.archivo_ids
    )
    return map_examen_to_response(examen)

@router.get("/{sala_id}/exams", response_model=List[ExamenResponseSchema], status_code=status.HTTP_200_OK)
async def listar_examenes_sala(
    sala_id: int,
    current_user_id: int = Depends(get_current_user_id),
    study_room_service: StudyRoomService = Depends(get_study_room_service),
    assessment_service: AssessmentService = Depends(get_assessment_service)
):
    await study_room_service.obtener_acceso_sala(sala_id, current_user_id)
    examenes = await assessment_service.listar_examenes_por_sala(sala_id)
    return [map_examen_to_response(e) for e in examenes]
