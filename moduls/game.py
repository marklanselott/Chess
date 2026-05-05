from responses import StartOpponentSearch as StartOpponentSearchResponse
from db.models import OpponentSearch, GameSessionStatus, User, UserRole
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from db.database import get_db
from auth import verify_token
import asyncio
import os

router = APIRouter(dependencies=[Depends(verify_token)])
rating_search_range = int(os.getenv("RATING_SEARCH_RANGE", 100))

def opponent_search_response(search: OpponentSearch):
    return StartOpponentSearchResponse(
        id=search.id,
        user_id=search.user_id,
        status=search.status,
        oponent=search.oponent
    )

async def get_opponent_search(session: AsyncSession, user_id: str):
    result = await session.execute(select(OpponentSearch).filter(OpponentSearch.user_id == user_id))
    return result.scalars().first()

async def get_user(session: AsyncSession, user_id: str):
    result = await session.execute(select(User).filter(User.id == user_id))
    return result.scalars().first()

@router.post("/start_search_opponent", responses={
    200: {"description": "Successfully started searching for opponent"},
    404: {"description": "User not found"}
}, response_model=StartOpponentSearchResponse)
async def start_search_opponent(user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_user(session, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    opponent_search = await get_opponent_search(session, user.id)

    if not opponent_search:
        opponent_search = OpponentSearch(user_id=user.id, status=GameSessionStatus.Searching)
        session.add(opponent_search)
    else:
        if opponent_search.status == GameSessionStatus.Searching:
            raise HTTPException(status_code=400, detail="Already searching for opponent")

        opponent_search.status = GameSessionStatus.Searching
        opponent_search.oponent = None

    await session.commit()
    await session.refresh(opponent_search)

    return opponent_search_response(opponent_search)

@router.get("/await_oponent", responses={
    200: {"description": "Successfully got opponent"},
    404: {"description": "User not found or opponent not found"}
}, response_model=StartOpponentSearchResponse)
async def await_opponent(user_id: str, session: AsyncSession = Depends(get_db)):
    while True:
        user = await get_user(session, user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        opponent_search = await get_opponent_search(session, user.id)

        if not opponent_search:
            raise HTTPException(status_code=404, detail="Opponent search not found")

        if opponent_search.oponent:
            return opponent_search_response(opponent_search)

        min_rating = user.rating - rating_search_range
        max_rating = user.rating + rating_search_range
        opponent_result = await session.execute(
            select(OpponentSearch)
            .join(User, OpponentSearch.user_id == User.id)
            .filter(
                and_(
                    OpponentSearch.user_id != user.id,
                    OpponentSearch.status == GameSessionStatus.Searching,
                    OpponentSearch.oponent == None,
                    User.is_active == True,
                    User.role == UserRole.USER,
                    User.rating >= min_rating,
                    User.rating <= max_rating
                )
            )
            .order_by(func.random())
            .limit(1)
        )
        opponent_waiting_search = opponent_result.scalars().first()

        if opponent_waiting_search:
            opponent_search.oponent = opponent_waiting_search.user_id
            opponent_search.status = GameSessionStatus.WaitingOpponent
            opponent_waiting_search.oponent = user.id
            opponent_waiting_search.status = GameSessionStatus.WaitingOpponent

            await session.commit()
            await session.refresh(opponent_search)
            return opponent_search_response(opponent_search)

        await asyncio.sleep(3)

@router.post("/stop_search_opponent", responses={
    200: {"description": "Successfully stopped searching for opponent"},
    404: {"description": "User not found"}
})
async def stop_search_opponent(user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_opponent_search(session, user_id)
    
    if not user:
        raise HTTPException(status_code=400, detail="Not currently searching for opponent")

    if user.oponent and user.status == GameSessionStatus.WaitingOpponent:
        opponent_search = await get_opponent_search(session, user.oponent)
        if opponent_search and opponent_search.status == GameSessionStatus.WaitingOpponent:
            opponent_search.oponent = None
            opponent_search.status = GameSessionStatus.Searching

    await session.delete(user)
    await session.commit()

    return {"message": "Stopped searching for opponent"}

@router.post("/confirm_opponent", responses={
    200: {"description": "Successfully confirmed opponent"},
    404: {"description": "Opponent search not found"}
}, response_model=StartOpponentSearchResponse)
async def confirm_opponent(user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_opponent_search(session, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="Opponent search not found")

    if not user.oponent:
        raise HTTPException(status_code=400, detail="Opponent not found yet")

    user.status = GameSessionStatus.InGame
    await session.commit()
    await session.refresh(user)

    return opponent_search_response(user)
