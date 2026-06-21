from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ....domain.assessment_context.interfaces.examen_repository import ExamenRepository
from ....domain.assessment_context.entities.examen import Examen, PreguntaExamen, IntentoExamen, RespuestaUsuario
from ..models.assessment_orm import ExamenORM, PreguntaExamenORM, IntentoExamenORM, RespuestaUsuarioORM

class SqlAlchemyExamenRepository(ExamenRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain_examen(self, orm: ExamenORM) -> Examen:
        preguntas = [
            PreguntaExamen(p.id, p.examen_id, p.question_text, p.opciones, p.correct_answer)
            for p in orm.preguntas
        ]
        return Examen(
            id=orm.id,
            title=orm.title,
            notebook_id=orm.notebook_id,
            sala_id=orm.sala_id,
            created_at=orm.created_at,
            preguntas=preguntas
        )

    def _to_domain_intento(self, orm: IntentoExamenORM) -> IntentoExamen:
        respuestas = [
            RespuestaUsuario(r.id, r.intento_id, r.pregunta_id, r.user_answer, r.is_correct)
            for r in orm.respuestas
        ]
        return IntentoExamen(
            id=orm.id,
            examen_id=orm.examen_id,
            usuario_id=orm.usuario_id,
            participante_sala_id=orm.participante_sala_id,
            score=float(orm.score),
            completed_at=orm.completed_at,
            respuestas=respuestas
        )

    async def get_examen_by_id(self, examen_id: int) -> Optional[Examen]:
        stmt = select(ExamenORM).where(ExamenORM.id == examen_id).options(selectinload(ExamenORM.preguntas))
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain_examen(orm) if orm else None

    async def list_examenes_by_notebook_id(self, notebook_id: int) -> List[Examen]:
        stmt = select(ExamenORM).where(ExamenORM.notebook_id == notebook_id).options(selectinload(ExamenORM.preguntas))
        result = await self.session.execute(stmt)
        return [self._to_domain_examen(orm) for orm in result.scalars().all()]

    async def list_examenes_by_sala_id(self, sala_id: int) -> List[Examen]:
        stmt = select(ExamenORM).where(ExamenORM.sala_id == sala_id).options(selectinload(ExamenORM.preguntas))
        result = await self.session.execute(stmt)
        return [self._to_domain_examen(orm) for orm in result.scalars().all()]

    async def save_examen(self, examen: Examen) -> None:
        orm = ExamenORM(
            title=examen.title,
            notebook_id=examen.notebook_id,
            sala_id=examen.sala_id,
            created_at=examen.created_at
        )
        self.session.add(orm)
        await self.session.flush()
        examen.id = orm.id

        for p in examen.preguntas:
            p_orm = PreguntaExamenORM(
                examen_id=examen.id,
                question_text=p.question_text,
                opciones=p.opciones,
                correct_answer=p.correct_answer
            )
            self.session.add(p_orm)
            await self.session.flush()
            p.id = p_orm.id
            p.examen_id = examen.id

    async def delete_examen(self, examen_id: int) -> None:
        stmt = select(ExamenORM).where(ExamenORM.id == examen_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)

    # --- Intentos de Exámenes ---
    async def get_intento_by_id(self, intento_id: int) -> Optional[IntentoExamen]:
        stmt = select(IntentoExamenORM).where(IntentoExamenORM.id == intento_id).options(selectinload(IntentoExamenORM.respuestas))
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain_intento(orm) if orm else None

    async def list_intentos_by_usuario_id(self, usuario_id: int) -> List[IntentoExamen]:
        stmt = select(IntentoExamenORM).where(IntentoExamenORM.usuario_id == usuario_id).options(selectinload(IntentoExamenORM.respuestas))
        result = await self.session.execute(stmt)
        return [self._to_domain_intento(orm) for orm in result.scalars().all()]

    async def list_intentos_by_examen_id(self, examen_id: int) -> List[IntentoExamen]:
        stmt = select(IntentoExamenORM).where(IntentoExamenORM.examen_id == examen_id).options(selectinload(IntentoExamenORM.respuestas))
        result = await self.session.execute(stmt)
        return [self._to_domain_intento(orm) for orm in result.scalars().all()]

    async def save_intento(self, intento: IntentoExamen) -> None:
        orm = IntentoExamenORM(
            examen_id=intento.examen_id,
            usuario_id=intento.usuario_id,
            participante_sala_id=intento.participante_sala_id,
            score=intento.score,
            completed_at=intento.completed_at
        )
        self.session.add(orm)
        await self.session.flush()
        intento.id = orm.id

        for r in intento.respuestas:
            r_orm = RespuestaUsuarioORM(
                intento_id=intento.id,
                pregunta_id=r.pregunta_id,
                user_answer=r.user_answer,
                is_correct=r.is_correct
            )
            self.session.add(r_orm)
            await self.session.flush()
            r.id = r_orm.id
            r.intento_id = intento.id
