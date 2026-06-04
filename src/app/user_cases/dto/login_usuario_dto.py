from pydantic import BaseModel, EmailStr

class LoginDTO(BaseModel):
    password:str
    email: EmailStr
