from pathlib import Path
from uuid import uuid4
import atexit
import os
import subprocess
import time

from dotenv import load_dotenv
import httpx
import pytest

from .helpers import ApiClient


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

API_BASE = os.getenv("MAIN_API_BASE", f"http://127.0.0.1:{os.getenv('MAIN_API_PORT', '9538')}")
CHESS_CORE_BASE = os.getenv("CHESS_CORE_BASE", f"http://127.0.0.1:{os.getenv('CHESS_CORE_API_PORT', '4956')}")
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

_chess_core_process = None


def chess_core_is_available() -> bool:
    payload = {"fen": START_FEN, "from": "e2", "to": "e4"}
    try:
        response = httpx.post(f"{CHESS_CORE_BASE}/api/chess/move", json=payload, timeout=2)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def stop_started_chess_core():
    global _chess_core_process
    if _chess_core_process and _chess_core_process.poll() is None:
        _chess_core_process.terminate()
        try:
            _chess_core_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _chess_core_process.kill()
    _chess_core_process = None


@pytest.fixture(scope="session", autouse=True)
def ensure_chess_core():
    global _chess_core_process
    if chess_core_is_available():
        yield
        return

    chess_core_path = os.getenv("CHESS_CORE_API_PATH", "./chess_core/ChessAPI.dll")
    _chess_core_process = subprocess.Popen(
        ["dotnet", chess_core_path, "--urls", CHESS_CORE_BASE],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    atexit.register(stop_started_chess_core)

    for _ in range(20):
        if chess_core_is_available():
            break
        time.sleep(0.5)
    else:
        stop_started_chess_core()
        raise RuntimeError("Chess Core did not start")

    yield
    stop_started_chess_core()


@pytest.fixture(scope="session")
def api_base() -> str:
    return API_BASE


@pytest.fixture(scope="session")
def chess_core_base() -> str:
    return CHESS_CORE_BASE


@pytest.fixture(scope="session")
def start_fen() -> str:
    return START_FEN


@pytest.fixture(scope="session")
def token(api_base: str):
    response = httpx.post(
        f"{api_base}/api/auth/create-token",
        headers={"token": os.getenv("SECURE_TOKEN")},
        timeout=10,
    )
    assert response.status_code == 200, f"Failed to get token: {response.text}"
    return response.json()


@pytest.fixture(scope="session")
def api_client(api_base: str, token) -> ApiClient:
    return ApiClient(api_base, token)


@pytest.fixture(scope="session")
def test_users():
    run_id = uuid4().hex[:8]
    return {
        "max": {
            "unique": f"max_{run_id}",
            "email": f"max_{run_id}@example.com",
            "password": "secure_password",
            "first_name": "Max",
        },
        "john": {
            "unique": f"john_{run_id}",
            "email": f"john_{run_id}@example.com",
            "password": "secure_password",
            "first_name": "John",
        },
        "kate": {
            "unique": f"kate_{run_id}",
            "email": f"kate_{run_id}@example.com",
            "password": "secure_password",
            "first_name": "Kate",
        },
        "mate_white": {
            "unique": f"mate_white_{run_id}",
            "email": f"mate_white_{run_id}@example.com",
            "password": "secure_password",
            "first_name": "MateWhite",
        },
        "mate_black": {
            "unique": f"mate_black_{run_id}",
            "email": f"mate_black_{run_id}@example.com",
            "password": "secure_password",
            "first_name": "MateBlack",
        },
        "trio_one": {
            "unique": f"trio_one_{run_id}",
            "email": f"trio_one_{run_id}@example.com",
            "password": "secure_password",
            "first_name": "TrioOne",
        },
        "trio_two": {
            "unique": f"trio_two_{run_id}",
            "email": f"trio_two_{run_id}@example.com",
            "password": "secure_password",
            "first_name": "TrioTwo",
        },
        "trio_three": {
            "unique": f"trio_three_{run_id}",
            "email": f"trio_three_{run_id}@example.com",
            "password": "secure_password",
            "first_name": "TrioThree",
        },
    }


@pytest.fixture
def cleanup_test_users(api_client: ApiClient, test_users):
    for user in test_users.values():
        api_client.remove_user_if_exists(user)
    yield
    for user in test_users.values():
        api_client.remove_user_if_exists(user)
