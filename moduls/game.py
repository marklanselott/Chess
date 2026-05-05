from responses import StartOpponentSearch as StartOpponentSearchResponse
from db.models import OpponentSearch, GameSessionStatus
from fastapi import APIRouter, HTTPException, Depends
from db.database import SessionLocal
from pydantic import BaseModel
from auth import verify_token
from enum import Enum

router = APIRouter(dependencies=[Depends(verify_token)])

@router.post("/search_opponent", responses={
    200: {"description": "Successfully started searching for opponent"},
    404: {"description": "User not found"}
}, response_model=StartOpponentSearchResponse)
async def search_opponent(user_id: str):
    with SessionLocal() as session:
        user = session.query(OpponentSearch).filter(OpponentSearch.user_id == user_id).first()
        if not user:
            user = OpponentSearch(user_id=user_id, status=GameSessionStatus.Searching)
            session.add(user)

        if user.status == GameSessionStatus.Searching:
            raise HTTPException(status_code=400, detail="Already searching for opponent")

        user.status = GameSessionStatus.Searching
        session.commit()

        return StartOpponentSearchResponse(
            id=user.id,
            user_id=user.user_id,
            status=user.status,
            oponent=user.oponent
        )

@router.post("/stop_search_opponent", responses={
    200: {"description": "Successfully stopped searching for opponent"},
    404: {"description": "User not found"}
})
async def stop_search_opponent(user_id: str):
    with SessionLocal() as session:
        user = session.query(OpponentSearch).filter(OpponentSearch.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=400, detail="Not currently searching for opponent")

        session.delete(user)
        session.commit()

        return {"message": "Stopped searching for opponent"}

# @router.get("/accepted_opponent", responses={
#     200: {"description": "Successfully got accepted opponent"},
#     404: {"description": "User not found or opponent not found"}
# }, response_model=OpponentSearchResponse)
# async def get_accepted_opponent(user_id: str):
#     """
#     >> user_id >> get accepted opponent
#     """
