from pydantic import BaseModel,EmailStr

class UpdateNombreDTO(BaseModel):
    id: int
    name: str | None

class UpdateEmailDTO(BaseModel):
    id:int
    email: EmailStr | None
    password: str

class UpdatePasswordDTO(BaseModel):
    id:int
    password: str
    new_password: str