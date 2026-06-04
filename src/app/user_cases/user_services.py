from ...domain.user_context import Usuario, UsuarioRepository, EncryptService, TokenService
from ...domain.exceptions import UsuarioNoEncontradoError, CredencialesInvalidasError
from .dto import CreateUsuarioDTO, LoginDTO, InfoUsuarioDTO

class UserService:
    def __init__(self, usuario_repository: UsuarioRepository, encrypt_service: EncryptService, token_service: TokenService):
        self.usuario_repository = usuario_repository
        self.encrypt_service = encrypt_service
        self.token_service = token_service

    async def register_usuario(self, create_usuario_dto: CreateUsuarioDTO) -> None:
        """
        Registra un nuevo usuario encriptando su contraseña asíncronamente.
        """
        hash_password = await self.encrypt_service.hash_password(create_usuario_dto.password)
        usuario = Usuario(
            id=None,
            full_name=create_usuario_dto.nombre,
            email=create_usuario_dto.email,
            hashed_password=hash_password,
            is_active=True,
            cuadernos_resumen=[]
        )
        await self.usuario_repository.save_usuario(usuario)
        return None

    async def login_usuario(self, login_dto: LoginDTO) -> str:
        """
        Valida las credenciales del usuario y retorna un token JWT firmado de forma asíncrona.
        Lanza excepciones de dominio en caso de fallos.
        """
        usuario = await self.usuario_repository.get_usuario_by_email(login_dto.email)
        if usuario is None:
            raise UsuarioNoEncontradoError()
        
        # Validar contraseña usando el servicio de encriptación asíncrono (soporte para bcrypt)
        es_valida = await self.encrypt_service.compare_password(login_dto.password, usuario.hashed_password)
        if not es_valida:
            raise CredencialesInvalidasError()
    
        token = await self.token_service.generate_token(usuario)
        return token

    async def get_usuario_info(self, usuario_id: int) -> InfoUsuarioDTO:
        """
        Recupera información básica del usuario. Lanza UsuarioNoEncontradoError si no existe.
        """
        usuario = await self.usuario_repository.get_usuario_by_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontradoError()
        
        return InfoUsuarioDTO(
            id=usuario.id,
            nombre=usuario.nombre,
            email=usuario.email,
            activo=usuario.is_active
        )

    async def delete_usuario(self, email: str, contrasenia: str) -> None:
        """
        Valida la identidad del usuario y luego ordena su eliminación física de base de datos.
        """
        # 1. Recuperar el usuario
        usuario = await self.usuario_repository.get_usuario_by_email(email)
        if usuario is None:
            raise UsuarioNoEncontradoError()

        # 2. Validar contraseña
        es_valida = await self.encrypt_service.compare_password(contrasenia, usuario.hashed_password)
        if not es_valida:
            raise CredencialesInvalidasError()

        # 3. Eliminar por ID
        await self.usuario_repository.delete_usuario(usuario.id)
        return None