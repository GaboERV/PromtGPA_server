from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ....domain.study_room_context.interfaces.sala_estudio_repository import SalaEstudioRepository
from ....domain.study_room_context.entities.sala_estudio import SalaEstudio, ParticipanteSala
from ..models.study_room_orm import SalaEstudioORM, ParticipanteSalaORM

class SqlAlchemySalaRepository(SalaEstudioRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, orm: SalaEstudioORM) -> SalaEstudio:
        return SalaEstudio(
            id=orm.id,
            title=orm.title,
            codigo=orm.codigo,
            notebook_id=orm.notebook_id,
            creado_por_id=orm.creado_por_id,
            created_at=orm.created_at
        )

    async def get_by_id(self, sala_id: int) -> Optional[SalaEstudio]:
        stmt = select(SalaEstudioORM).where(SalaEstudioORM.id == sala_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_codigo(self, codigo: str) -> Optional[SalaEstudio]:
        stmt = select(SalaEstudioORM).where(SalaEstudioORM.codigo == codigo)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_usuario_id(self, usuario_id: int) -> List[SalaEstudio]:
        stmt = select(SalaEstudioORM).where(SalaEstudioORM.creado_por_id == usuario_id)
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def list_by_participante_id(self, usuario_id: int) -> List[SalaEstudio]:
        stmt = (
            select(SalaEstudioORM)
            .join(ParticipanteSalaORM, SalaEstudioORM.id == ParticipanteSalaORM.sala_id)
            .where(ParticipanteSalaORM.usuario_id == usuario_id)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def save(self, sala: SalaEstudio) -> None:
        orm = None
        if sala.id is not None:
            stmt = select(SalaEstudioORM).where(SalaEstudioORM.id == sala.id)
            result = await self.session.execute(stmt)
            orm = result.scalar_one_or_none()

        if orm is None:
            orm = SalaEstudioORM(
                title=sala.title,
                codigo=sala.codigo,
                notebook_id=sala.notebook_id,
                creado_por_id=sala.creado_por_id,
                created_at=sala.created_at
            )
            self.session.add(orm)
            await self.session.flush()
            sala.id = orm.id
        else:
            orm.title = sala.title

    async def delete(self, sala_id: int) -> None:
        stmt = select(SalaEstudioORM).where(SalaEstudioORM.id == sala_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)

    # --- Participantes ---
    async def get_participante(self, sala_id: int, usuario_id: int) -> Optional[ParticipanteSala]:
        stmt = select(ParticipanteSalaORM).where(
            ParticipanteSalaORM.sala_id == sala_id,
            ParticipanteSalaORM.usuario_id == usuario_id
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return ParticipanteSala(orm.id, orm.sala_id, orm.usuario_id) if orm else None

    async def save_participante(self, participante: ParticipanteSala) -> None:
        orm = ParticipanteSalaORM(
            sala_id=participante.sala_id,
            usuario_id=participante.usuario_id
        )
        self.session.add(orm)
        await self.session.flush()
        participante.id = orm.id

    async def delete_participante(self, sala_id: int, usuario_id: int) -> None:
        stmt = select(ParticipanteSalaORM).where(
            ParticipanteSalaORM.sala_id == sala_id,
            ParticipanteSalaORM.usuario_id == usuario_id
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)

    async def list_participantes(self, sala_id: int) -> List[ParticipanteSala]:
        stmt = select(ParticipanteSalaORM).where(ParticipanteSalaORM.sala_id == sala_id)
        result = await self.session.execute(stmt)
        return [
            ParticipanteSala(p.id, p.sala_id, p.usuario_id)
            for p in result.scalars().all()
        ]
