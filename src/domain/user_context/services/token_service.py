import asyncio
from typing import Protocol
from ..usuario import Usuario

class TokenService(Protocol):
    async def generate_token(self, usuario: Usuario) -> str: ...
    async def validate_token(self, token: str) -> bool: ...