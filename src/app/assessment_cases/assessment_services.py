from datetime import datetime
from typing import List, Dict, Optional

from ...domain.exceptions import (
    ExamenNoEncontradoError,
    IntentoNoEncontradoError,
    CuadernoNoEncontradoError
)
from ...domain.assessment_context.entities.examen import (
    Examen,
    PreguntaExamen,
    IntentoExamen,
    RespuestaUsuario
)
from ...domain.assessment_context.services.rag_engine_service import RAGEngineService
from ...domain.assessment_context.interfaces.examen_repository import ExamenRepository
from ...domain.notebook_context.interfaces.cuaderno_repository import CuadernoRepository
from ...domain.notebook_context.entities.flashcard import Flashcard


class AssessmentService:
    def __init__(
        self,
        examen_repository: ExamenRepository,
        cuaderno_repository: CuadernoRepository,
        rag_engine: RAGEngineService
    ):
        self.examen_repository = examen_repository
        self.cuaderno_repository = cuaderno_repository
        self.rag_engine = rag_engine

    async def _validar_propietario_cuaderno(self, notebook_id: int, user_id: int):
        cuaderno = await self.cuaderno_repository.get_by_id(notebook_id)
        if not cuaderno:
            raise CuadernoNoEncontradoError()
        from ...domain.exceptions import PermisoDenegadoError
        if cuaderno.user_id != user_id:
            raise PermisoDenegadoError()

    async def _obtener_texto_completo_cuaderno(self, notebook_id: int, user_id: int, archivo_ids: Optional[List[int]] = None) -> str:
        await self._validar_propietario_cuaderno(notebook_id, user_id)
        archivos = await self.cuaderno_repository.list_archivos_by_notebook_id(notebook_id)
        if archivo_ids:
            archivos = [f for f in archivos if f.id in archivo_ids]
            # Validamos si encontramos todos los archivos especificados
            if len(archivos) != len(set(archivo_ids)):
                raise CuadernoNoEncontradoError()
        return "\n\n".join([f.content for f in archivos if f.content])

    # --- Flashcards ---
    async def generar_flashcards(
        self, notebook_id: int, user_id: int, prompt: str, cantidad: int = 5, archivo_ids: Optional[List[int]] = None
    ) -> List[Flashcard]:
        texto_crudo = await self._obtener_texto_completo_cuaderno(notebook_id, user_id, archivo_ids)
        flashcards = await self.rag_engine.generar_flashcards_por_contexto(
            prompt=prompt,
            archivo_ids=archivo_ids,
            texto_crudo=texto_crudo,
            cantidad=cantidad
        )

        for fc in flashcards:
            fc.notebook_id = notebook_id
            fc.created_at = datetime.utcnow()
            await self.cuaderno_repository.save_flashcard(fc)

        return flashcards

    async def listar_flashcards(self, notebook_id: int, user_id: int) -> List[Flashcard]:
        await self._validar_propietario_cuaderno(notebook_id, user_id)
        return await self.cuaderno_repository.list_flashcards_by_notebook_id(notebook_id)

    # --- Exámenes ---
    async def generar_examen(
        self, notebook_id: int, user_id: int, prompt: str, sala_id: Optional[int] = None, archivo_ids: Optional[List[int]] = None
    ) -> Examen:
        texto_crudo = await self._obtener_texto_completo_cuaderno(notebook_id, user_id, archivo_ids)
        examen = await self.rag_engine.generar_examen_por_contexto(
            prompt=prompt,
            archivo_ids=archivo_ids,
            texto_crudo=texto_crudo
        )

        examen.notebook_id = notebook_id
        examen.sala_id = sala_id
        examen.created_at = datetime.utcnow()

        await self.examen_repository.save_examen(examen)
        return examen

    async def obtener_examen(self, examen_id: int, user_id: int) -> Examen:
        examen = await self.examen_repository.get_examen_by_id(examen_id)
        if not examen:
            raise ExamenNoEncontradoError()
        # Validación de propiedad
        await self._validar_propietario_cuaderno(examen.notebook_id, user_id)
        return examen

    async def listar_examenes_por_cuaderno(self, notebook_id: int, user_id: int) -> List[Examen]:
        await self._validar_propietario_cuaderno(notebook_id, user_id)
        return await self.examen_repository.list_examenes_by_notebook_id(notebook_id)

    async def listar_examenes_por_sala(self, sala_id: int) -> List[Examen]:
        return await self.examen_repository.list_examenes_by_sala_id(sala_id)

    # --- Resolver Examen (Calificación Individual Privada) ---
    async def resolver_examen(
        self,
        examen_id: int,
        usuario_id: int,
        respuestas_usuario: Dict[int, str],  # Mapea pregunta_id -> respuesta seleccionada ('A', 'B', etc.)
        participante_sala_id: Optional[int] = None
    ) -> IntentoExamen:
        examen = await self.examen_repository.get_examen_by_id(examen_id)
        if not examen:
            raise ExamenNoEncontradoError()

        if not examen.preguntas:
            # Examen sin preguntas
            intento = IntentoExamen(
                id=None,
                examen_id=examen_id,
                usuario_id=usuario_id,
                participante_sala_id=participante_sala_id,
                score=0.0,
                completed_at=datetime.utcnow(),
                respuestas=[]
            )
            await self.examen_repository.save_intento(intento)
            return intento

        respuestas_list = []
        aciertos = 0

        for pregunta in examen.preguntas:
            user_ans = respuestas_usuario.get(pregunta.id, "").strip().upper()
            is_correct = (user_ans == pregunta.correct_answer.strip().upper())
            if is_correct:
                aciertos += 1

            respuestas_list.append(
                RespuestaUsuario(
                    id=None,
                    intento_id=None,
                    pregunta_id=pregunta.id,
                    user_answer=user_ans,
                    is_correct=is_correct
                )
            )

        score = (aciertos / len(examen.preguntas)) * 100.0

        intento = IntentoExamen(
            id=None,
            examen_id=examen_id,
            usuario_id=usuario_id,
            participante_sala_id=participante_sala_id,
            score=round(score, 2),
            completed_at=datetime.utcnow(),
            respuestas=respuestas_list
        )

        await self.examen_repository.save_intento(intento)
        return intento

    async def obtener_intento(self, intento_id: int) -> IntentoExamen:
        intento = await self.examen_repository.get_intento_by_id(intento_id)
        if not intento:
            raise IntentoNoEncontradoError()
        return intento

    async def listar_intentos_usuario(self, usuario_id: int) -> List[IntentoExamen]:
        return await self.examen_repository.list_intentos_by_usuario_id(usuario_id)

    async def listar_intentos_examen(self, examen_id: int) -> List[IntentoExamen]:
        return await self.examen_repository.list_intentos_by_examen_id(examen_id)
