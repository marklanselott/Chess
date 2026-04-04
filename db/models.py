from sqlalchemy import Column, String, Boolean, ForeignKey, UUID, Integer, Enum as SQLEnum
from datetime import datetime
from . database import Base
from enum import Enum
import uuid

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    unique = Column(String, unique=True, nullable=False)  # Renamed from 'unique'
    first_name = Column(String, nullable=False)
    middle_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    password = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    tg_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    registryed_at = Column(Integer, nullable=False, default=int(datetime.utcnow().timestamp()))  # Cast to int

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(Integer, nullable=False, default=datetime.utcnow().timestamp())

