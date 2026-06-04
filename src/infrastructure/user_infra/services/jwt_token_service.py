import os
from datetime import datetime, timedelta, timezone
import jwt
from ....domain.user_context import TokenService, Usuario

class JwtTokenService(TokenService):
    def __init__(self):
        # Configuraciones leídas de variables de entorno con fallbacks seguros para desarrollo
        self.secret_key = os.getenv("JWT_SECRET_KEY", "prod-security-fallback-must-be-replaced-via-env")
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    async def generate_token(self, usuario: Usuario) -> str:
        """
        Genera un token JWT firmado digitalmente conteniendo el payload estándar del usuario
        y fijando una fecha de expiración y de emisión.
        """
        payload = {
            "sub": str(usuario.id),  # Identificador principal (id entero del usuario)
            "email": usuario.email,
            "nombre": usuario.nombre,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes),
            "iat": datetime.now(timezone.utc)
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    async def validate_token(self, token: str) -> bool:
        """
        Valida que el token JWT sea auténtico, que no haya sido alterado
        y que no haya expirado. Retorna True si es válido, de lo contrario False.
        """
        try:
            # decode verifica la expiración (exp) e iat de forma automática
            jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return True
        except jwt.PyJWTError:
            return False
