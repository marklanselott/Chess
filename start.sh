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
    source .env
    set +a
else
    echo "Warning: .env file not found"
fi

CHESS_CORE_PORT=${CHESS_CORE_API_PORT}
CHESS_CORE_PATH=${CHESS_CORE_API_PATH}
API_URL="http://127.0.0.1:$CHESS_CORE_PORT"

dotnet "$CHESS_CORE_PATH" --urls "http://*:$CHESS_CORE_PORT" &

echo "Still waiting for ChessAPI..."
while ! curl -s "$API_URL" > /dev/null; do
    sleep 1
done

MAIN_API_PORT=${MAIN_API_PORT}
uvicorn app:app --host 0.0.0.0 --port $MAIN_API_PORT --reload