from moduls.friends import router as friends_router
from moduls.user import router as user_router
from moduls.game import router as game_router
from auth import router as auth_router
from fastapi import FastAPI, APIRouter
from db import init

api = APIRouter(prefix="/api")
app = FastAPI()

api.include_router(friends_router, prefix="/friends")
api.include_router(auth_router, prefix="/auth")
api.include_router(user_router, prefix="/user")
api.include_router(game_router, prefix="/game")
app.include_router(api)

@app.get("/health")
@app.get("/")
def health_check():
    return {"status": "ok"}