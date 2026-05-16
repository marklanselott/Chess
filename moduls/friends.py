from requests import SendRequestFriend, UpdateFriendRequest
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from responses import User as UserResponse
from sqlalchemy import or_, and_
from db.models import Friendship, User
from sqlalchemy.future import select
from responses import FriendRequest
from auth import verify_token
from db.database import get_db
from utils import get_user_or_404, setup_logger, user_to_response
from uuid import UUID

router = APIRouter(dependencies=[Depends(verify_token)])
logger = setup_logger(__name__)


@router.get("/get_list/user_id/{user_id}", responses={
    200: {"description": "Successful get list of friends"},
    404: {"description": "User not found"}
}, response_model=list[UserResponse])
async def get_friends_list(user_id: UUID, start: int = 0, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)

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
            friends.append(user_to_response(friend))

    return friends


@router.post("/send_request", responses={
    200: {"description": "Friend request sent successfully"},
    400: {"description": "Friend request already exists or invalid request"},
    404: {"description": "User not found"}
}, response_model=FriendRequest)
async def send_friend_request(data: SendRequestFriend, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, data.user_id)
    friend = await get_user_or_404(session, data.friend_id)

    if user.id == friend.id:
        raise HTTPException(status_code=400, detail="You cannot send a friend request to yourself")

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
    logger.info("Friend request sent: request_id=%s user_id=%s friend_id=%s", new_request.id, user.id, friend.id)

    return FriendRequest(
        id=new_request.id,
        user=user_to_response(user),
        friend=user_to_response(friend),
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
    logger.info("Friend request cancelled: request_id=%s", request_id)

    return {"detail": "Friend request cancelled successfully"}


@router.get("/get_requests_my/user_id/{user_id}", responses={
    200: {"description": "Friend requests retrieved successfully"},
    404: {"description": "User not found"}
}, response_model=list[FriendRequest])
async def get_friend_requests(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)

    stmt = select(Friendship).filter(Friendship.user_id == user.id, Friendship.status == False)
    friend_requests = (await session.execute(stmt)).scalars().all()

    result_list = []
    for req in friend_requests:
        friend = await get_user_or_404(session, req.friend_id)
        result_list.append(FriendRequest(
            id=req.id,
            user=user_to_response(user),
            friend=user_to_response(friend),
            status=req.status
        ))

    return result_list


@router.get("/get_requests_for_me/user_id/{user_id}", responses={
    200: {"description": "Friend requests retrieved successfully"},
    404: {"description": "User not found"}
}, response_model=list[FriendRequest])
async def get_friend_requests_for_me(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)

    stmt = select(Friendship).filter(Friendship.friend_id == user.id, Friendship.status == False)
    friend_requests = (await session.execute(stmt)).scalars().all()

    result_list = []
    for req in friend_requests:
        friend = await get_user_or_404(session, req.user_id)
        result_list.append(FriendRequest(
            id=req.id,
            user=user_to_response(friend),
            friend=user_to_response(user),
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

    await get_user_or_404(session, friendship.user_id)
    await get_user_or_404(session, friendship.friend_id)

    if not data.status:
        await session.delete(friendship)
        detail = "Friend request deleted successfully"
    else:
        friendship.status = data.status
        detail = "Friend request updated successfully"

    await session.commit()
    logger.info("Friend request updated: request_id=%s status=%s", data.request_id, data.status)

    return {"detail": detail}
