import uuid
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..interceptors.auth_interceptor import get_current_user_id
from ...core.memory_state import (
    add_webhook_subscription,
    get_webhook_subscriptions_by_org,
    get_webhook_attempts,
    get_webhook_attempt_by_id,
    add_webhook_attempt,
    deliver_webhook_async
)

router = APIRouter(tags=["Webhooks"])

# --- Schemas ---
class WebhookSubscriptionCreateSchema(BaseModel):
    org_id: int
    url: str

class WebhookSubscriptionResponseSchema(BaseModel):
    id: int
    org_id: int
    url: str
    created_at: datetime

class WebhookAttemptResponseSchema(BaseModel):
    id: str
    subscription_id: int
    url: str
    payload: dict
    status_code: Optional[int]
    response_body: Optional[str]
    timestamp: datetime
    success: bool

# --- Endpoints ---

@router.post("/webhooks/subscriptions", response_model=WebhookSubscriptionResponseSchema, status_code=status.HTTP_201_CREATED)
async def registrar_webhook(
    schema: WebhookSubscriptionCreateSchema,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Registra una suscripcion de webhook para una organizacion/sala de estudio en memoria.
    """
    from ...core.memory_state import get_all_webhook_subscriptions
    all_subs = await get_all_webhook_subscriptions()
    sub_id = len(all_subs) + 1
    sub = {
        "id": sub_id,
        "org_id": schema.org_id,
        "url": schema.url,
        "created_at": datetime.utcnow()
    }
    await add_webhook_subscription(sub)
    return sub

@router.get("/webhooks/subscriptions/org/{org_id}", response_model=List[WebhookSubscriptionResponseSchema], status_code=status.HTTP_200_OK)
async def listar_webhooks_org(
    org_id: int,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Lista los webhooks suscritos para una organizacion especifica.
    """
    return await get_webhook_subscriptions_by_org(org_id)

@router.get("/internal/webhooks/attempts", response_model=List[WebhookAttemptResponseSchema], status_code=status.HTTP_200_OK)
async def listar_intentos_webhooks(
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Consulta la bitacora de envios de webhooks.
    """
    return await get_webhook_attempts()

@router.post("/internal/webhooks/attempts/{attempt_id}/retry", status_code=status.HTTP_200_OK)
async def reintentar_webhook(
    attempt_id: str,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    Reintenta el envio de un webhook de forma asincrona.
    """
    past_attempt = await get_webhook_attempt_by_id(attempt_id)
    if not past_attempt:
        raise HTTPException(status_code=404, detail="Intento de webhook no encontrado.")
        
    new_id = str(uuid.uuid4())
    new_attempt = {
        "id": new_id,
        "subscription_id": past_attempt["subscription_id"],
        "url": past_attempt["url"],
        "payload": past_attempt["payload"],
        "status_code": None,
        "response_body": None,
        "timestamp": datetime.utcnow(),
        "success": False
    }
    await add_webhook_attempt(new_attempt)
    
    background_tasks.add_task(
        deliver_webhook_async,
        new_id,
        past_attempt["url"],
        past_attempt["payload"]
    )
    
    return {
        "message": "Reintento de webhook encolado",
        "attempt_id": new_id
    }
