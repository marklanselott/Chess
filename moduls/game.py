from responses import Game as GameResponse, SearchedOpponent
from httpx import AsyncClient, ConnectError, RequestError
from fastapi import APIRouter, Depends, HTTPException, Query
from responses import GameMove as GameMoveResponse
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import GameSessionStatus, GameMove, Games, OpponentSearch, UserColor
from sqlalchemy.future import select
from db.database import get_db
from auth import verify_token
from utils import (
    apply_game_draw,
    apply_game_result,
    clear_game_sessions,
    get_game_or_404,
    get_last_move_or_404,
    get_or_create_ai_user,
    get_user_or_404,
    setup_logger,
    user_to_response,
)
from uuid import UUID, uuid4
import os

base_url = f"http://127.0.0.1:{os.getenv('CHESS_CORE_API_PORT', '4956')}"

router = APIRouter(dependencies=[Depends(verify_token)])
logger = setup_logger(__name__)

class Convert:
    def fen_to_json(fen: str) -> dict:
        parts = fen.split()
        board_fen = parts[0]
        turn = parts[1]
        castling = parts[2]
        en_passant = parts[3]
        halfmove_clock = int(parts[4])
        fullmove_number = int(parts[5])
        board = {}

        for rank_index, row in enumerate(board_fen.split("/")):
            rank = 8 - rank_index
            file_index = 0

            for char in row:
                if char.isdigit():
                    file_index += int(char)
                    continue

                file = chr(ord("a") + file_index)
                board.setdefault(char, []).append(f"{file}{rank}")
                file_index += 1
        
        return {
            "board": board,
            "turn": turn,
            "castling": castling,
            "en_passant": en_passant,
            "halfmove_clock": halfmove_clock,
            "fullmove_number": fullmove_number
        }
    
    def json_to_fen(data: dict) -> str:
        board = data["board"]
        rows = []

        for rank in range(8, 0, -1):
            empty = 0
            row = ""

            for file in "abcdefgh":
                position = f"{file}{rank}"
                piece = None

                for board_piece, positions in board.items():
                    if position in positions:
                        piece = board_piece
                        break

                if piece:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += piece
                else:
                    empty += 1

            if empty:
                row += str(empty)

            rows.append(row)

        turn = data["turn"]
        castling = data["castling"]
        en_passant = data["en_passant"]
        halfmove_clock = str(data["halfmove_clock"])
        fullmove_number = str(data["fullmove_number"])
        
        return f"{'/'.join(rows)} {turn} {castling} {en_passant} {halfmove_clock} {fullmove_number}"

class Game:
    def board() -> GameResponse.Board:
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        return GameResponse.Board(fen=fen, json=Convert.fen_to_json(fen))
    
    def move_fix(from_to: str) -> list[str, str]:
        from_to = from_to.lower().replace(" ", "")
        from_ = "".join(sorted(from_to[:2]))[::-1]
        to_ = "".join(sorted(from_to[2:]))[::-1]
        return from_, to_

    async def move(board: GameResponse.Board, from_: str, to_: str) -> dict:
        async with AsyncClient() as client:
            json={"fen": board.fen, "from": from_, "to": to_}
            response = await client.post(f"{base_url}/api/chess/move", json=json)

            if response.status_code >= 400:
                raise HTTPException(status_code=400, detail=response.text)
            return response.json()

    async def bot_move(board: GameResponse.Board, depth: int) -> dict:
        async with AsyncClient() as client:
            json={"fen": board.fen, "depth": depth}
            response = await client.post(f"{base_url}/api/chess/bot-move", json=json)

            if response.status_code >= 400:
                raise HTTPException(status_code=400, detail=response.text)
            return response.json()


def get_payload_value(payload: dict, camel_case: str, pascal_case: str, default=None):
    return payload.get(camel_case, payload.get(pascal_case, default))


def turn_to_user_color(fen: str) -> UserColor:
    return UserColor.WHITE if fen.split()[1] == "w" else UserColor.BLACK


def participant_color(game, user_id: UUID) -> UserColor | None:
    if game.white_id == user_id:
        return UserColor.WHITE
    if game.black_id == user_id:
        return UserColor.BLACK
    return None


def game_ai_difficulty(game) -> int:
    difficulty = game.ai_difficulty or 3
    return max(1, min(5, int(difficulty)))

@router.get("/game", responses={
    200: {"description": "Get current chess board state"},
    400: {"description": "Invalid game ID"},
    404: {"description": "Game not found"}
}, response_model=SearchedOpponent)
async def get_board(game_id: UUID, session: AsyncSession = Depends(get_db)):
    game = await get_game_or_404(session, game_id)
    move = await get_last_move_or_404(session, game_id)
    white = await get_user_or_404(session, game.white_id)
    black = await get_user_or_404(session, game.black_id)

    return SearchedOpponent(
        user=user_to_response(white),
        opponent=user_to_response(black),
        game=GameResponse(
            id=game_id,
            white=game.white_id,
            black=game.black_id,
            ai_difficulty=game.ai_difficulty,
            board=GameResponse.Board(
                fen=move.fen,
                json=Convert.fen_to_json(move.fen)
            )
        )
    )

@router.post("/ai/start", responses={
    200: {"description": "Successfully started game with AI"},
    400: {"description": "User is already searching or in game"},
    404: {"description": "User not found"}
}, response_model=SearchedOpponent)
async def start_ai_game(
    user_id: UUID,
    user_color: UserColor = UserColor.WHITE,
    ai_difficulty: int = Query(default=3, ge=1, le=5),
    session: AsyncSession = Depends(get_db)
):
    user = await get_user_or_404(session, user_id)
    active_session = (await session.execute(
        select(OpponentSearch).where(OpponentSearch.user_id == user_id)
    )).scalar_one_or_none()

    if active_session:
        cases = {
            GameSessionStatus.Searching: "You are already searching for an opponent.",
            GameSessionStatus.InGame: "While you are in the game, you cannot start a game with AI."
        }
        raise HTTPException(
            status_code=400,
            detail=cases.get(active_session.status, f"Unknown status >>> {active_session.status}")
        )

    ai_user = await get_or_create_ai_user(session)
    if ai_user.id == user.id:
        raise HTTPException(status_code=400, detail="AI user cannot start a game with itself")

    game_id = uuid4()
    board = Game.board()

    if user_color == UserColor.WHITE:
        white_id = user.id
        black_id = ai_user.id
    else:
        white_id = ai_user.id
        black_id = user.id

    session.add(Games(
        id=game_id,
        white_id=white_id,
        black_id=black_id,
        ai_difficulty=ai_difficulty
    ))
    await session.flush()

    session.add(GameMove(
        game_id=game_id,
        fen=board.fen,
        step=0
    ))
    session.add(OpponentSearch(
        user_id=user.id,
        rating=user.rating,
        status=GameSessionStatus.InGame,
        game_id=game_id
    ))
    await session.commit()

    logger.info(
        "AI game started: game_id=%s user_id=%s ai_user_id=%s difficulty=%s",
        game_id,
        user.id,
        ai_user.id,
        ai_difficulty,
    )

    return SearchedOpponent(
        user=user_to_response(user),
        opponent=user_to_response(ai_user),
        game=GameResponse(
            id=game_id,
            white=white_id,
            black=black_id,
            ai_difficulty=ai_difficulty,
            board=board
        )
    )

@router.get("/move", responses={
    200: {"description": "Successfully made a move"},
    400: {"description": "Invalid move or game ID"},
    404: {"description": "Game not found"}
}, response_model=GameMoveResponse)
async def move_piece(game_id: UUID, from_to: str, session: AsyncSession = Depends(get_db)):
    try:
        game = await get_game_or_404(session, game_id)
        if game.result:
            raise HTTPException(status_code=400, detail="Game already finished")

        last_move = await get_last_move_or_404(session, game_id)
        moving_color = last_move.fen.split()[1]
        result = None

        board = GameResponse.Board(
            fen=last_move.fen,
            json=Convert.fen_to_json(last_move.fen)
        )
        fixed_move = Game.move_fix(from_to)
        chess_core = await Game.move(board, *fixed_move)
        if chess_core.get('newFen') is not None:
            board = GameResponse.Board(
                fen=chess_core['newFen'],
                json=Convert.fen_to_json(chess_core['newFen'])
            )
            session.add(GameMove(
                game_id=game_id,
                fen=board.fen,
                step=last_move.step + 1
            ))
            if chess_core.get("isLegal") and chess_core.get("isCheckmate"):
                winner_id = game.white_id if moving_color == "w" else game.black_id
                loser_id = game.black_id if moving_color == "w" else game.white_id
                winner = await get_user_or_404(session, winner_id)
                loser = await get_user_or_404(session, loser_id)
                result = await apply_game_result(session, game, winner, loser, reason="checkmate")
                await clear_game_sessions(session, game_id)
                logger.info(
                    "Game finished by checkmate: game_id=%s winner_id=%s loser_id=%s winner_delta=%s loser_delta=%s",
                    game_id,
                    winner_id,
                    loser_id,
                    result.winner.delta,
                    result.loser.delta,
                )
            elif chess_core.get("isLegal") and chess_core.get("isDraw"):
                await apply_game_draw(session, game, reason="draw")
                await clear_game_sessions(session, game_id)
                logger.info("Game finished by draw: game_id=%s", game_id)
        await session.commit()
        logger.info("Move processed: game_id=%s from_to=%s", game_id, fixed_move)

        if "newFen" in chess_core:
            del chess_core["newFen"] 

        return GameMoveResponse(
            chess_core=chess_core,
            from_to=list(fixed_move),
            game=GameResponse(
                id=game_id,
                white=game.white_id,
                black=game.black_id,
                ai_difficulty=game.ai_difficulty,
                board=board
            ),
            result=result
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        logger.error("Error in move_piece: %s", error_msg)
        raise HTTPException(status_code=400, detail=str(e) + "\n" + error_msg)

@router.post("/ai/move", responses={
    200: {"description": "Successfully made an AI move"},
    400: {"description": "Invalid game ID or AI move request"},
    404: {"description": "Game not found"}
}, response_model=GameMoveResponse)
async def move_ai(
    game_id: UUID,
    session: AsyncSession = Depends(get_db)
):
    try:
        game = await get_game_or_404(session, game_id)
        if game.result:
            raise HTTPException(status_code=400, detail="Game already finished")

        ai_user = await get_or_create_ai_user(session)
        ai_color = participant_color(game, ai_user.id)
        if ai_color is None:
            raise HTTPException(status_code=400, detail="Game is not an AI game")

        last_move = await get_last_move_or_404(session, game_id)
        moving_color = turn_to_user_color(last_move.fen)
        if moving_color != ai_color:
            raise HTTPException(status_code=400, detail="It is not AI's turn")

        board = GameResponse.Board(
            fen=last_move.fen,
            json=Convert.fen_to_json(last_move.fen)
        )
        ai_difficulty = game_ai_difficulty(game)
        bot_response = await Game.bot_move(board, ai_difficulty)
        new_fen = get_payload_value(bot_response, "newFen", "NewFen")
        move_from = get_payload_value(bot_response, "moveFrom", "MoveFrom")
        move_to = get_payload_value(bot_response, "moveTo", "MoveTo")

        if not new_fen or not move_from or not move_to:
            raise HTTPException(status_code=400, detail=f"Chess core returned an invalid AI move: {bot_response}")

        board = GameResponse.Board(
            fen=new_fen,
            json=Convert.fen_to_json(new_fen)
        )
        session.add(GameMove(
            game_id=game_id,
            fen=board.fen,
            step=last_move.step + 1
        ))

        chess_core = {
            "isLegal": True,
            "moveFrom": move_from,
            "moveTo": move_to,
            "isCheck": bool(get_payload_value(bot_response, "isCheck", "IsCheck", False)),
            "isCheckmate": bool(get_payload_value(bot_response, "isCheckmate", "IsCheckmate", False)),
            "isDraw": bool(get_payload_value(bot_response, "isDraw", "IsDraw", False)),
        }
        result = None

        if chess_core["isCheckmate"]:
            winner_id = game.white_id if moving_color == UserColor.WHITE else game.black_id
            loser_id = game.black_id if moving_color == UserColor.WHITE else game.white_id
            winner = await get_user_or_404(session, winner_id)
            loser = await get_user_or_404(session, loser_id)
            result = await apply_game_result(session, game, winner, loser, reason="checkmate")
            await clear_game_sessions(session, game_id)
            logger.info(
                "AI game finished by checkmate: game_id=%s winner_id=%s loser_id=%s",
                game_id,
                winner_id,
                loser_id,
            )
        elif chess_core["isDraw"]:
            await apply_game_draw(session, game, reason="draw")
            await clear_game_sessions(session, game_id)
            logger.info("AI game finished by draw: game_id=%s", game_id)

        await session.commit()
        logger.info(
            "AI move processed: game_id=%s from_to=%s difficulty=%s",
            game_id,
            [move_from, move_to],
            ai_difficulty,
        )

        return GameMoveResponse(
            chess_core=chess_core,
            from_to=[move_from, move_to],
            game=GameResponse(
                id=game_id,
                white=game.white_id,
                black=game.black_id,
                ai_difficulty=game.ai_difficulty,
                board=board
            ),
            result=result
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        logger.error("Error in move_ai: %s", error_msg)
        raise HTTPException(status_code=400, detail=str(e) + "\n" + error_msg)

@router.post("/surrender", responses={
    200: {"description": "Successfully surrendered"},
    400: {"description": "User is not in game"},
    404: {"description": "Opponent search not found"}
})
async def surrender(user_id: UUID, session: AsyncSession = Depends(get_db)):
    user = await get_user_or_404(session, user_id)

    user_search = (await session.execute(
        select(OpponentSearch).where(OpponentSearch.user_id == user_id)
    )).scalar_one_or_none()

    if not user_search:
        raise HTTPException(status_code=404, detail="Opponent search not found")

    if user_search.status != GameSessionStatus.InGame or not user_search.game_id:
        raise HTTPException(status_code=400, detail="User is not in game")

    game_id = user_search.game_id
    game = await get_game_or_404(session, game_id)
    if game.result:
        await clear_game_sessions(session, game_id)
        await session.commit()
        raise HTTPException(status_code=400, detail="Game already finished")

    if game.white_id == user_id:
        opponent_id = game.black_id
    elif game.black_id == user_id:
        opponent_id = game.white_id
    else:
        raise HTTPException(status_code=400, detail="User is not a game participant")

    opponent = await get_user_or_404(session, opponent_id)
    result = await apply_game_result(
        session,
        game,
        winner=opponent,
        loser=user,
        reason="surrender",
        loser_penalty_range=(45, 55),
    )
    await clear_game_sessions(session, game_id)

    await session.commit()
    logger.info(
        "Game surrendered: game_id=%s user_id=%s opponent_id=%s winner_delta=%s loser_delta=%s",
        game_id,
        user_id,
        opponent_id,
        result.winner.delta,
        result.loser.delta,
    )

    return {
        "detail": "Game closed",
        "game": game_id,
        "user": user_id,
        "opponent": opponent_id,
        "result": result,
    }
