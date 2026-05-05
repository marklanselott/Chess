from requests import SendRequestFriend, UpdateFriendRequest
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from responses import User as UserResponse
from sqlalchemy import or_, and_, delete
from db.models import Friendship, User
from sqlalchemy.future import select
from responses import FriendRequest
from auth import verify_token
from db.database import get_db
from uuid import UUID

router = APIRouter(dependencies=[Depends(verify_token)])

@router.get("/get_list/user_id/{user_id}", responses={
    200: {"description": "Successful get list of friends"},
    404: {"description": "User not found"}
}, response_model=list[UserResponse])
async def get_friends_list(user_id: UUID, start: int = 0, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(Friendship).filter(
        and_(
            or_(Friendship.user_id == user.id, Friendship.friend_id == user.id),
            Friendship.status == True
        )
    ).offset(start).limit(15)
    
    friendships_result = await session.execute(stmt)
    friendships = friendships_result.scalars().all()

    friends = []
    for friendship in friendships:
        friend_id = friendship.friend_id if friendship.user_id == user.id else friendship.user_id
        friend_result = await session.execute(select(User).filter(User.id == friend_id))
        friend = friend_result.scalars().first()
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
async def send_friend_request(data: SendRequestFriend, session: AsyncSession = Depends(get_db)):
    user_res = await session.execute(select(User).filter(User.id == data.user_id))
    friend_res = await session.execute(select(User).filter(User.id == data.friend_id))
    user = user_res.scalars().first()
    friend = friend_res.scalars().first()

    if not user or not friend:
        raise HTTPException(status_code=404, detail="User not found")

    exist_stmt = select(Friendship).filter(
        or_(
            and_(Friendship.user_id == user.id, Friendship.friend_id == friend.id),
            and_(Friendship.user_id == friend.id, Friendship.friend_id == user.id)
        )
    )
    existing_request = (await session.execute(exist_stmt)).scalars().first()

    if existing_request:
        raise HTTPException(status_code=400, detail="Friend request already exists")

    new_request = Friendship(user_id=user.id, friend_id=friend.id, status=False)
    session.add(new_request)
    await session.commit()
    await session.refresh(new_request)

    return FriendRequest(
        id=new_request.id,
        user=UserResponse(**user.__dict__), # Упрощенный маппинг
        friend=UserResponse(**friend.__dict__),
        status=new_request.status
    )

@router.get("/cancel_request/request_id/{request_id}", responses={
    200: {"description": "Friend request cancelled successfully"},
    404: {"description": "Friend request not found"}
})
async def cancel_friend_request(request_id: UUID, session: AsyncSession = Depends(get_db)):
    stmt = select(Friendship).filter(Friendship.id == request_id, Friendship.status == False)
    friendship = (await session.execute(stmt)).scalars().first()

    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")

    await session.delete(friendship)
    await session.commit()

    return {"detail": "Friend request cancelled successfully"}

@router.get("/get_requests_my/user_id/{user_id}", responses={
    200: {"description": "Friend requests retrieved successfully"},
    404: {"description": "User not found"}
})
async def get_friend_requests(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = (await session.execute(select(User).filter(User.id == user_id))).scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(Friendship).filter(Friendship.user_id == user.id, Friendship.status == False)
    friend_requests = (await session.execute(stmt)).scalars().all()

    if not friend_requests:
        return []

    # Логика из оригинала: берем друга для первого запроса (странная логика, но сохранена)
    friend = (await session.execute(select(User).filter(User.id == friend_requests[0].friend_id))).scalars().first()

    if not friend:
        raise HTTPException(status_code=404, detail="Friend not found")

    return [
        FriendRequest(
            id=req.id,
            user=UserResponse(**user.__dict__),
            friend=UserResponse(**friend.__dict__),
            status=req.status
        ) for req in friend_requests
    ]

@router.get("/get_requests_for_me/user_id/{user_id}", responses={
    200: {"description": "Friend requests retrieved successfully"},
    404: {"description": "User not found"}
})
async def get_friend_requests_for_me(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = (await session.execute(select(User).filter(User.id == user_id))).scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(Friendship).filter(Friendship.friend_id == user.id, Friendship.status == False)
    friend_requests = (await session.execute(stmt)).scalars().all()

    result_list = []
    for req in friend_requests:
        f_res = await session.execute(select(User).filter(User.id == req.user_id))
        friend = f_res.scalars().first()
        if friend:
            result_list.append(FriendRequest(
                id=req.id,
                user=UserResponse(**user.__dict__),
                friend=UserResponse(**friend.__dict__),
                status=req.status
            ))
    return result_list

@router.post("/update_request", responses={
    200: {"description": "Friend request updated successfully"},
    404: {"description": "Friend request not found"}
})
async def update_friend_request(data: UpdateFriendRequest, session: AsyncSession = Depends(get_db)):
    stmt = select(Friendship).filter(Friendship.id == data.request_id)
    friendship = (await session.execute(stmt)).scalars().first()

    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")

    if not data.status:
        await session.delete(friendship)
        detail = "Friend request deleted successfully"
    else:
        friendship.status = data.status
        detail = "Friend request updated successfully"
    
    await session.commit()
    return {"detail": detail}
    with SessionLocal() as session:
        friendship = session.query(Friendship).filter(Friendship.id == data.request_id).first()
        updated = False
        removed = False

        if not friendship:
            raise HTTPException(status_code=404, detail="Friend request not found")

        if not data.status:
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