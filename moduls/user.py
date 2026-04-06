from responses import SearchUser as UserResponseSearch
from fastapi import APIRouter, HTTPException, Depends
from requests import UpdateUser as UpdateUserRequest
from requests import SearchUser as UserRequestSearch
from requests import RemoveUser as RemoveUserRequest
from db.models import User, UserRole, Friendship
from requests import CreateUser as RegisterUser
from responses import User as UserResponse
from db.database import SessionLocal
from auth import verify_token
from datetime import datetime
import os

router = APIRouter(dependencies=[Depends(verify_token)])

@router.post("/search/", responses={
    200: {"description": "Successful search"}
}, response_model=UserResponseSearch)
async def search(search_filter: UserRequestSearch):
    with SessionLocal() as session:
        query = session.query(User).filter(User.role == UserRole.USER)
        filtered = False

        if search_filter.unique:
            filtered = True
            query = query.filter(User.unique == search_filter.unique)
        if search_filter.first_name:
            filtered = True
            query = query.filter(User.first_name == search_filter.first_name)
        if search_filter.middle_name:
            filtered = True
            query = query.filter(User.middle_name == search_filter.middle_name)
        if search_filter.last_name:
            filtered = True
            query = query.filter(User.last_name == search_filter.last_name)
        if search_filter.phone:
            filtered = True
            query = query.filter(User.phone == search_filter.phone)
        if search_filter.tg_id:
            filtered = True
            query = query.filter(User.tg_id == search_filter.tg_id)
        if search_filter.email:
            filtered = True
            query = query.filter(User.email == search_filter.email)

        users = query.offset(search_filter.start).limit(15).all() if filtered else []

        return {
            "searched": [
                UserResponse(
                    id=user.id,
                    unique=user.unique,
                    first_name=user.first_name,
                    middle_name=user.middle_name,
                    last_name=user.last_name,
                    phone=user.phone,
                    email=user.email,
                    tg_id=user.tg_id,
                    rating=user.rating,
                    registryed_at=datetime.fromtimestamp(user.registryed_at)
                ) for user in users
            ],
            "start": search_filter.start,
            "limit": 15
        }

@router.post("/update/user_id/{user_id}", responses={
    200: {"description": "Successful updated"},
    400: {"description": "Unique identifier already exists"},
    404: {"description": "User not found"}
}, response_model=UserResponse)
async def update(update_data: UpdateUserRequest, user_id: str):
    with SessionLocal() as session:
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        changed = False

        if update_data.unique and update_data.unique != user.unique:
            if session.query(User).filter(User.unique == update_data.unique).first():
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

        session.commit()
        session.refresh(user)

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
            registryed_at=datetime.fromtimestamp(user.registryed_at)
        )

@router.post("/register", responses={
    201: {"description": "User successfully registered"},
    400: {"description": "Unique identifier already exists"}
}, response_model=UserResponse)
async def register(data: RegisterUser):
    with SessionLocal() as session:
        if session.query(User).filter(User.unique == data.unique).first():
            raise HTTPException(status_code=400, detail="Unique identifier already exists")

        new_user = User(
            unique=data.unique,
            first_name=data.first_name,
            middle_name=data.middle_name,
            last_name=data.last_name,
            password=data.password,
            phone=data.phone,
            email=data.email,
            tg_id=data.tg_id,
            rating=int(os.getenv("BASE_USER_RATING")),
            is_active=True,
            role=UserRole.USER,
            registryed_at=int(datetime.utcnow().timestamp())
        )
        session.add(new_user)
        session.commit()

        return UserResponse(
            id=new_user.id,
            unique=new_user.unique,
            first_name=new_user.first_name,
            middle_name=new_user.middle_name,
            last_name=new_user.last_name,
            phone=new_user.phone,
            email=new_user.email,
            tg_id=new_user.tg_id,
            rating=new_user.rating,
            registryed_at=datetime.fromtimestamp(new_user.registryed_at)
        )

@router.post("/remove", responses={
    200: {"description": "User successfully removed"},
    404: {"description": "Unique identifier or password is incorrect"}
})
async def remove(data: RemoveUserRequest):
    with SessionLocal() as session:
        user = session.query(User).filter(User.unique == data.unique, User.password == data.password).first()

        if not user:
            raise HTTPException(status_code=404, detail="Unique identifier or password is incorrect")

        session.query(Friendship).filter(Friendship.user_id == user.id).delete()

        session.delete(user)
        session.commit()

        return {"detail": "User successfully removed"}

@router.get("/user_id/{user_id}", responses={
    200: {"description": "User found"},
    404: {"description": "User not found"}
}, response_model=UserResponse)
async def get_by_id(user_id: str):
    with SessionLocal() as session:
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

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
            registryed_at=datetime.fromtimestamp(user.registryed_at)
        )

@router.post("/rating", responses={
    200: {"description": "Rating updated successfully"},
    404: {"description": "User not found"}
}, response_model=UserResponse)
async def get_rating_players(start: int=0):
    with SessionLocal() as session:
        users = session.query(User).filter(User.role == UserRole.USER).order_by(User.rating.desc()).offset(start).limit(10).all()

        return [
            UserResponse(
                id=user.id,
                unique=user.unique,
                first_name=user.first_name,
                middle_name=user.middle_name,
                last_name=user.last_name,
                phone=user.phone,
                email=user.email,
                tg_id=user.tg_id,
                rating=user.rating,
                registryed_at=datetime.fromtimestamp(user.registryed_at)
            ) for user in users
        ]


