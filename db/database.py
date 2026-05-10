from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy.orm import DeclarativeBase

import os

engine = create_async_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session



class Base(DeclarativeBase):
    pass