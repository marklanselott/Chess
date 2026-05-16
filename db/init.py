from dotenv import load_dotenv; load_dotenv()
from .database import engine, Base
from sqlalchemy import text
from . import models
import asyncio

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS result VARCHAR"))
        await conn.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS result_reason VARCHAR"))
        await conn.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS winner_id UUID"))
        await conn.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS loser_id UUID"))
        await conn.execute(text("ALTER TABLE games ADD COLUMN IF NOT EXISTS finished_at INTEGER"))
