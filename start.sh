#!/bin/bash
 
trap "kill 0" EXIT

if [ ! -d ".venv" ]; then
    python -m venv .venv
fi

source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

clear

if [ -f .env ]; then
    set -a
    source <(sed 's/\r$//' .env)
    set +a
else
    echo "Warning: .env file not found"
fi

CHESS_CORE_PORT=${CHESS_CORE_API_PORT:?CHESS_CORE_API_PORT is not set}
CHESS_CORE_PATH=${CHESS_CORE_API_PATH:?CHESS_CORE_API_PATH is not set}
API_URL="http://127.0.0.1:$CHESS_CORE_PORT"
START_FEN="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

dotnet "$CHESS_CORE_PATH" --urls "http://*:$CHESS_CORE_PORT" &

echo "Still waiting for ChessAPI..."
until curl -fsS \
    -H "Content-Type: application/json" \
    -d "{\"fen\":\"$START_FEN\",\"from\":\"e2\",\"to\":\"e4\",\"promoteTo\":\"q\"}" \
    "$API_URL/api/Chess/move" > /dev/null; do
    sleep 1
done

MAIN_API_PORT=${MAIN_API_PORT:?MAIN_API_PORT is not set}
uvicorn app:app --host 0.0.0.0 --port "$MAIN_API_PORT" --reload
