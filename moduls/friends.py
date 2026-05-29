from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from auth import verify_token
from db.database import get_db
from db.models import Friendship, User
from requests import SendRequestFriend, UpdateFriendRequest
from responses import FriendRequest, User as UserResponse
from utils import get_user_or_404, setup_logger, user_to_response


router = APIRouter(dependencies=[Depends(verify_token)])
logger = setup_logger(__name__)


async def friendship_or_404(session: AsyncSession, request_id: UUID) -> Friendship:
    friendship = (
        await session.execute(select(Friendship).where(Friendship.id == request_id))
    ).scalar_one_or_none()
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")
    return friendship


async def friendship_response(session: AsyncSession, friendship: Friendship) -> FriendRequest:
    user = await get_user_or_404(session, friendship.user_id)
    friend = await get_user_or_404(session, friendship.friend_id)
    return FriendRequest(
        id=friendship.id,
        user=user_to_response(user),
        friend=user_to_response(friend),
        status=friendship.status,
    )


async def friendship_between(session: AsyncSession, user_id: UUID, friend_id: UUID) -> Friendship | None:
    return (
        await session.execute(
            select(Friendship).where(
                or_(
                    and_(Friendship.user_id == user_id, Friendship.friend_id == friend_id),
                    and_(Friendship.user_id == friend_id, Friendship.friend_id == user_id),
                )
            )
        )
    ).scalar_one_or_none()


@router.get("/list/user_id/{user_id}", response_model=list[UserResponse])
@router.get("/get_list/user_id/{user_id}", response_model=list[UserResponse])
async def get_friends_list(user_id: UUID, start: int = 0, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)
    friendships = (
        await session.execute(
            select(Friendship)
            .where(
                and_(
                    or_(Friendship.user_id == user.id, Friendship.friend_id == user.id),
                    Friendship.status == True,
                )
            )
            .offset(start)
            .limit(15)
        )
    ).scalars().all()

    friends = []
    for friendship in friendships:
        friend_id = friendship.friend_id if friendship.user_id == user.id else friendship.user_id
        friend = (await session.execute(select(User).where(User.id == friend_id))).scalar_one_or_none()
        if friend:
            friends.append(user_to_response(friend))
    return friends


@router.post("/requests", response_model=FriendRequest)
@router.post("/send_request", response_model=FriendRequest)
async def send_friend_request(data: SendRequestFriend, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, data.user_id)
    friend = await get_user_or_404(session, data.friend_id)

    if user.id == friend.id:
        raise HTTPException(status_code=400, detail="You cannot send a friend request to yourself")

    if await friendship_between(session, user.id, friend.id):
        raise HTTPException(status_code=400, detail="Friend request or friendship already exists")

    friendship = Friendship(user_id=user.id, friend_id=friend.id, status=False)
    session.add(friendship)
    await session.commit()
    await session.refresh(friendship)

    logger.info("Friend request sent: request_id=%s user_id=%s friend_id=%s", friendship.id, user.id, friend.id)
    return await friendship_response(session, friendship)


@router.get("/requests/sent/user_id/{user_id}", response_model=list[FriendRequest])
@router.get("/get_requests_my/user_id/{user_id}", response_model=list[FriendRequest])
async def get_sent_friend_requests(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)
    requests = (
        await session.execute(
            select(Friendship).where(Friendship.user_id == user.id, Friendship.status == False)
        )
    ).scalars().all()
    return [await friendship_response(session, item) for item in requests]


@router.get("/requests/incoming/user_id/{user_id}", response_model=list[FriendRequest])
@router.get("/get_requests_for_me/user_id/{user_id}", response_model=list[FriendRequest])
async def get_incoming_friend_requests(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)
    requests = (
        await session.execute(
            select(Friendship).where(Friendship.friend_id == user.id, Friendship.status == False)
        )
    ).scalars().all()
    return [await friendship_response(session, item) for item in requests]


@router.post("/requests/{request_id}/accept")
async def accept_friend_request(request_id: UUID, user_id: UUID, session: AsyncSession = Depends(get_db)):
    await get_user_or_404(session, user_id)
    friendship = await friendship_or_404(session, request_id)

    if friendship.friend_id != user_id or friendship.status:
        raise HTTPException(status_code=404, detail="Incoming friend request not found")

    friendship.status = True
    await session.commit()
    logger.info("Friend request accepted: request_id=%s user_id=%s", request_id, user_id)
    return {"detail": "Friend request accepted successfully"}


@router.delete("/requests/{request_id}/cancel")
@router.get("/cancel_request/request_id/{request_id}")
async def cancel_sent_friend_request(
    request_id: UUID,
    user_id: UUID | None = None,
    session: AsyncSession = Depends(get_db),
):
    friendship = await friendship_or_404(session, request_id)

    if friendship.status:
        raise HTTPException(status_code=404, detail="Sent friend request not found")
    if user_id is not None and friendship.user_id != user_id:
        raise HTTPException(status_code=404, detail="Sent friend request not found")

    await session.delete(friendship)
    await session.commit()
    logger.info("Friend request cancelled: request_id=%s user_id=%s", request_id, user_id)
    return {"detail": "Friend request cancelled successfully"}


@router.delete("/requests/{request_id}/decline")
async def decline_incoming_friend_request(request_id: UUID, user_id: UUID, session: AsyncSession = Depends(get_db)):
    await get_user_or_404(session, user_id)
    friendship = await friendship_or_404(session, request_id)

    if friendship.friend_id != user_id or friendship.status:
        raise HTTPException(status_code=404, detail="Incoming friend request not found")

    await session.delete(friendship)
    await session.commit()
    logger.info("Friend request declined: request_id=%s user_id=%s", request_id, user_id)
    return {"detail": "Friend request declined successfully"}


@router.delete("/friend")
async def remove_friend(user_id: UUID, friend_id: UUID, session: AsyncSession = Depends(get_db)):
    await get_user_or_404(session, user_id)
    await get_user_or_404(session, friend_id)
    friendship = await friendship_between(session, user_id, friend_id)

    if not friendship or not friendship.status:
        raise HTTPException(status_code=404, detail="Friendship not found")

    await session.delete(friendship)
    await session.commit()
    logger.info("Friendship removed: user_id=%s friend_id=%s", user_id, friend_id)
    return {"detail": "Friend removed successfully"}


@router.post("/update_request")
async def update_friend_request(data: UpdateFriendRequest, session: AsyncSession = Depends(get_db)):
    friendship = await friendship_or_404(session, data.request_id)

    if data.status:
        return await accept_friend_request(data.request_id, friendship.friend_id, session)

    if friendship.status:
        return await remove_friend(friendship.user_id, friendship.friend_id, session)

    await session.delete(friendship)
    await session.commit()
    logger.info("Friend request deleted: request_id=%s", data.request_id)
    return {"detail": "Friend request deleted successfully"}
