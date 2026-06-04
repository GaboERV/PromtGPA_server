from pydantic import BaseModel, EmailStr

class CreateUsuarioDTO(BaseModel):
    id: int | None = None
    nombre: str
    email: EmailStr
    password: str