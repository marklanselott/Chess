import logging
import os
from random import randint
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import GameMove, Games, OpponentSearch, User, UserRole
from responses import GameResult, RatingChange, User as UserResponse


def setup_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    return logging.getLogger(name)


def user_to_response(user: User) -> UserResponse:
    registryed_at = user.registryed_at
    if isinstance(registryed_at, int):
        registryed_at = datetime.fromtimestamp(registryed_at)

    return UserResponse(
        id=user.id,
        unique=user.unique,
        first_name=user.first_name,
        middle_name=user.middle_name,
        last_name=user.last_name,
        phone=user.phone,
        email=user.email,
        tg_id=user.tg_id,
        rating=user.rating,
        registryed_at=registryed_at,
    )


async def get_or_create_ai_user(session: AsyncSession) -> User:
    unique = os.getenv("AI_USER_UNIQUE", "chess_ai")
    result = await session.execute(select(User).where(User.unique == unique))
    ai_user = result.scalar_one_or_none()
    if ai_user:
        return ai_user

    ai_user = User(
        unique=unique,
        first_name=os.getenv("AI_USER_FIRST_NAME", "Chess AI"),
        middle_name=None,
        last_name=None,
        password=os.getenv("AI_USER_PASSWORD", "ai_opponent"),
        phone=None,
        email=os.getenv("AI_USER_EMAIL"),
        tg_id=None,
        rating=int(os.getenv("AI_USER_RATING", os.getenv("BASE_USER_RATING", 400))),
        is_active=True,
        role=UserRole.ADMIN,
        registryed_at=int(datetime.utcnow().timestamp()),
    )
    session.add(ai_user)
    await session.flush()
    return ai_user


async def get_user_or_404(session: AsyncSession, user_id: UUID | str) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_game_or_404(session: AsyncSession, game_id: UUID) -> Games:
    result = await session.execute(select(Games).where(Games.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


async def get_last_move_or_404(session: AsyncSession, game_id: UUID) -> GameMove:
    result = await session.execute(
        select(GameMove)
        .where(GameMove.game_id == game_id)
        .order_by(GameMove.step.desc())
        .limit(1)
    )
    move = result.scalar_one_or_none()
    if not move:
        raise HTTPException(status_code=404, detail="Game board not found")
    return move


def apply_rating_delta(user: User, delta: int) -> RatingChange:
    before = int(user.rating or 0)
    after = max(0, before + delta)
    user.rating = after

    return RatingChange(
        user_id=user.id,
        before=before,
        after=after,
        delta=after - before,
    )


def mark_game_finished(
    game: Games,
    result: str,
    reason: str,
    winner_id: UUID | None = None,
    loser_id: UUID | None = None,
) -> None:
    game.result = result
    game.result_reason = reason
    game.winner_id = winner_id
    game.loser_id = loser_id
    game.finished_at = int(datetime.utcnow().timestamp())


async def apply_game_result(
    session: AsyncSession,
    game: Games,
    winner: User,
    loser: User,
    reason: str,
    loser_penalty_range: tuple[int, int] = (20, 25),
) -> GameResult:
    if game.result:
        raise HTTPException(status_code=400, detail="Game already finished")

    winner_change = apply_rating_delta(winner, randint(20, 25))
    loser_change = apply_rating_delta(loser, -randint(*loser_penalty_range))
    mark_game_finished(
        game,
        result="win",
        reason=reason,
        winner_id=winner.id,
        loser_id=loser.id,
    )
    await session.flush()

    return GameResult(
        reason=reason,
        winner=winner_change,
        loser=loser_change,
    )


async def apply_game_draw(session: AsyncSession, game: Games, reason: str) -> None:
    if game.result:
        raise HTTPException(status_code=400, detail="Game already finished")

    mark_game_finished(game, result="draw", reason=reason)
    await session.flush()


async def clear_game_sessions(session: AsyncSession, game_id: UUID) -> None:
    await session.execute(delete(OpponentSearch).where(OpponentSearch.game_id == game_id))
