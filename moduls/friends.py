from requests import SendRequestFriend, UpdateFriendRequest
from fastapi import APIRouter, HTTPException, Depends
from responses import User as UserResponse
from db.database import SessionLocal
from responses import FriendRequest
from db.models import Friendship
from auth import verify_token
from db.models import User
from uuid import UUID

router = APIRouter(dependencies=[Depends(verify_token)])

@router.get("/get_list/user_id/{user_id}", responses={
    200: {"description": "Successful get list of friends"},
    404: {"description": "User not found"}
}, response_model=list[UserResponse])
async def get_friends_list(user_id: UUID, start: int=0):
    with SessionLocal() as session:
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        friendships = session.query(Friendship).filter(
            ((Friendship.user_id == user.id) | (Friendship.friend_id == user.id)) &
            (Friendship.status == True)
        ).offset(start).limit(15)

        friends = []
        for friendship in friendships:
            friend_id = friendship.friend_id if friendship.user_id == user.id else friendship.user_id
            friend = session.query(User).filter(User.id == friend_id).first()
            if friend:
                friends.append(UserResponse(
                    id=friend.id,
                    unique=friend.unique,
                    first_name=friend.first_name,
                    middle_name=friend.middle_name,
                    last_name=friend.last_name,
                    phone=friend.phone,
                    email=friend.email,
                    tg_id=friend.tg_id,
                    rating=friend.rating,
                    registryed_at=friend.registryed_at
                ))

        return friends

@router.post("/send_request", responses={
    200: {"description": "Friend request sent successfully"},
    404: {"description": "User not found"}
}, response_model=FriendRequest)
async def send_friend_request(data: SendRequestFriend):
    with SessionLocal() as session:
        user = session.query(User).filter(User.id == data.user_id).first()
        friend = session.query(User).filter(User.id == data.friend_id).first()

        if not user or not friend:
            raise HTTPException(status_code=404, detail="User not found")

        existing_request = session.query(Friendship).filter(
            ((Friendship.user_id == user.id) & (Friendship.friend_id == friend.id)) |
            ((Friendship.user_id == friend.id) & (Friendship.friend_id == user.id))
        ).first()

        if existing_request:
            raise HTTPException(status_code=400, detail="Friend request already exists")

        new_request = Friendship(user_id=user.id, friend_id=friend.id, status=False)
        session.add(new_request)
        session.commit()

        return FriendRequest(
            id=new_request.id,
            user_id=new_request.user_id,
            friend_id=new_request.friend_id,
            status=new_request.status
        )

@router.get("/cancel_request/request_id/{request_id}", responses={
    200: {"description": "Friend request cancelled successfully"},
    404: {"description": "Friend request not found"}
})
async def cancel_friend_request(request_id: UUID):
    with SessionLocal() as session:
        friendship = session.query(Friendship).filter(Friendship.id == request_id).filter(Friendship.status == False).first()

        if not friendship:
            raise HTTPException(status_code=404, detail="Friend request not found")

        session.delete(friendship)
        session.commit()

        return {"detail": "Friend request cancelled successfully"}

@router.get("/get_requests_my/user_id/{user_id}", responses={
    200: {"description": "Friend requests retrieved successfully"},
    404: {"description": "User not found"}
})
async def get_friend_requests(user_id: UUID):
    with SessionLocal() as session:
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        friend_requests = session.query(Friendship).filter(Friendship.user_id == user.id, Friendship.status == False).all()

        friend = session.query(User).filter(User.id == friend_requests[0].friend_id).first()

        if not friend:
            raise HTTPException(status_code=404, detail="Friend not found")

        return [
            FriendRequest(
                id=req.id,
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
                friend=UserResponse(
                    id=friend.id,
                    unique=friend.unique,
                    first_name=friend.first_name,
                    middle_name=friend.middle_name,
                    last_name=friend.last_name,
                    phone=friend.phone,
                    email=friend.email,
                    tg_id=friend.tg_id,
                    rating=friend.rating,
                    registryed_at=friend.registryed_at
                ),
                status=req.status
            ) for req in friend_requests
        ]

@router.get("/get_requests_for_me/user_id/{user_id}", responses={
    200: {"description": "Friend requests retrieved successfully"},
    404: {"description": "User not found"}
})
async def get_friend_requests(user_id: UUID):
    with SessionLocal() as session:
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        friend_requests = session.query(Friendship).filter(Friendship.friend_id == user.id, Friendship.status == False).all()

        friend = session.query(User).filter(User.id == friend_requests[0].user_id).first()

        if not friend:
            raise HTTPException(status_code=404, detail="Friend not found")

        return [
            FriendRequest(
                id=req.id,
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
                friend=UserResponse(
                    id=friend.id,
                    unique=friend.unique,
                    first_name=friend.first_name,
                    middle_name=friend.middle_name,
                    last_name=friend.last_name,
                    phone=friend.phone,
                    email=friend.email,
                    tg_id=friend.tg_id,
                    rating=friend.rating,
                    registryed_at=friend.registryed_at
                ),
                status=req.status
            ) for req in friend_requests
        ]

@router.post("/update_request", responses={
    200: {"description": "Friend request updated successfully"},
    200: {"description": "Friend request deleted successfully"},
    404: {"description": "Friend request not found"}
})
async def update_friend_request(data: UpdateFriendRequest):
    with SessionLocal() as session:
        friendship = session.query(Friendship).filter(Friendship.id == data.request_id).first()
        updated = False
        removed = False

        if not friendship:
            raise HTTPException(status_code=404, detail="Friend request not found")

        if not friendship.status and not data.status:
            session.delete(friendship)
            removed = True
        else:
            friendship.status = data.status
            updated = True
        
        session.commit()

        
        if updated:
            return {"detail": "Friend request updated successfully"}
        elif removed:
            return {"detail": "Friend request deleted successfully"}