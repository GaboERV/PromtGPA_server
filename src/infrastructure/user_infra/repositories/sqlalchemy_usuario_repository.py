from datetime import datetime
from typing import Optional

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ....domain.user_context import Usuario, CuadernoResumen, UsuarioRepository
from ..models.user_orm import UserORM
from ...notebook_infra.models.notebook_orm import NotebookORM

class SqlAlchemyUsuarioRepository(UsuarioRepository):
    def __init__(self, session: AsyncSession):
        """
        Inicializa el repositorio SQLAlchemy inyectando la sesión asíncrona de base de datos.
        """
        self.session = session

    def _to_domain(self, user_orm: UserORM) -> Usuario:
        """
        Mapea un modelo físico ORM de base de datos a una entidad del dominio de negocio pura.
        """
        cuadernos = [
            CuadernoResumen(id=nb.id, titulo=nb.title)
            for nb in user_orm.notebooks
        ]
        return Usuario(
            id=user_orm.id,
            full_name=user_orm.full_name,
            email=user_orm.email,
            hashed_password=user_orm.hashed_password,
            is_active=True,
            cuadernos_resumen=cuadernos
        )

    async def get_usuario_by_email(self, email: str) -> Optional[Usuario]:
        """
        Busca un usuario por su correo electrónico. Carga ansiosamente (eager loading)
        sus cuadernos asociados para evitar el problema de N+1 consultas en llamadas posteriores.
        """
        stmt = select(UserORM).where(UserORM.email == email).options(selectinload(UserORM.notebooks))
        result = await self.session.execute(stmt)
        user_orm = result.scalar_one_or_none()
        return self._to_domain(user_orm) if user_orm else None

    async def get_usuario_by_id(self, usuario_id: int) -> Optional[Usuario]:
        """
        Busca un usuario por su ID primario. Carga ansiosamente sus cuadernos asociados.
        """
        stmt = select(UserORM).where(UserORM.id == usuario_id).options(selectinload(UserORM.notebooks))
        result = await self.session.execute(stmt)
        user_orm = result.scalar_one_or_none()
        return self._to_domain(user_orm) if user_orm else None

    async def save_usuario(self, usuario: Usuario) -> None:
        """
        Guarda o actualiza la información del usuario y sincroniza de forma bidireccional
        y en cascada toda su colección de cuadernos asociados.
        """
        user_orm = None
        # 1. Intentar buscar por ID si ya está definido
        if usuario.id is not None:
            stmt = select(UserORM).where(UserORM.id == usuario.id).options(selectinload(UserORM.notebooks))
            result = await self.session.execute(stmt)
            user_orm = result.scalar_one_or_none()

        if user_orm is None:
            # Si no se encuentra por ID, intentar buscar por email para prevenir duplicados
            stmt = select(UserORM).where(UserORM.email == usuario.email).options(selectinload(UserORM.notebooks))
            result = await self.session.execute(stmt)
            user_orm = result.scalar_one_or_none()

        if user_orm is None:
            # Crear un nuevo registro físico de usuario con la relación de notebooks precargada como vacía
            user_orm = UserORM(
                email=usuario.email,
                hashed_password=usuario.hashed_password,
                full_name=usuario.nombre,
                created_at=datetime.now(),
                notebooks=[]
            )
            self.session.add(user_orm)
            # Flush asíncrono para generar la PK autoincremental de base de datos
            await self.session.flush()
            usuario.id = user_orm.id  # Sincronizar el ID de la base de datos de vuelta al dominio
        else:
            # Actualizar campos básicos del usuario existente
            user_orm.email = usuario.email
            user_orm.hashed_password = usuario.hashed_password
            user_orm.full_name = usuario.nombre

        # 2. Sincronizar en cascada la colección de cuadernos de notas
        # Crear un diccionario para identificar rápidamente qué cuadernos persisten del dominio
        domain_notebooks_dict = {c.id: c for c in usuario.cuadernos_resumen if c.id is not None}

        # Remover del ORM los que ya no están en la lista del dominio.
        # Gracias a cascade="all, delete-orphan", SQLAlchemy los borrará físicamente del SQLite
        user_orm.notebooks = [nb for nb in user_orm.notebooks if nb.id in domain_notebooks_dict]

        # Actualizar cuadernos existentes y agregar los nuevos
        existing_notebooks_dict = {nb.id: nb for nb in user_orm.notebooks}
        for cuaderno in usuario.cuadernos_resumen:
            if cuaderno.id in existing_notebooks_dict:
                # Ya existe en DB: actualizar el título
                existing_notebooks_dict[cuaderno.id].title = cuaderno.titulo
            else:
                # Es un cuaderno nuevo creado en el dominio: instanciar en ORM y asociar
                new_notebook_orm = NotebookORM(
                    title=cuaderno.titulo,
                    usuario_id=user_orm.id
                )
                # Opcional: si el dominio definió un ID manual, preservarlo
                if cuaderno.id is not None:
                    new_notebook_orm.id = cuaderno.id
                user_orm.notebooks.append(new_notebook_orm)

    async def delete_usuario(self, usuario_id: int) -> None:
        """
        Elimina físicamente a un usuario de la base de datos por su ID de forma directa.
        Los cuadernos asociados se borran automáticamente en cascada.
        """
        stmt = select(UserORM).where(UserORM.id == usuario_id)
        result = await self.session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        if user_orm:
            await self.session.delete(user_orm)
