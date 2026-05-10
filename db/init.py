from dotenv import load_dotenv; load_dotenv()
from .database import engine, Base
from . import models
import asyncio

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)