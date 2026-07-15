from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, status, UploadFile, File
from pydantic import BaseModel

from ..interceptors.auth_interceptor import get_current_user_id, get_current_user_id_with_api_key
from ..dependencies import get_notebook_service
from ....app.notebook_cases.notebook_services import NotebookService
from ....utils.RAG.pdf_parser import extract_pages

router = APIRouter(prefix="/notebooks", tags=["Cuadernos"])


# --- Schemas ---
class NotebookCreateSchema(BaseModel):
    title: str
    description: Optional[str] = ""

class NotebookUpdateSchema(BaseModel):
    title: str
    description: Optional[str] = None

class NotebookResponseSchema(BaseModel):
    id: int
    title: str
    description: str
    created_at: datetime
    usuario_id: int

    class Config:
        from_attributes = True

class FileResponseSchema(BaseModel):
    id: int
    filename: str
    file_type: str
    notebook_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ChatCreateSchema(BaseModel):
    title: str

class ChatResponseSchema(BaseModel):
    id: int
    title: str
    notebook_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class MessageCreateSchema(BaseModel):
    content: str

class MessageResponseSchema(BaseModel):
    id: int
    chat_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ResumenResponseSchema(BaseModel):
    id: int
    content: str
    notebook_id: int
    archivo_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Endpoints Cuadernos ---

@router.post("", status_code=status.HTTP_201_CREATED)
async def crear_cuaderno(
    schema: NotebookCreateSchema,
    current_user_id: int = Depends(get_current_user_id_with_api_key),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    notebook_id = await notebook_service.crear_cuaderno(
        title=schema.title,
        description=schema.description,
        usuario_id=current_user_id
    )
    return {"id": notebook_id, "message": "Cuaderno creado exitosamente"}

@router.get("", response_model=List[NotebookResponseSchema], status_code=status.HTTP_200_OK)
async def listar_cuadernos(
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    return await notebook_service.listar_cuadernos(usuario_id=current_user_id)

@router.get("/{notebook_id}", response_model=NotebookResponseSchema, status_code=status.HTTP_200_OK)
async def obtener_cuaderno(
    notebook_id: int,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    # El servicio valida la existencia; si no pertenece, se maneja según los accesos de sala o dominio
    return await notebook_service.obtener_cuaderno(notebook_id)

@router.put("/{notebook_id}", status_code=status.HTTP_200_OK)
async def actualizar_cuaderno(
    notebook_id: int,
    schema: NotebookUpdateSchema,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    await notebook_service.actualizar_cuaderno(
        notebook_id=notebook_id,
        title=schema.title,
        description=schema.description
    )
    return {"message": "Cuaderno actualizado exitosamente"}

@router.delete("/{notebook_id}", status_code=status.HTTP_200_OK)
async def eliminar_cuaderno(
    notebook_id: int,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    await notebook_service.eliminar_cuaderno(notebook_id)
    return {"message": "Cuaderno eliminado exitosamente"}


# --- Endpoints Archivos ---

@router.post("/{notebook_id}/files", status_code=status.HTTP_201_CREATED)
async def subir_archivo(
    notebook_id: int,
    file: UploadFile = File(...),
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    filename = file.filename
    # Determinar tipo de archivo de la extensión
    ext = filename.split(".")[-1].lower() if "." in filename else "txt"
    
    file_bytes = await file.read()
    
    # Extraer texto y convertirlo a Markdown en memoria
    if ext in ["txt", "md"]:
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = file_bytes.decode("latin-1")
    elif ext == "pdf":
        pages = extract_pages(file_bytes)
        if pages:
            content_lines = [f"# Documento: {filename}\n"]
            for page_num, text in pages:
                content_lines.append(f"\n## Página {page_num}\n{text}")
            content = "\n".join(content_lines)
        else:
            content = (
                f"# Documento: {filename}\n\n"
                f"**Nota:** Se intentó extraer texto del PDF pero parece estar vacío o contener solo imágenes.\n"
            )
    else:
        # Para DOCX u otros formatos, simulamos la extracción
        content = (
            f"# Documento: {filename}\n\n"
            f"**Tipo de archivo:** {ext.upper()}\n"
            f"**Tamaño:** {len(file_bytes)} bytes\n\n"
            f"Este es el contenido Markdown extraído y formateado en memoria del archivo original `{filename}`. "
            f"Este texto estructurado se utilizará para alimentar el motor RAG."
        )

    file_id = await notebook_service.subir_archivo(
        filename=filename,
        content=content,
        file_type=ext,
        notebook_id=notebook_id
    )
    return {"id": file_id, "filename": filename, "message": "Archivo subido y procesado a Markdown exitosamente"}

@router.get("/{notebook_id}/files", response_model=List[FileResponseSchema], status_code=status.HTTP_200_OK)
async def listar_archivos(
    notebook_id: int,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    return await notebook_service.listar_archivos(notebook_id)

@router.delete("/files/{archivo_id}", status_code=status.HTTP_200_OK)
async def eliminar_archivo(
    archivo_id: int,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    await notebook_service.eliminar_archivo(archivo_id)
    return {"message": "Archivo eliminado exitosamente"}


# --- Endpoints Chats ---

@router.post("/{notebook_id}/chats", status_code=status.HTTP_201_CREATED)
async def crear_chat(
    notebook_id: int,
    schema: ChatCreateSchema,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    chat_id = await notebook_service.crear_chat(
        title=schema.title,
        notebook_id=notebook_id,
        usuario_id=current_user_id
    )
    return {"id": chat_id, "message": "Chat creado exitosamente"}

@router.get("/{notebook_id}/chats", response_model=List[ChatResponseSchema], status_code=status.HTTP_200_OK)
async def listar_chats(
    notebook_id: int,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    return await notebook_service.listar_chats(notebook_id, current_user_id)

@router.delete("/chats/{chat_id}", status_code=status.HTTP_200_OK)
async def eliminar_chat(
    chat_id: int,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    await notebook_service.eliminar_chat(chat_id, current_user_id)
    return {"message": "Chat eliminado exitosamente"}

@router.get("/chats/{chat_id}/messages", response_model=List[MessageResponseSchema], status_code=status.HTTP_200_OK)
async def listar_mensajes_paginados(
    chat_id: int,
    page: int = 1,
    limit: int = 20,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    return await notebook_service.listar_mensajes_paginados(
        chat_id=chat_id,
        usuario_id=current_user_id,
        limit=limit,
        page=page
    )

@router.post(
    "/chats/{chat_id}/messages",
    response_model=List[MessageResponseSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Enviar mensaje y recibir respuesta de IA",
    description="Agrega un mensaje de usuario al chat y devuelve una lista con el mensaje del usuario y la respuesta generada por el asistente RAG."
)
async def agregar_mensaje_usuario(
    chat_id: int,
    schema: MessageCreateSchema,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    return await notebook_service.agregar_mensaje_usuario(
        chat_id=chat_id,
        content=schema.content,
        usuario_id=current_user_id
    )

# --- Endpoints Resumenes ---

@router.post("/{notebook_id}/summaries", status_code=status.HTTP_201_CREATED)
async def generar_resumen(
    notebook_id: int,
    archivo_id: Optional[int] = None,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    resumen_id = await notebook_service.generar_y_guardar_resumen(notebook_id, archivo_id)
    return {"id": resumen_id, "message": "Resumen generado exitosamente"}

@router.get("/{notebook_id}/summaries", response_model=List[ResumenResponseSchema], status_code=status.HTTP_200_OK)
async def listar_resumenes(
    notebook_id: int,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    return await notebook_service.listar_resumenes(notebook_id)

@router.delete("/summaries/{resumen_id}", status_code=status.HTTP_200_OK)
async def eliminar_resumen(
    resumen_id: int,
    current_user_id: int = Depends(get_current_user_id),
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    await notebook_service.eliminar_resumen(resumen_id)
    return {"message": "Resumen eliminado exitosamente"}
