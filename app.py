from moduls.opponents import router as opponents_router
from moduls.friends import router as friends_router
from fastapi.responses import RedirectResponse
from moduls.game import router as game_router
from moduls.user import router as user_router
from contextlib import asynccontextmanager
from auth import router as auth_router
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError, StatementError
from db import init
from utils import setup_logger
import os, httpx



from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse

api = APIRouter(prefix="/api")
logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init.init_models()
    logger.info("Application startup complete")
    yield

app = FastAPI(lifespan=lifespan)


@app.exception_handler(DataError)
@app.exception_handler(StatementError)
async def database_input_error_handler(request: Request, exc: Exception):
    logger.warning("Invalid database input on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request data"},
    )

api.include_router(opponents_router, prefix="/opponents")
api.include_router(friends_router, prefix="/friends")
api.include_router(auth_router, prefix="/auth")
api.include_router(game_router, prefix="/game")
api.include_router(user_router, prefix="/user")
app.include_router(api)

@app.get("/health")
@app.get("/")
def health_check():
    return {"status": "ok"}
