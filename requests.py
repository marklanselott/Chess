from pydantic import BaseModel

class Login(BaseModel):
    unique: str
    password: str

class SearchUser(BaseModel):
    unique: str      | None = None
    first_name: str  | None = None
    middle_name: str | None = None
    last_name: str   | None = None
    phone: int       | None = None
    email: str       | None = None
    tg_id: int       | None = None
    start: int       | None = 0

class CreateUser(BaseModel):
    unique: str
    first_name: str
    middle_name: str | None = None
    last_name: str   | None = None
    password: str
    phone: int       | None = None
    email: str       | None = None
    tg_id: int       | None = None

class UpdateUser(BaseModel):
    unique: str      | None = None
    first_name: str  | None = None
    middle_name: str | None = None
    last_name: str   | None = None
    password: str    | None = None
    phone: int       | None = None
    email: str       | None = None