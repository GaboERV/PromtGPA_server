from typing import Protocol, List
from ..entities.archivo import ArchivoResumen
from ..entities.chat import ChatResumen

class LectorContenido(Protocol):
    """
    Interfaz de lectura para el cuaderno.
    Exhibe capacidades restringidas de solo lectura.
    """
    async def listar_archivos(self) -> List[ArchivoResumen]: ...
    async def listar_chats(self) -> List[ChatResumen]: ...
    async def obtener_texto_completo(self) -> str: ...
