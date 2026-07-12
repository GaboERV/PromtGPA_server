from typing import Protocol, List
from ..entities.archivo import ArchivoResumen
from ..entities.chat import ChatResumen
from ..entities.resumen import Resumen

class LectorContenido(Protocol):
    """
    Interfaz de lectura para el cuaderno.
    Exhibe capacidades restringidas de solo lectura.
    """
    async def listar_archivos(self) -> List[ArchivoResumen]: ...
    async def listar_chats(self, usuario_id: int) -> List[ChatResumen]: ...
    async def listar_resumenes(self) -> List[Resumen]: ...
    async def obtener_texto_completo(self) -> str: ...
