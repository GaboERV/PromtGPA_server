from .repositories.cuaderno_resumen import CuadernoResumen
from typing import List

class Usuario:
    def __init__(self, id: int, full_name: str, email: str, hashed_password: str, is_active: bool, cuadernos_resumen: List[CuadernoResumen]):
        self.id = id
        self.nombre = full_name
        self.email = email
        self.hashed_password = hashed_password
        self.is_active = is_active
        self.cuadernos_resumen: List[CuadernoResumen] = cuadernos_resumen or []
    def __str__(self):
        return f"Usuario(id={self.id}, nombre='{self.nombre}', email='{self.email}')"
    
    def comprobar_contrasenia(self, contrasenia:str)->bool:
        es_valida = self.hashed_password == contrasenia
        return es_valida
    
    def agregar_cuaderno(self, cuaderno: CuadernoResumen) -> None:
        self.cuadernos_resumen.append(cuaderno)
        return None
    