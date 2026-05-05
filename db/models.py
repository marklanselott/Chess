from sqlalchemy import Column, String, Boolean, ForeignKey, UUID, Integer, Enum as SQLEnum
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
    WaitingOpponent = "waiting_opponent"
    Searching = "searching"
    InGame = "in_game"

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
    status = Column(SQLEnum(GameSessionStatus), default=GameSessionStatus.Searching)
    oponent = Column(UUID, ForeignKey("users.id"), nullable=True)

# class GameSession(Base):
#     __tablename__ = "game_sessions"

#     id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
#     user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
#     status = Column(SQLEnum(GameSessionStatus), default=GameSessionStatus.WaitingOpponent)
#     created_at = Column(Integer, nullable=False, default=int(datetime.utcnow().timestamp()))

# class GameHistory(Base):
#     __tablename__ = "games"

#     id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
#     winner_id = Column(UUID, ForeignKey("users.id"), nullable=True)
#     num_of_moves = Column(Integer, nullable=False)




# class Session(Base):
#     __tablename__ = "sessions"

#     id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
#     user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
#     created_at = Column(Integer, nullable=False, default=datetime.utcnow().timestamp())

