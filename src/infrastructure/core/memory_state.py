import os
import json
import uuid
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Any
import httpx
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL")
_redis_client_by_loop = {}

def get_redis_client():
    """
    Retorna un cliente de Redis enlazado al bucle de eventos (event loop) actual.
    Esto evita errores de 'Event loop is closed' cuando la suite de pruebas o
    el servidor recrean event loops entre distintas peticiones.
    """
    if not REDIS_URL:
        return None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return None
        
    if loop not in _redis_client_by_loop:
        try:
            client = aioredis.from_url(REDIS_URL, decode_responses=True)
            _redis_client_by_loop[loop] = client
            logger.debug(f"Cliente de Redis creado para el loop: {id(loop)}")
        except Exception as e:
            logger.error(f"Error al inicializar Redis client en loop {id(loop)}: {str(e)}")
            return None
    return _redis_client_by_loop[loop]

# --- JSON Helpers with Datetime Serialization ---
def _serialize_datetime(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def serialize_json(data: dict) -> str:
    return json.dumps(data, default=_serialize_datetime)

def deserialize_json(data_str: str) -> dict:
    data = json.loads(data_str)
    for key, val in data.items():
        if isinstance(val, str):
            if len(val) >= 19 and "-" in val and ":" in val:
                try:
                    clean_val = val.replace("Z", "+00:00")
                    data[key] = datetime.fromisoformat(clean_val)
                except ValueError:
                    pass
    return data

# --- Fallback Local In-Memory Databases ---
used_jti_set: Set[str] = set()
last_api_key_generation: Dict[int, datetime] = {}
api_keys_db: List[Dict] = []
webhook_subscriptions: List[Dict] = []
webhook_attempts: List[Dict] = []
audit_logs_db: List[Dict] = []

# --- Helper Functions with Auto Fallback ---

async def check_and_use_jti(jti: str) -> bool:
    """
    Verifica si una llave de un solo uso ya fue consumida.
    Si no, la marca como consumida en Redis (o en memoria) y retorna True.
    """
    client = get_redis_client()
    if client:
        try:
            key = f"promptgpt:jti:{jti}"
            success = await client.set(key, "1", ex=2592000, nx=True)
            return success is not None
        except Exception as e:
            logger.error(f"Error en Redis check_and_use_jti: {str(e)}. Usando fallback en memoria.")
    
    if jti in used_jti_set:
        return False
    used_jti_set.add(jti)
    return True

async def check_and_set_cooldown(user_id: int, cooldown_seconds: int) -> bool:
    """
    Verifica si el usuario esta en cooldown de generacion de API Keys.
    Si no, establece el cooldown en Redis (o memoria) y retorna True.
    """
    client = get_redis_client()
    if client:
        try:
            key = f"promptgpt:cooldown:{user_id}"
            success = await client.set(key, "1", ex=cooldown_seconds, nx=True)
            return success is not None
        except Exception as e:
            logger.error(f"Error en Redis check_and_set_cooldown: {str(e)}. Usando fallback en memoria.")
            
    now = datetime.utcnow()
    last_gen = last_api_key_generation.get(user_id)
    if last_gen and (now - last_gen) < timedelta(seconds=cooldown_seconds):
        return False
    last_api_key_generation[user_id] = now
    return True

# --- API Keys Helpers ---

async def add_api_key(meta: dict) -> None:
    client = get_redis_client()
    if client:
        try:
            await client.hset("promptgpt:api_keys", meta["id"], serialize_json(meta))
            return
        except Exception as e:
            logger.error(f"Error en Redis add_api_key: {str(e)}. Usando fallback.")
    api_keys_db.append(meta)

async def get_active_api_keys(user_id: int) -> List[dict]:
    client = get_redis_client()
    if client:
        try:
            keys_map = await client.hgetall("promptgpt:api_keys")
            active_keys = []
            for k, v in keys_map.items():
                meta = deserialize_json(v)
                if meta["user_id"] == user_id:
                    is_used = await client.get(f"promptgpt:jti:{meta['id']}")
                    meta["active"] = meta["active"] and not is_used
                    active_keys.append(meta)
            return active_keys
        except Exception as e:
            logger.error(f"Error en Redis get_active_api_keys: {str(e)}. Usando fallback.")
             
    user_keys = []
    for k in api_keys_db:
        if k["user_id"] == user_id:
            is_active = k["active"] and k["id"] not in used_jti_set
            user_keys.append({**k, "active": is_active})
    return user_keys

async def deactivate_api_key(key_id: str, user_id: int) -> bool:
    client = get_redis_client()
    if client:
        try:
            val = await client.hget("promptgpt:api_keys", key_id)
            if val:
                meta = deserialize_json(val)
                if meta["user_id"] == user_id:
                    meta["active"] = False
                    await client.hset("promptgpt:api_keys", key_id, serialize_json(meta))
                    await client.setex(f"promptgpt:jti:{key_id}", 2592000, "1")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error en Redis deactivate_api_key: {str(e)}. Usando fallback.")
             
    for k in api_keys_db:
        if k["id"] == key_id and k["user_id"] == user_id:
            k["active"] = False
            used_jti_set.add(key_id)
            return True
    return False

# --- Webhook Subscriptions Helpers ---

async def add_webhook_subscription(sub: dict) -> None:
    client = get_redis_client()
    if client:
        try:
            await client.hset("promptgpt:webhook_subscriptions", str(sub["id"]), serialize_json(sub))
            return
        except Exception as e:
            logger.error(f"Error en Redis add_webhook_subscription: {str(e)}. Usando fallback.")
    webhook_subscriptions.append(sub)

async def get_webhook_subscriptions_by_org(org_id: int) -> List[dict]:
    client = get_redis_client()
    if client:
        try:
            subs_map = await client.hgetall("promptgpt:webhook_subscriptions")
            return [deserialize_json(v) for v in subs_map.values() if deserialize_json(v)["org_id"] == org_id]
        except Exception as e:
            logger.error(f"Error en Redis get_webhook_subscriptions_by_org: {str(e)}. Usando fallback.")
    return [s for s in webhook_subscriptions if s["org_id"] == org_id]

async def get_all_webhook_subscriptions() -> List[dict]:
    client = get_redis_client()
    if client:
        try:
            subs_map = await client.hgetall("promptgpt:webhook_subscriptions")
            return [deserialize_json(v) for v in subs_map.values()]
        except Exception as e:
            logger.error(f"Error en Redis get_all_webhook_subscriptions: {str(e)}. Usando fallback.")
    return webhook_subscriptions

# --- Webhook Attempts Helpers ---

async def add_webhook_attempt(attempt: dict) -> None:
    client = get_redis_client()
    if client:
        try:
            await client.hset("promptgpt:webhook_attempts", attempt["id"], serialize_json(attempt))
            return
        except Exception as e:
            logger.error(f"Error en Redis add_webhook_attempt: {str(e)}. Usando fallback.")
    webhook_attempts.append(attempt)

async def update_webhook_attempt(attempt_id: str, status_code: Optional[int], response_body: Optional[str], success: bool) -> None:
    client = get_redis_client()
    if client:
        try:
            val = await client.hget("promptgpt:webhook_attempts", attempt_id)
            if val:
                attempt = deserialize_json(val)
                attempt["status_code"] = status_code
                attempt["response_body"] = response_body
                attempt["success"] = success
                attempt["timestamp"] = datetime.utcnow()
                await client.hset("promptgpt:webhook_attempts", attempt_id, serialize_json(attempt))
                return
        except Exception as e:
            logger.error(f"Error en Redis update_webhook_attempt: {str(e)}. Usando fallback.")
             
    for a in webhook_attempts:
        if a["id"] == attempt_id:
            a["status_code"] = status_code
            a["response_body"] = response_body
            a["success"] = success
            a["timestamp"] = datetime.utcnow()
            break

async def get_webhook_attempts() -> List[dict]:
    client = get_redis_client()
    if client:
        try:
            attempts_map = await client.hgetall("promptgpt:webhook_attempts")
            attempts = [deserialize_json(v) for v in attempts_map.values()]
            attempts.sort(key=lambda x: x["timestamp"])
            return attempts
        except Exception as e:
            logger.error(f"Error en Redis get_webhook_attempts: {str(e)}. Usando fallback.")
    return webhook_attempts

async def get_webhook_attempt_by_id(attempt_id: str) -> Optional[dict]:
    client = get_redis_client()
    if client:
        try:
            val = await client.hget("promptgpt:webhook_attempts", attempt_id)
            if val:
                return deserialize_json(val)
            return None
        except Exception as e:
            logger.error(f"Error en Redis get_webhook_attempt_by_id: {str(e)}. Usando fallback.")
    for a in webhook_attempts:
        if a["id"] == attempt_id:
            return a
    return None

# --- Audit Logs Helpers ---

async def add_audit_log(log: dict) -> None:
    client = get_redis_client()
    if client:
        try:
            await client.lpush("promptgpt:audit_logs", serialize_json(log))
            await client.ltrim("promptgpt:audit_logs", 0, 999)
            return
        except Exception as e:
            logger.error(f"Error en Redis add_audit_log: {str(e)}. Usando fallback.")
    audit_logs_db.append(log)

async def get_audit_logs_by_user(user_id: int) -> List[dict]:
    client = get_redis_client()
    if client:
        try:
            logs_str_list = await client.lrange("promptgpt:audit_logs", 0, -1)
            logs = [deserialize_json(log_str) for log_str in logs_str_list]
            return [l for l in logs if l["user_id"] == user_id]
        except Exception as e:
            logger.error(f"Error en Redis get_audit_logs_by_user: {str(e)}. Usando fallback.")
    return [l for l in audit_logs_db if l["user_id"] == user_id]

# --- Async Webhook Delivery Function ---

async def deliver_webhook_async(attempt_id: str, url: str, payload: dict):
    """
    Envia la peticion POST del webhook de forma asincrona y registra el resultado.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            status_code = response.status_code
            response_body = response.text
            success = 200 <= status_code < 300
    except Exception as e:
        status_code = None
        response_body = f"Connection error: {str(e)}"
        success = False
        
    await update_webhook_attempt(attempt_id, status_code, response_body, success)
