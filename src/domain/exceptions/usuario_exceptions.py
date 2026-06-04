from .base import BaseError

class UsuarioNoEncontradoError(BaseError):
    def __init__(self):
        self.mensaje = "Usuario no encontrado"
        super().__init__(self.mensaje)

class CredencialesInvalidasError(BaseError):
    def __init__(self):
        self.mensaje = "Credenciales inválidas"
        super().__init__(self.mensaje)