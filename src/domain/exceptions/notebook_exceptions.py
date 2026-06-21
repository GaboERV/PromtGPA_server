from .base import BaseError

class CuadernoNoEncontradoError(BaseError):
    def __init__(self):
        self.mensaje = "Cuaderno no encontrado"
        super().__init__(self.mensaje)

class SalaNoEncontradaError(BaseError):
    def __init__(self):
        self.mensaje = "Sala de estudio no encontrada"
        super().__init__(self.mensaje)

class PermisoDenegadoError(BaseError):
    def __init__(self, detalle: str = "No tienes permisos para realizar esta acción"):
        self.mensaje = detalle
        super().__init__(self.mensaje)

class ExamenNoEncontradoError(BaseError):
    def __init__(self):
        self.mensaje = "Examen no encontrado"
        super().__init__(self.mensaje)

class IntentoNoEncontradoError(BaseError):
    def __init__(self):
        self.mensaje = "Intento de examen no encontrado"
        super().__init__(self.mensaje)
