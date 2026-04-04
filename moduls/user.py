from fastapi import APIRouter, HTTPException, Depends
from requests import CreateUser as RegisterUser
from responses import User as UserResponse
from db.database import SessionLocal
from auth import verify_token
from datetime import datetime
from db.models import User, UserRole

router = APIRouter(dependencies=[Depends(verify_token)])

@router.get("/search/{unique}", responses={
    200: {"description": "Successful search"},
    400: {"description": "Unique identifier cannot be empty"}
}, response_model=list[UserResponse])
async def search(unique: str):
    if unique == "":
        raise HTTPException(status_code=400, detail="Unique identifier cannot be empty")
    
    with SessionLocal() as session:
        db_users = session.query(User).filter(User.unique.like(f"%{unique}%")).all()
        users = []

        for user in db_users:
            users.append(UserResponse(
                unique=user.unique,
                first_name=user.first_name,
                middle_name=user.middle_name,
                last_name=user.last_name,
                phone=user.phone,
                email=user.email,
                registryed_at=datetime.fromtimestamp(user.registryed_at)
            ))
        
        return users

@router.post("/register", responses={
    201: {"description": "User successfully registered"},
    400: {"description": "Unique identifier already exists"}
}, response_model=UserResponse)
async def register(data: RegisterUser):
    with SessionLocal() as session:
        if session.query(User).filter(User.unique == data.unique).first():  # Updated field name
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

