import asyncio
import bcrypt
from ....domain.user_context import EncryptService

class BcryptEncryptService(EncryptService):
    async def hash_password(self, password: str) -> str:
        """
        Hashea una contraseña de texto plano de manera segura con salting de Bcrypt.
        Esta operación es costosa en CPU, por lo que se ejecuta en un hilo del pool de hilos
        para evitar bloquear el event loop asíncrono principal.
        """
        hashed = await asyncio.to_thread(
            bcrypt.hashpw,
            password.encode("utf-8"),
            bcrypt.gensalt()
        )
        return hashed.decode("utf-8")

    async def compare_password(self, password: str, hashed_password: str) -> bool:
        """
        Compara una contraseña de texto plano contra un hash para verificar si coincide.
        Al igual que el hashing, se ejecuta en un hilo del pool de hilos de forma asíncrona.
        """
        is_valid = await asyncio.to_thread(
            bcrypt.checkpw,
            password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
        return is_valid
