from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


ROOT = runtime_root()


def load_environment() -> None:
    env_paths = [Path.cwd() / ".env", ROOT / ".env", ROOT.parent / ".env"]
    seen = set()

    for path in env_paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        load_dotenv(resolved, override=False)


def api_base_url() -> str:
    return os.getenv("MAIN_API_BASE", f"http://5.161.254.136:9538")


def api_timeout() -> float:
    return float(os.getenv("MAIN_API_TIMEOUT", "130"))


def client_kwargs() -> dict:
    return {
        "timeout": api_timeout(),
        "limits": httpx.Limits(max_keepalive_connections=0),
        "headers": {"Connection": "close"},
    }


def format_api_connection_error(exc: httpx.HTTPError) -> str:
    return (
        f"API connection error: {exc}\n"
        "Check that the Python API is running and reachable."
    )


def request_json(response: httpx.Response, action: str) -> dict:
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"{action} failed: HTTP {response.status_code}\n{detail}")
    return response.json()


def create_token(client: httpx.Client, base_url: str) -> str:
    secure_token = os.getenv("SECURE_TOKEN")
    if not secure_token:
        raise RuntimeError("SECURE_TOKEN is missing in .env")

    response = client.post(
        f"{base_url}/api/auth/create-token",
        headers={"token": secure_token},
    )
    return request_json(response, "Create token")["jwt"]


def params(token: str, **extra) -> dict:
    return {"token": token, **extra}


def register_test_user(client: httpx.Client, base_url: str, token: str) -> dict:
    unique = f"terminal_board_{uuid4().hex[:8]}"
    response = client.post(
        f"{base_url}/api/user/register",
        params=params(token),
        json={
            "unique": unique,
            "first_name": "TerminalBoard",
            "password": "terminal_board_password",
            "email": f"{unique}@example.com",
        },
    )
    return request_json(response, "Register test user")


def remove_test_user(client: httpx.Client, base_url: str, token: str, unique: str) -> None:
    client.post(
        f"{base_url}/api/user/remove",
        params=params(token),
        json={"unique": unique, "password": "terminal_board_password"},
    )


def start_ai_game(
    client: httpx.Client,
    base_url: str,
    token: str,
    user_id: str,
    user_color: str,
    ai_difficulty: int,
) -> dict:
    response = client.post(
        f"{base_url}/api/game/ai/start",
        params=params(token, user_id=user_id, user_color=user_color, ai_difficulty=ai_difficulty),
    )
    return request_json(response, "Start AI game")


def get_game(client: httpx.Client, base_url: str, token: str, game_id: str) -> dict:
    response = client.get(
        f"{base_url}/api/game/game",
        params=params(token, game_id=game_id),
    )
    return request_json(response, "Get game")


def make_move(client: httpx.Client, base_url: str, token: str, game_id: str, move: str) -> dict:
    response = client.get(
        f"{base_url}/api/game/move",
        params=params(token, game_id=game_id, from_to=move),
    )
    return request_json(response, f"Move {move}")


def make_ai_move(client: httpx.Client, base_url: str, token: str, game_id: str) -> dict:
    response = client.post(
        f"{base_url}/api/game/ai/move",
        params=params(token, game_id=game_id),
    )
    return request_json(response, "AI move")


def ask_ai_difficulty(default_depth: int) -> int:
    default_depth = max(1, min(5, default_depth))

    while True:
        try:
            value = input(f"AI difficulty (1-5, Enter={default_depth})> ").strip()
        except EOFError:
            return default_depth

        if not value:
            return default_depth
        if value.isdigit() and 1 <= int(value) <= 5:
            return int(value)

        print("Use a number from 1 to 5.")


def fen_to_grid(fen: str) -> list[list[str]]:
    board_fen = fen.split()[0]
    rows = []

    for rank in board_fen.split("/"):
        row = []
        for char in rank:
            if char.isdigit():
                row.extend(["."] * int(char))
            else:
                row.append(char)
        rows.append(row)

    if len(rows) != 8 or any(len(row) != 8 for row in rows):
        raise RuntimeError(f"Invalid FEN board: {fen}")

    return rows


def print_board(fen: str) -> None:
    parts = fen.split()
    turn = "white" if len(parts) > 1 and parts[1] == "w" else "black"
    castling = parts[2] if len(parts) > 2 else "-"
    en_passant = parts[3] if len(parts) > 3 else "-"
    grid = fen_to_grid(fen)

    print()
    print(f"FEN: {fen}")
    print(f"Turn: {turn} | Castling: {castling} | En passant: {en_passant}")
    print()
    print("    a   b   c   d   e   f   g   h")
    print("  +---+---+---+---+---+---+---+---+")

    for index, row in enumerate(grid):
        rank = 8 - index
        cells = " | ".join(row)
        print(f"{rank} | {cells} | {rank}")
        print("  +---+---+---+---+---+---+---+---+")

    print("    a   b   c   d   e   f   g   h")
    print()


def print_game(client: httpx.Client, base_url: str, token: str, game_id: str) -> dict:
    game = get_game(client, base_url, token, game_id)
    print_board(game["game"]["board"]["fen"])
    return game


def print_move_result(move_result: dict) -> tuple[bool, bool]:
    chess_core = move_result.get("chess_core", {})
    from_to = move_result.get("from_to", [])

    if not chess_core.get("isLegal"):
        message = chess_core.get("message") or chess_core.get("Message") or "Illegal move"
        print(f"{message}. Board unchanged.")
        return False, False

    if len(from_to) == 2:
        print(f"Move: {from_to[0]} -> {from_to[1]}")

    print_board(move_result["game"]["board"]["fen"])

    if chess_core.get("isCheckmate"):
        print("Checkmate.")
        return True, True
    if chess_core.get("isDraw"):
        print("Draw.")
        return True, True
    if move_result.get("result"):
        print(f"Game finished: {move_result['result']['reason']}")
        return True, True

    return True, False


def run_interactive_loop(
    client: httpx.Client,
    base_url: str,
    token: str,
    game_id: str,
    auto_ai: bool,
) -> None:
    print("Enter moves like e2e4. Commands: ai, board, quit.")

    while True:
        command = input("move> ").strip().lower()
        if not command:
            continue
        if command in {"q", "quit", "exit"}:
            break
        if command in {"b", "board"}:
            try:
                print_game(client, base_url, token, game_id)
            except RuntimeError as exc:
                print(exc)
            except httpx.HTTPError as exc:
                print(format_api_connection_error(exc))
            continue

        try:
            if command == "ai":
                move_result = make_ai_move(client, base_url, token, game_id)
            else:
                move_result = make_move(client, base_url, token, game_id, command)
        except RuntimeError as exc:
            print(exc)
            continue
        except httpx.HTTPError as exc:
            print(format_api_connection_error(exc))
            continue

        move_was_legal, game_finished = print_move_result(move_result)
        if game_finished:
            break
        if command != "ai" and move_was_legal and auto_ai:
            try:
                print("AI is thinking...")
                ai_result = make_ai_move(client, base_url, token, game_id)
            except RuntimeError as exc:
                print(exc)
                continue
            except httpx.HTTPError as exc:
                print(format_api_connection_error(exc))
                continue

            _, game_finished = print_move_result(ai_result)
            if game_finished:
                break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show a chess board in terminal using the local Python API."
    )
    parser.add_argument("--base-url", default=api_base_url(), help="Python API base URL")
    parser.add_argument("--game-id", help="Show an existing game")
    parser.add_argument("--user-color", choices=["white", "black"], default="white")
    parser.add_argument("--move", help="Optional player move before rendering, for example e2e4")
    parser.add_argument("--ai-move", action="store_true", help="Ask AI to move before rendering")
    parser.add_argument("--depth", type=int, choices=range(1, 6), default=1, help="Default AI difficulty")
    parser.add_argument("--no-auto-ai", action="store_true", help="Do not ask AI to move after player moves")
    parser.add_argument("--once", action="store_true", help="Show the board once and exit")
    parser.add_argument("--keep", action="store_true", help="Keep the temporary user/game")
    return parser.parse_args()


def main() -> int:
    load_environment()
    args = parse_args()

    created_user = None
    token = None

    try:
        with httpx.Client(**client_kwargs()) as client:
            token = create_token(client, args.base_url)

            if args.game_id:
                game_id = args.game_id
            else:
                ai_depth = ask_ai_difficulty(args.depth)
                print(f"AI difficulty set to {ai_depth}.")
                created_user = register_test_user(client, args.base_url, token)
                game = start_ai_game(
                    client,
                    args.base_url,
                    token,
                    created_user["id"],
                    args.user_color,
                    ai_depth,
                )
                game_id = game["game"]["id"]
                print(f"Created temporary AI game: {game_id}")

            if args.move:
                move_result = make_move(client, args.base_url, token, game_id, args.move)
                move_was_legal, game_finished = print_move_result(move_result)
                if move_was_legal and not game_finished and not args.no_auto_ai and not args.ai_move:
                    print("AI is thinking...")
                    ai_result = make_ai_move(client, args.base_url, token, game_id)
                    print_move_result(ai_result)

            if args.ai_move:
                ai_result = make_ai_move(client, args.base_url, token, game_id)
                print_move_result(ai_result)

            if not args.move and not args.ai_move:
                print_game(client, args.base_url, token, game_id)

            if not args.once:
                run_interactive_loop(
                    client,
                    args.base_url,
                    token,
                    game_id,
                    auto_ai=not args.no_auto_ai,
                )

    except httpx.HTTPError as exc:
        print(format_api_connection_error(exc), file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print()
        print("Exiting.")
    finally:
        if created_user and token and not args.keep:
            try:
                with httpx.Client(**client_kwargs()) as client:
                    remove_test_user(client, args.base_url, token, created_user["unique"])
                print("Temporary user/game removed. Use --keep to leave it in the database.")
            except httpx.HTTPError as exc:
                print(f"Temporary cleanup failed: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
