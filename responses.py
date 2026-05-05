from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class CreateToken(BaseModel):
    jwt: str
    exp: int

class User(BaseModel):
    id: UUID
    unique: str
    first_name: str  | None
    middle_name: str | None
    last_name: str   | None
    phone: int       | None
    email: str       | None
    tg_id: int       | None
    rating: int
    registryed_at: datetime

class FriendRequest(BaseModel):
    id: UUID
    user: User
    friend: User
    status: bool

class SearchUser(BaseModel):
    searched: list[User]
    start: int
    limit: int

class StartOpponentSearch(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    oponent: UUID | None = None

