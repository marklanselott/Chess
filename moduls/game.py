from responses import StartOpponentSearch as StartOpponentSearchResponse
from responses import SearchedOpponent as SearchedOpponentResponse
from responses import User as UserResponse
from db.models import OpponentSearch, GameSessionStatus, get_user
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from db.database import get_db
from auth import verify_token
from uuid import uuid4
import asyncio, os

router = APIRouter(dependencies=[Depends(verify_token)])

async def random_uuid_in_rating_range(session: AsyncSession, user_id: str, rating: int):
    rating_range = int(os.getenv("RATING_SEARCH_RANGE", 100))
    min_rating, max_rating = rating - rating_range, rating + rating_range
    opponent = await session.execute(
        select(OpponentSearch).where(
            and_(
                OpponentSearch.user_id != user_id,
                OpponentSearch.rating.between(min_rating, max_rating),
                OpponentSearch.status == GameSessionStatus.Searching
            )
        ).order_by(func.random())
        .limit(1)
    )
    return opponent.scalar_one_or_none()

async def get_duo_opponent(session: AsyncSession, user_id: str, duo):
    opponent = await session.execute(
        select(OpponentSearch).where(
            and_(
                OpponentSearch.user_id != user_id,
                OpponentSearch.duo == duo,
                OpponentSearch.status == GameSessionStatus.InGame
            )
        )
    )
    return opponent.scalar_one_or_none()

@router.post("/start_search_opponent", responses={
    200: {"description": "Successfully started searching for opponent"},
    404: {"description": "User not found"}
}, response_model=StartOpponentSearchResponse)
async def start_search_opponent(user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_user(session, user_id)

    oponent = (await session.execute(select(OpponentSearch).where(OpponentSearch.user_id == user_id))).scalar_one_or_none()
    if oponent: 

        cases = {
            GameSessionStatus.Searching: "You are already searching for an opponent.",
            GameSessionStatus.InGame: "While you are in the game, you cannot start searching for an opponent."
        }

        raise HTTPException(status_code=400, detail=cases.get(oponent.status, f"Unknown status >>> {oponent.status}"))
    else:
        session.add(OpponentSearch(user_id=user_id, rating=user.rating, status=GameSessionStatus.Searching))
        await session.commit()
    
    return StartOpponentSearchResponse(
        user=UserResponse(
            id=user.id,
            unique=user.unique,
            first_name=user.first_name,
            middle_name=user.middle_name,
            last_name=user.last_name,
            phone=user.phone,
            email=user.email,
            tg_id=user.tg_id,
            rating=user.rating,
            registryed_at=user.registryed_at
        ),
        oponent=None
    )


@router.get("/await_oponent", responses={
    200: {"description": "Successfully got opponent"},
    404: {"description": "User not found or opponent not found"}
}, response_model=StartOpponentSearchResponse)
async def await_opponent(user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_user(session, user_id)
    user_opponent = (await session.execute(select(OpponentSearch).where(OpponentSearch.user_id == user_id))).scalar_one_or_none()

    if not user_opponent:
        raise HTTPException(status_code=404, detail="Opponent search not found")
    
    async def find_opponent():
        while True:
            await session.refresh(user_opponent)
            result = SearchedOpponentResponse(
                user=UserResponse(
                    id=user.id,
                    unique=user.unique,
                    first_name=user.first_name,
                    middle_name=user.middle_name,
                    last_name=user.last_name,
                    phone=user.phone,
                    email=user.email,
                    tg_id=user.tg_id,
                    rating=user.rating,
                    registryed_at=user.registryed_at
                ),
                oponent=None
            )

            if user_opponent.status == GameSessionStatus.InGame and user_opponent.duo:
                oponent = await get_duo_opponent(session, user_id, user_opponent.duo)
                if oponent:
                    oponent = await get_user(session, oponent.user_id)
                    result.oponent = UserResponse(
                        id=oponent.id,
                        unique=oponent.unique,
                        first_name=oponent.first_name,
                        middle_name=oponent.middle_name,
                        last_name=oponent.last_name,
                        phone=oponent.phone,
                        email=oponent.email,
                        tg_id=oponent.tg_id,
                        rating=oponent.rating,
                        registryed_at=oponent.registryed_at
                    )
                    yield result.model_dump_json() + "\n"
                    return

            oponent = await random_uuid_in_rating_range(session, user_id, user.rating)
            
            if oponent:
                if user_opponent.status == GameSessionStatus.Searching:
                    duo = uuid4()
                    oponent.status = GameSessionStatus.InGame
                    oponent.duo = duo

                    user_opponent.status = GameSessionStatus.InGame
                    user_opponent.duo = duo
                    await session.commit()

                    oponent = await get_user(session, oponent.user_id)
                    oponent = UserResponse(
                        id=oponent.id,
                        unique=oponent.unique,
                        first_name=oponent.first_name,
                        middle_name=oponent.middle_name,
                        last_name=oponent.last_name,
                        phone=oponent.phone,
                        email=oponent.email,
                        tg_id=oponent.tg_id,
                        rating=oponent.rating,
                        registryed_at=oponent.registryed_at
                    )
                    result.oponent = oponent
                    yield result.model_dump_json() + "\n"
                    return
                else:
                    raise HTTPException(status_code=400, detail=f"Outside of the search status, you cannot expect to find an opponent.")
            
            await asyncio.sleep(3)

    return StreamingResponse(find_opponent(), media_type="application/json")

@router.post("/stop_search_opponent", responses={
    200: {"description": "Successfully stopped searching for opponent"},
    404: {"description": "User not found"}
})
async def stop_search_opponent(user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_user(session, user_id)
    
    opponent_user = (await session.execute(select(OpponentSearch).where(OpponentSearch.user_id == user_id))).scalar_one_or_none()
    if opponent_user:
        if opponent_user.status == GameSessionStatus.Searching:
            await session.delete(opponent_user)
            await session.commit()
            return {"detail": "Successfully stopped searching for opponent"}
        else:
            raise HTTPException(status_code=400, detail=f"While you are in the game, you cannot stop searching for an opponent.")
    
