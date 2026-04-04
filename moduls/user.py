from fastapi import APIRouter, HTTPException, Depends
from requests import CreateUser as RegisterUser
from responses import User as UserResponse
from responses import UserSearch as UserResponseSearch
from db.database import SessionLocal
from db.models import User, UserRole
from requests import UserSearch as UserRequestSearch
from auth import verify_token
from datetime import datetime

router = APIRouter(dependencies=[Depends(verify_token)])

@router.post("/search/", responses={
    200: {"description": "Successful search"}
}, response_model=UserResponseSearch)
async def search(search_filter: UserRequestSearch):
    with SessionLocal() as session:
        query = session.query(User).filter(User.role == UserRole.USER)

        if search_filter.unique:
            query = query.filter(User.unique == search_filter.unique)
        if search_filter.first_name:
            query = query.filter(User.first_name == search_filter.first_name)
        if search_filter.middle_name:
            query = query.filter(User.middle_name == search_filter.middle_name)
        if search_filter.last_name:
            query = query.filter(User.last_name == search_filter.last_name)
        if search_filter.phone:
            query = query.filter(User.phone == search_filter.phone)
        if search_filter.email:
            query = query.filter(User.email == search_filter.email)

        users = query.offset(search_filter.start).limit(15).all()

        return {
            "searched": [
                UserResponse(
                    unique=user.unique,
                    first_name=user.first_name,
                    middle_name=user.middle_name,
                    last_name=user.last_name,
                    phone=user.phone,
                    email=user.email,
                    registryed_at=datetime.fromtimestamp(user.registryed_at)
                ) for user in users
            ],
            "start": search_filter.start,
            "limit": 15
        }



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
            is_active=True,
            role=UserRole.USER,
            registryed_at=int(datetime.utcnow().timestamp())
        )
        session.add(new_user)
        session.commit()

        return UserResponse(
            unique=new_user.unique,
            first_name=new_user.first_name,
            middle_name=new_user.middle_name,
            last_name=new_user.last_name,
            phone=new_user.phone,
            email=new_user.email,
            registryed_at=datetime.fromtimestamp(new_user.registryed_at)
        )

