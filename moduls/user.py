from responses import SearchUser as UserResponseSearch
from fastapi import APIRouter, HTTPException, Depends
from requests import UpdateUser as UpdateUserRequest
from requests import SearchUser as UserRequestSearch
from requests import RemoveUser as RemoveUserRequest
from db.models import User, UserRole, Friendship
from sqlalchemy.ext.asyncio import AsyncSession
from requests import CreateUser as RegisterUser
from responses import User as UserResponse
from sqlalchemy import select, delete
from db.database import get_db
from auth import verify_token
from datetime import datetime
import os

router = APIRouter(dependencies=[Depends(verify_token)])

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
        searched=[
            UserResponse(
                id=user.id, unique=user.unique, first_name=user.first_name,
                middle_name=user.middle_name, last_name=user.last_name,
                phone=user.phone, email=user.email, tg_id=user.tg_id,
                rating=user.rating, registryed_at=datetime.fromtimestamp(user.registryed_at)
            ) for user in users
        ],
        start=search_filter.start,
        limit=15
    )

@router.post("/update/user_id/{user_id}", response_model=UserResponse, responses={
    200: {"description": "User updated successfully"},
    400: {"description": "No changes detected or unique identifier already exists"}
})
async def update(update_data: UpdateUserRequest, user_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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

    return UserResponse(
        id=user.id, unique=user.unique, first_name=user.first_name,
        middle_name=user.middle_name, last_name=user.last_name,
        phone=user.phone, email=user.email, tg_id=user.tg_id,
        rating=user.rating, registryed_at=datetime.fromtimestamp(user.registryed_at)
    )

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

    return UserResponse(
        id=new_user.id, unique=new_user.unique, first_name=new_user.first_name,
        middle_name=new_user.middle_name, last_name=new_user.last_name,
        phone=new_user.phone, email=new_user.email, tg_id=new_user.tg_id,
        rating=new_user.rating, registryed_at=datetime.fromtimestamp(new_user.registryed_at)
    )

@router.post("/remove", responses={
    200: {"description": "User removed successfully"},
    404: {"description": "Unique identifier or password is incorrect"}
})
async def remove(data: RemoveUserRequest, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.unique == data.unique, User.password == data.password))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Unique identifier or password is incorrect")

    await session.execute(delete(Friendship).where(Friendship.user_id == user.id))
    await session.delete(user)
    await session.commit()

    raise HTTPException(status_code=200, detail="User removed successfully")

@router.get("/user_id/{user_id}", response_model=UserResponse, responses={
    200: {"description": "User found"}, 
    404: {"description": "User not found"}
})
async def get_by_id(user_id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id, unique=user.unique, first_name=user.first_name,
        middle_name=user.middle_name, last_name=user.last_name,
        phone=user.phone, email=user.email, tg_id=user.tg_id,
        rating=user.rating, registryed_at=datetime.fromtimestamp(user.registryed_at)
    )

@router.post("/rating", response_model=list[UserResponse], responses={
    200: {"description": "Users found"}, 
    404: {"description": "No users found"}
})
async def get_rating_players(start: int=0, session: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.role == UserRole.USER).order_by(User.rating.desc()).offset(start).limit(10)
    result = await session.execute(stmt)
    users = result.scalars().all()

    return [
        UserResponse(
            id=user.id, unique=user.unique, first_name=user.first_name,
            middle_name=user.middle_name, last_name=user.last_name,
            phone=user.phone, email=user.email, tg_id=user.tg_id,
            rating=user.rating, registryed_at=datetime.fromtimestamp(user.registryed_at)
        ) for user in users
    ]