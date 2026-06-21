from fastapi import APIRouter, Depends, status
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
    user_service: UserService = Depends(get_user_service)
):
    """
    Endpoint para la autenticación de usuarios. Retorna un token JWT Bearer.
    """
    token = await user_service.login_usuario(dto)
    return {"access_token": token, "token_type": "bearer"}

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
