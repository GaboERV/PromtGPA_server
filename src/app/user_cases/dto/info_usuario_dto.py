from pydantic import  BaseModel,EmailStr

class InfoUsuarioDTO(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    is_active: bool