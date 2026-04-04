if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

pip install --upgrade pip

pip install -r requirements.txt

clear

uvicorn app:app --host 0.0.0.0 --port 9538 --reload
# uvicorn app:app --host 0.0.0.0 --port 9358