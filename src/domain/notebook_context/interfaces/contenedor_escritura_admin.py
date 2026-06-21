from typing import Protocol
from ..entities.archivo import Archivo

class ContenedorEscrituraAdmin(Protocol):
    """
    Interfaz de escritura administrativa para el cuaderno.
    Exclusiva del propietario o creador de la sala.
    """
    async def agregar_archivo(self, filename: str, content: str, file_type: str) -> Archivo: ...
    async def eliminar_archivo(self, archivo_id: int) -> None: ...
