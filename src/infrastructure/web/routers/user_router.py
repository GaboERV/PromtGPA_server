from fastapi import APIRouter, Depends, Response, status
from ...web.dependencies import get_user_service
from ....app.user_cases.user_services import UserService
from ....app.user_cases.dto import CreateUsuarioDTO, LoginDTO, InfoUsuarioDTO
from ..interceptors.auth_interceptor import get_current_user_id

router = APIRouter(prefix="/users", tags=["Usuarios"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    dto: CreateUsuarioDTO,
    user_service: UserService = Depends(get_user_service)
):
    """
    Endpoint para el registro de nuevos usuarios.
    """
    await user_service.register_usuario(dto)
    return {"message": "Usuario registrado exitosamente"}

@router.post("/login", status_code=status.HTTP_200_OK)
async def login(
    dto: LoginDTO,
    response: Response,
    user_service: UserService = Depends(get_user_service)
):
    """
    Endpoint para la autenticación de usuarios.
    Retorna el JWT en el body JSON **y** lo inyecta como cookie HttpOnly
    (`access_token`) para soportar flujos cross-origin desde el frontend.
    """
    token = await user_service.login_usuario(dto)

    # Inyectar cookie segura para clientes web cross-origin
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,             # Inaccesible a JavaScript (mitigación XSS)
        secure=True,               # Solo se envía por HTTPS
        samesite="none",           # Necesario para cross-origin
        max_age=30 * 24 * 3600,   # 30 días
        path="/",
    )
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    """
    Invalida la cookie de sesión del cliente. Para invalidar el token
    en servidor use la rotación de contraseña o la revocación por JTI.
    """
    response.delete_cookie(key="access_token", path="/", samesite="none", secure=True)
    return {"message": "Sesión cerrada exitosamente"}

@router.get("/me", response_model=InfoUsuarioDTO, status_code=status.HTTP_200_OK)
async def get_profile(
    current_user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """
    Endpoint para obtener la información de perfil del usuario autenticado (Protegido).
    """
    info = await user_service.get_usuario_info(current_user_id)
    return info

@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_account(
    dto: LoginDTO,  # Por seguridad se solicita confirmación de email y password
    current_user_id: int = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
):
    """
    Endpoint para eliminar permanentemente la cuenta del usuario autenticado (Protegido).
    """
    await user_service.delete_usuario(dto.email, dto.password)
    return {"message": "Cuenta eliminada exitosamente"}
