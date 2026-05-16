from sqlalchemy import Column, String, Boolean, ForeignKey, UUID, Integer, Enum as SQLEnum, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from datetime import datetime
from .database import Base
from enum import Enum
import uuid

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class UserColor(str, Enum):
    WHITE = "white"
    BLACK = "black"

class GameSessionStatus(str, Enum):
    Searching = "searching"
    InGame = "in_game"

async def get_user(session: AsyncSession, user_id: str):
    user = await session.execute(select(User).where(User.id == user_id))
    if user: return user.scalars().first()
    else: raise HTTPException(status_code=404, detail="User not found")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    unique = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    password = Column(String, nullable=False)
    phone = Column(Integer, nullable=True)
    email = Column(String, nullable=True)
    tg_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    rating = Column(Integer, default=400)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    registryed_at = Column(Integer, nullable=False, default=int(datetime.utcnow().timestamp()))

class Friendship(Base):
    __tablename__ = "friends"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    friend_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    status = Column(Boolean, default=False)
    created_at = Column(Integer, nullable=False, default=int(datetime.utcnow().timestamp()))

class OpponentSearch(Base):
    __tablename__ = "opponent_search"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    status = Column(SQLEnum(GameSessionStatus), default=GameSessionStatus.Searching)
    game_id = Column(UUID, nullable=True)

class Games(Base):
    __tablename__ = "games"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    white_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    black_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    result = Column(String, nullable=True)
    result_reason = Column(String, nullable=True)
    winner_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    loser_id = Column(UUID, ForeignKey("users.id"), nullable=True)
    finished_at = Column(Integer, nullable=True)


class GameMove(Base):
    __tablename__ = "game_moves"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    game_id = Column(UUID, ForeignKey("games.id"), nullable=False)
    fen = Column(String, nullable=False)
    step = Column(Integer, nullable=False)

# class Session(Base):
#     __tablename__ = "sessions"

#     id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
#     user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
#     created_at = Column(Integer, nullable=False, default=datetime.utcnow().timestamp())

