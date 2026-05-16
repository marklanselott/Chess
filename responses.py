from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from uuid import UUID

class CreateToken(BaseModel):
    jwt: str
    exp: int

class User(BaseModel):
    id: UUID
    unique: str
    first_name: str  | None
    middle_name: str | None
    last_name: str   | None
    phone: int       | None
    email: str       | None
    tg_id: int       | None
    rating: int
    registryed_at: datetime

class FriendRequest(BaseModel):
    id: UUID
    user: User
    friend: User
    status: bool

class SearchUser(BaseModel):
    searched: list[User]
    start: int
    limit: int


class UserStats(BaseModel):
    user: User
    games_total: int
    games_finished: int
    games_active: int
    wins: int
    losses: int
    draws: int
    win_loss_ratio: float | None
    win_rate: float
    rating: int

class StartOpponentSearch(BaseModel):
    user: User
    opponent: User | None = None

class Game(BaseModel):
    class Board(BaseModel):
        model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

        fen: str
        state: dict = Field(alias="json")

    id: UUID
    white: UUID
    black: UUID
    board: Board
    ai_difficulty: int | None = None

class SearchedOpponent(BaseModel):
    game: Game | None = None
    user: User
    opponent: User | None = None


class RatingChange(BaseModel):
    user_id: UUID
    before: int
    after: int
    delta: int


class GameResult(BaseModel):
    reason: str
    winner: RatingChange
    loser: RatingChange


class GameMove(BaseModel):
    chess_core: dict
    from_to: list[str]
    game: Game
    result: GameResult | None = None

