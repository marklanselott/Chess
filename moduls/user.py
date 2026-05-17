from responses import SearchUser as UserResponseSearch
from responses import UserStats as UserStatsResponse
from fastapi import APIRouter, HTTPException, Depends
from requests import UpdateUser as UpdateUserRequest
from requests import SearchUser as UserRequestSearch
from requests import RemoveUser as RemoveUserRequest
from db.models import GameMove, Games, OpponentSearch, User, UserRole, Friendship
from sqlalchemy.ext.asyncio import AsyncSession
from requests import CreateUser as RegisterUser
from responses import User as UserResponse
from sqlalchemy import or_, select, delete
from db.database import get_db
from auth import verify_token
from utils import get_user_or_404, setup_logger, user_to_response
from datetime import datetime
import os

router = APIRouter(dependencies=[Depends(verify_token)])
logger = setup_logger(__name__)

@router.post("/search/", response_model=UserResponseSearch, responses={
    200: {"description": "Successful search"},
    404: {"description": "No users found"}
})
async def search(search_filter: UserRequestSearch, session: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.role == UserRole.USER)
    filtered = False

    if search_filter.unique:
        filtered = True
        stmt = stmt.where(User.unique == search_filter.unique)
    if search_filter.first_name:
        filtered = True
        stmt = stmt.where(User.first_name == search_filter.first_name)
    if search_filter.middle_name:
        filtered = True
        stmt = stmt.where(User.middle_name == search_filter.middle_name)
    if search_filter.last_name:
        filtered = True
        stmt = stmt.where(User.last_name == search_filter.last_name)
    if search_filter.phone:
        filtered = True
        stmt = stmt.where(User.phone == search_filter.phone)
    if search_filter.tg_id:
        filtered = True
        stmt = stmt.where(User.tg_id == search_filter.tg_id)
    if search_filter.email:
        filtered = True
        stmt = stmt.where(User.email == search_filter.email)

    if filtered:
        result = await session.execute(stmt.offset(search_filter.start).limit(15))
        users = result.scalars().all()
    else:
        users = []

    return UserResponseSearch(
        searched=[user_to_response(user) for user in users],
        start=search_filter.start,
        limit=15
    )

@router.post("/update/user_id/{user_id}", response_model=UserResponse, responses={
    200: {"description": "User updated successfully"},
    400: {"description": "No changes detected or unique identifier already exists"}
})
async def update(update_data: UpdateUserRequest, user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)

    changed = False

    if update_data.unique and update_data.unique != user.unique:
        check_stmt = await session.execute(select(User).where(User.unique == update_data.unique))
        if check_stmt.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Unique identifier already exists")
        user.unique = update_data.unique
        changed = True
        
    if update_data.password and update_data.password != user.password:
        user.password = update_data.password
        changed = True
    if update_data.first_name and update_data.first_name != user.first_name:
        user.first_name = update_data.first_name
        changed = True
    if update_data.middle_name and update_data.middle_name != user.middle_name:
        user.middle_name = update_data.middle_name
        changed = True
    if update_data.last_name and update_data.last_name != user.last_name:
        user.last_name = update_data.last_name
        changed = True
    if update_data.phone and update_data.phone != user.phone:
        user.phone = update_data.phone
        changed = True
    if update_data.email and update_data.email != user.email:
        user.email = update_data.email
        changed = True

    if not changed:
        raise HTTPException(status_code=400, detail="No changes detected")

    await session.commit()
    await session.refresh(user)
    logger.info("User updated: user_id=%s", user.id)

    return user_to_response(user)

@router.post("/register", response_model=UserResponse, responses={
    200: {"description": "User registered successfully"},
    400: {"description": "Unique identifier already exists"}
})
async def register(data: RegisterUser, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.unique == data.unique))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Unique identifier already exists")

    new_user = User(
        unique=data.unique, first_name=data.first_name, middle_name=data.middle_name,
        last_name=data.last_name, password=data.password, phone=data.phone,
        email=data.email, tg_id=data.tg_id, rating=int(os.getenv("BASE_USER_RATING")),
        is_active=True, role=UserRole.USER, registryed_at=int(datetime.utcnow().timestamp())
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    logger.info("User registered: user_id=%s unique=%s", new_user.id, new_user.unique)

    return user_to_response(new_user)

@router.post("/remove", responses={
    200: {"description": "User removed successfully"},
    404: {"description": "Unique identifier or password is incorrect"}
})
async def remove(data: RemoveUserRequest, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.unique == data.unique, User.password == data.password))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Unique identifier or password is incorrect")

    games_result = await session.execute(
        select(Games.id).where(or_(Games.white_id == user.id, Games.black_id == user.id))
    )
    game_ids = [row[0] for row in games_result.all()]

    if game_ids:
        await session.execute(delete(GameMove).where(GameMove.game_id.in_(game_ids)))
        await session.execute(delete(OpponentSearch).where(OpponentSearch.game_id.in_(game_ids)))
        await session.execute(delete(Games).where(Games.id.in_(game_ids)))

    await session.execute(delete(OpponentSearch).where(OpponentSearch.user_id == user.id))
    await session.execute(delete(Friendship).where(Friendship.user_id == user.id))
    await session.execute(delete(Friendship).where(Friendship.friend_id == user.id))
    await session.delete(user)
    await session.commit()
    logger.info("User removed: user_id=%s unique=%s games_removed=%s", user.id, user.unique, len(game_ids))

    raise HTTPException(status_code=200, detail="User removed successfully")

@router.get("/user_id/{user_id}", response_model=UserResponse, responses={
    200: {"description": "User found"}, 
    404: {"description": "User not found"}
})
async def get_by_id(user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)
    return user_to_response(user)

@router.get("/stats/user_id/{user_id}", response_model=UserStatsResponse, responses={
    200: {"description": "User stats found"},
    404: {"description": "User not found"}
})
async def get_stats(user_id: str, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)
    result = await session.execute(
        select(Games).where(or_(Games.white_id == user.id, Games.black_id == user.id))
    )
    games = result.scalars().all()

    wins = sum(1 for game in games if game.result == "win" and game.winner_id == user.id)
    losses = sum(1 for game in games if game.result == "win" and game.loser_id == user.id)
    draws = sum(1 for game in games if game.result == "draw")
    games_finished = wins + losses + draws
    games_total = len(games)
    win_loss_ratio = round(wins / losses, 2) if losses else None
    win_rate = round((wins / games_finished) * 100, 2) if games_finished else 0.0

    logger.info(
        "User stats requested: user_id=%s games=%s wins=%s losses=%s draws=%s",
        user.id,
        games_total,
        wins,
        losses,
        draws,
    )

    return UserStatsResponse(
        user=user_to_response(user),
        games_total=games_total,
        games_finished=games_finished,
        games_active=games_total - games_finished,
        wins=wins,
        losses=losses,
        draws=draws,
        win_loss_ratio=win_loss_ratio,
        win_rate=win_rate,
        rating=user.rating,
    )

@router.post("/rating", response_model=list[UserResponse], responses={
    200: {"description": "Users found"}, 
    404: {"description": "No users found"}
})
async def get_rating_players(start: int=0, session: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.role == UserRole.USER).order_by(User.rating.desc()).offset(start).limit(10)
    result = await session.execute(stmt)
    users = result.scalars().all()

    return [user_to_response(user) for user in users]

