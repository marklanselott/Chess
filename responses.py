from pydantic import BaseModel
from datetime import datetime

class CreateToken(BaseModel):
    jwt: str
    exp: int

class User(BaseModel):
    unique: str
    first_name: str  | None
    middle_name: str | None
    last_name: str   | None
    phone: int       | None
    email: str       | None
    registryed_at: datetime

class SearchUser(BaseModel):
    searched: list[User]
    start: int
    limit: int

