from responses import StartOpponentSearch as StartOpponentSearchResponse
from db.models import GameMove, OpponentSearch, GameSessionStatus, Games
from responses import SearchedOpponent as SearchedOpponentResponse
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from responses import Game as GameResponse
from responses import User as UserResponse
from sqlalchemy.future import select
from sqlalchemy import func, and_
from db.database import get_db
from auth import verify_token
from moduls.game import Game
from utils import get_user_or_404, setup_logger, user_to_response
from uuid import uuid4, UUID
import asyncio, os, random

router = APIRouter(dependencies=[Depends(verify_token)])
logger = setup_logger(__name__)

async def get_opponent_search(session: AsyncSession, user_id: UUID):
    opponent_search = await session.execute(
        select(OpponentSearch).where(OpponentSearch.user_id == user_id)
    )
    return opponent_search.scalar_one_or_none()

async def random_uuid_in_rating_range(session: AsyncSession, user_id: UUID, rating: int):
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

async def get_game_opponent(session: AsyncSession, user_id: UUID, game_id: UUID):
    opponent = await session.execute(
        select(OpponentSearch).where(
            and_(
                OpponentSearch.user_id != user_id,
                OpponentSearch.game_id == game_id,
                OpponentSearch.status == GameSessionStatus.InGame
            )
        )
    )
    return opponent.scalar_one_or_none()

@router.post("/search/start", responses={
    200: {"description": "Successfully started searching for opponent"},
    404: {"description": "User not found"}
}, response_model=StartOpponentSearchResponse)
async def start_search_opponent(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)

    opponent = (await session.execute(select(OpponentSearch).where(OpponentSearch.user_id == user_id))).scalar_one_or_none()
    if opponent: 

        cases = {
            GameSessionStatus.Searching: "You are already searching for an opponent.",
            GameSessionStatus.InGame: "While you are in the game, you cannot start searching for an opponent."
        }

        raise HTTPException(status_code=400, detail=cases.get(opponent.status, f"Unknown status >>> {opponent.status}"))
    else:
        session.add(OpponentSearch(user_id=user_id, rating=user.rating, status=GameSessionStatus.Searching))
        await session.commit()
        logger.info("Opponent search started: user_id=%s", user_id)
    
    return StartOpponentSearchResponse(
        user=user_to_response(user),
        opponent=None
    )

@router.get("/await", responses={
    200: {"description": "Successfully got opponent"},
    404: {"description": "User not found or opponent not found"}
}, response_model=StartOpponentSearchResponse)
async def await_opponent(user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)
    user_opponent = await get_opponent_search(session, user_id)

    if not user_opponent:
        raise HTTPException(status_code=404, detail="Opponent search not found")
    
    if user_opponent.status == GameSessionStatus.InGame:
        raise HTTPException(status_code=404, detail="You can't wait for an opponent while in the game")

    async def find_opponent():
        while True:
            result = SearchedOpponentResponse(
                user=user_to_response(user),
                opponent=None,
                game=None
            )

            user_opponent = await get_opponent_search(session, user_id)
            if not user_opponent:
                return
            
            if user_opponent.status == GameSessionStatus.InGame and user_opponent.game_id:
                opponent = await get_game_opponent(session, user_id, user_opponent.game_id)
                if opponent:
                    opponent = await get_user_or_404(session, opponent.user_id)
                    result.opponent = user_to_response(opponent)
                    yield result.model_dump_json() + "\n"
                    return

            opponent = await random_uuid_in_rating_range(session, user_id, user.rating)
            
            if opponent:
                if user_opponent.status == GameSessionStatus.Searching:
                    game_id = uuid4()
                    opponent.status = GameSessionStatus.InGame
                    opponent.game_id = game_id

                    user_opponent.status = GameSessionStatus.InGame
                    user_opponent.game_id = game_id
                    await session.commit()

                    try:
                        opponent = await get_user_or_404(session, opponent.user_id)
                    except HTTPException:
                        await session.delete(opponent)
                        await session.commit()
                        logger.warning("Removed stale opponent search: user_id=%s", user_id)
                        continue
                    opponent = user_to_response(opponent)

                    colors = ["white", "black"]
                    rand_color = random.choice(colors)
                    board = Game.board()
                    if rand_color == colors[0]: 
                        white = user_to_response(user)
                        black = user_to_response(opponent)
                    else: 
                        black = user_to_response(user)
                        white = user_to_response(opponent)

                    game = GameResponse(
                        id=game_id,
                        white=white.id,
                        black=black.id,
                        board=board
                    )

                    session.add(Games(
                        id=game_id,
                        white_id=white.id,
                        black_id=black.id
                    ))
                    await session.flush()

                    new_game = GameMove(
                        game_id=game_id,
                        fen=game.board.fen,
                        step=0
                    )
                    session.add(new_game)
                    await session.commit()
                    result.opponent = opponent
                    result.game = game
                    logger.info("Opponent found: game_id=%s user_id=%s opponent_id=%s", game_id, user_id, opponent.id)

                    yield result.model_dump_json() + "\n"
                    return
                else:
                    raise HTTPException(status_code=400, detail=f"Outside of the search status, you cannot expect to find an opponent.")
            
            await asyncio.sleep(3)

    return StreamingResponse(find_opponent(), media_type="application/json")

@router.post("/search/stop", responses={
    200: {"description": "Successfully stopped searching for opponent"},
    404: {"description": "User not found"}
})
async def stop_search_opponent(user_id: UUID, session: AsyncSession = Depends(get_db)):
    await get_user_or_404(session, user_id)
    
    opponent_user = (await session.execute(select(OpponentSearch).where(OpponentSearch.user_id == user_id))).scalar_one_or_none()
    if opponent_user:
        if opponent_user.status == GameSessionStatus.Searching:
            await session.delete(opponent_user)
            await session.commit()
            logger.info("Opponent search stopped: user_id=%s", user_id)
            return {"detail": "Successfully stopped searching for opponent"}
        else:
            raise HTTPException(status_code=400, detail=f"While you are in the game, you cannot stop searching for an opponent.")
    raise HTTPException(status_code=404, detail="Opponent search not found")
