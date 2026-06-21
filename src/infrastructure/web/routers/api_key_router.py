import os
import uuid
import jwt
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel

from ..interceptors.auth_interceptor import get_current_user_id, get_current_user_id_bearer_only
from ...core.memory_state import (
    add_api_key,
    get_active_api_keys,
    deactivate_api_key,
    add_audit_log,
    check_and_set_cooldown
)

COOLDOWN_SECONDS = int(os.getenv("API_KEY_COOLDOWN_SECONDS", "60"))

router = APIRouter(prefix="/api-keys", tags=["API Keys"])

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "prod-security-fallback-must-be-replaced-via-env")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# --- Schemas ---
class APIKeyCreateSchema(BaseModel):
    title: str

class APIKeyResponseSchema(BaseModel):
    id: str
    title: str
    created_at: datetime
    expires_at: datetime
    active: bool

# --- Endpoints ---

@router.post("", status_code=status.HTTP_201_CREATED)
async def generar_api_key(
    schema: APIKeyCreateSchema,
    current_user_id: int = Depends(get_current_user_id_bearer_only)
):
    """
    Genera una API Key firmada (JWT con claim jti) y la guarda en la bitacora in-memory.
    Enforce a cooldown rate limit per user to prevent mass token injection.
    """
    now = datetime.utcnow()
    allowed = await check_and_set_cooldown(current_user_id, COOLDOWN_SECONDS)
    if not allowed:
        # Registrar conducta sospechosa de generacion masiva
        await add_audit_log({
            "id": str(uuid.uuid4()),
            "user_id": current_user_id,
            "action": "SUSPICIOUS_MASS_TOKEN_CREATION",
            "timestamp": now,
            "ip": "127.0.0.1"
        })
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Límite excedido: Solo puedes generar una API Key cada {COOLDOWN_SECONDS} segundos para prevenir inyección masiva."
        )
        
    # Registrar log de auditoria
    await add_audit_log({
        "id": str(uuid.uuid4()),
        "user_id": current_user_id,
        "action": f"API_KEY_GENERATED: {schema.title}",
        "timestamp": now,
        "ip": "127.0.0.1"
    })
    
    jti = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    created_at = datetime.utcnow()
    
    payload = {
        "sub": str(current_user_id),
        "jti": jti,
        "exp": expires_at,
        "iat": datetime.now(timezone.utc)
    }
    
    api_key_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    api_key_meta = {
        "id": jti,
        "title": schema.title,
        "user_id": current_user_id,
        "created_at": created_at,
        "expires_at": expires_at,
        "active": True
    }
    await add_api_key(api_key_meta)
    
    return {
        "api_key": api_key_token,
        "title": schema.title,
        "jti": jti,
        "expires_at": expires_at
    }

@router.get("", response_model=List[APIKeyResponseSchema], status_code=status.HTTP_200_OK)
async def listar_api_keys(
    current_user_id: int = Depends(get_current_user_id_bearer_only)
):
    """
    Lista las API Keys creadas por el usuario.
    """
    user_keys = await get_active_api_keys(current_user_id)
    return [
        APIKeyResponseSchema(
            id=k["id"],
            title=k["title"],
            created_at=k["created_at"],
            expires_at=k["expires_at"],
            active=k["active"]
        ) for k in user_keys
    ]

@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def desactivar_api_key(
    key_id: str,
    current_user_id: int = Depends(get_current_user_id_bearer_only)
):
    """
    Invalida una API Key.
    """
    found = await deactivate_api_key(key_id, current_user_id)
    if not found:
        raise HTTPException(status_code=404, detail="API Key no encontrada.")
        
    return {"message": "API Key desactivada exitosamente"}
