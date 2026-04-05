from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class CreateToken(BaseModel):
    jwt: str
    exp: int

class CreateFriendRequest(BaseModel):
    id: UUID
    user_id: UUID
    friend_id: UUID
    status: bool

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

class SearchUser(BaseModel):
    searched: list[User]
    start: int
    limit: int

