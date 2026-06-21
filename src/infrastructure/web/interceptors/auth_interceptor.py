from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import os

from ...web.dependencies import get_user_service
from ....app.user_cases.user_services import UserService
from ....domain.exceptions import TokenInvalidoError
from ...core.memory_state import check_and_use_jti, add_audit_log

security_bearer = HTTPBearer(auto_error=False)

async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    user_service: UserService = Depends(get_user_service)
) -> int:
    """
    Interceptor de autenticación. Admite tanto un Bearer token estándar
    como una cabecera 'X-API-Key' de un solo uso.
    
    Lanza una excepción HTTP 401 si las credenciales son inválidas, han expirado
    o si la API Key de un solo uso ya fue consumida.
    """
    if credentials:
        token = credentials.credentials
        try:
            user_id = await user_service.validate_and_get_user_id(token)
            return user_id
        except TokenInvalidoError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.mensaje,
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
            
    elif x_api_key:
        secret_key = os.getenv("JWT_SECRET_KEY", "prod-security-fallback-must-be-replaced-via-env")
        algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        try:
            payload = jwt.decode(x_api_key, secret_key, algorithms=[algorithm])
            jti = payload.get("jti")
            user_id = payload.get("sub")
            if not jti or not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API Key inválida: Claims incompletos."
                )
            # Verificar reuso de la llave mediante el helper asíncrono
            success = await check_and_use_jti(jti)
            if not success:
                from datetime import datetime
                import uuid
                await add_audit_log({
                    "id": str(uuid.uuid4()),
                    "user_id": int(user_id),
                    "action": f"SUSPICIOUS_API_KEY_REUSE: {jti}",
                    "timestamp": datetime.utcnow(),
                    "ip": "127.0.0.1"
                })
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API Key ya consumida (llave de un solo uso)."
                )
            return int(user_id)
        except jwt.PyJWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key inválida o expirada."
            ) from e
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de acceso requeridas (Bearer token o X-API-Key).",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id_bearer_only(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    user_service: UserService = Depends(get_user_service)
) -> int:
    """
    Exige estrictamente un token Bearer de sesión. No admite X-API-Key.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial Bearer token requerida.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        user_id = await user_service.validate_and_get_user_id(token)
        return user_id
    except TokenInvalidoError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.mensaje,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_id_with_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    user_service: UserService = Depends(get_user_service)
) -> int:
    """
    Exige tanto el Bearer token (predeterminado) como la cabecera 'X-API-Key'
    (de un solo uso) para acceder a un recurso sensible y evitar inyección masiva.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere el token Bearer predeterminado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere la cabecera 'X-API-Key' de un solo uso para acceder a este recurso.",
        )

    # 1. Validar Bearer token
    token = credentials.credentials
    try:
        user_id_bearer = await user_service.validate_and_get_user_id(token)
    except TokenInvalidoError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.mensaje,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # 2. Validar X-API-Key (de un solo uso)
    secret_key = os.getenv("JWT_SECRET_KEY", "prod-security-fallback-must-be-replaced-via-env")
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(x_api_key, secret_key, algorithms=[algorithm])
        jti = payload.get("jti")
        user_id_key = payload.get("sub")
        if not jti or not user_id_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key inválida: Claims incompletos."
            )
        
        if int(user_id_key) != user_id_bearer:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="La API Key no pertenece al usuario autenticado."
            )

        # Verificar reuso de la llave mediante el helper asíncrono
        success = await check_and_use_jti(jti)
        if not success:
            from datetime import datetime
            import uuid
            await add_audit_log({
                "id": str(uuid.uuid4()),
                "user_id": int(user_id_key),
                "action": f"SUSPICIOUS_API_KEY_REUSE: {jti}",
                "timestamp": datetime.utcnow(),
                "ip": "127.0.0.1"
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key ya consumida (llave de un solo uso)."
            )
            
        return user_id_bearer
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o expirada."
        ) from e
