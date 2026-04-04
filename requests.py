from pydantic import BaseModel

class Login(BaseModel):
    unique: str
    password: str

class CreateUser(BaseModel):
    unique: str
    first_name: str
    middle_name: str | None = None
    last_name: str   | None = None
    password: str
    phone: int       | None = None
    email: str       | None = None