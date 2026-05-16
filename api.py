import requests
from config import secureToken, base_url


def get_token():
    headers = {"token": secureToken}
    resp = requests.post(f"{base_url}/api/auth/create-token", headers=headers)
    resp.raise_for_status()
    return resp.json()["jwt"]


def reg_user(token: str, unique: str, first_name: str, password: str, tg_id: int):
    payload = {
        "unique": unique,
        "first_name": first_name,
        "password": password,
        "tg_id": tg_id,
    }
    params = {"token": token}
    return requests.post(f"{base_url}/api/user/register", params=params, json=payload)


def get_user(token: str, tg_id: int):
    payload = {"tg_id": tg_id}
    params = {"token": token}
    return requests.post(f"{base_url}/api/user/search/", params=params, json=payload).json()


def get_user_by_unique(token: str, unique: str):
    payload = {"unique": unique}
    params = {"token": token}
    resp = requests.post(f"{base_url}/api/user/search/", params=params, json=payload)
    data = resp.json()
    if data.get("searched") and len(data["searched"]) > 0:
        return data["searched"][0]
    return None


def update_user(token: str, user_id: str, payload: dict):
    params = {"token": token}
    return requests.post(f"{base_url.rstrip('/')}/api/user/update/user_id/{user_id}", params=params, json=payload)


def delete_user(token: str, unique: str, password: str):
    payload = {"unique": unique, "password": password}
    params = {"token": token}
    return requests.post(f"{base_url.rstrip('/')}/api/user/remove", params=params, json=payload)


def get_friends_list(token: str, user_id: str):
    params = {"token": token}
    return requests.get(f"{base_url.rstrip('/')}/api/friends/get_list/user_id/{user_id}", params=params).json()


def get_friend_requests_for_me(token: str, user_id: str):
    params = {"token": token}
    resp = requests.get(f"{base_url.rstrip('/')}/api/friends/get_requests_for_me/user_id/{user_id}", params=params)
    return resp.json()


def get_friend_requests_my(token: str, user_id: str):
    params = {"token": token}
    resp = requests.get(f"{base_url.rstrip('/')}/api/friends/get_requests_my/user_id/{user_id}", params=params)
    return resp.json()


def send_friend_request(token: str, user_id: str, friend_unique: str):
    friend = get_user_by_unique(token, friend_unique)
    if not friend:
        return None
    payload = {"user_id": user_id, "friend_id": friend.get("id")}
    params = {"token": token}
    return requests.post(f"{base_url.rstrip('/')}/api/friends/send_request", params=params, json=payload)


def update_friend_request(token: str, request_id: str, status: bool):
    payload = {"request_id": request_id, "status": status}
    params = {"token": token}
    return requests.post(f"{base_url.rstrip('/')}/api/friends/update_request", params=params, json=payload)


def cancel_friend_request(token: str, request_id: str):
    params = {"token": token}
    return requests.get(f"{base_url.rstrip('/')}/api/friends/cancel_request/request_id/{request_id}", params=params)


def start_search_opponent(token: str, user_id: str):
    url = f"{base_url.rstrip('/')}/api/opponents/search/start"
    try:
        return requests.post(url, params={"user_id": user_id, "token": token}, timeout=10)
    except Exception as e:
        print(f"Ошибка start_search_opponent: {e}")
        return None

def await_opponent(token: str, user_id: str):
    url = f"{base_url.rstrip('/')}/api/opponents/await"
    try:
        # УБРАЛИ stream=True, оставили чистый long-polling запрос
        res = requests.get(url, params={"user_id": user_id, "token": token}, timeout=60)
        
        if res.status_code == 200:
            return res.json()
        elif res.status_code == 404:
            return "404"  # Обязательно возвращаем строку, а не None!
            
        print(f"[API ДОКА] Сервер вернул код: {res.status_code}")
        return None
    except requests.exceptions.Timeout:
        # Если библиотека requests отвалилась по таймауту в 60 сек — это нормально для лонг-поллинга
        return "404"
    except Exception as e:
        print(f"Ошибка await_opponent: {e}")
        return None

def stop_search_opponent(token: str, user_id: str):
    url = f"{base_url.rstrip('/')}/api/opponents/search/stop"
    try:
        return requests.post(url, params={"user_id": user_id, "token": token}, timeout=10)
    except Exception as e:
        print(f"Ошибка stop_search_opponent: {e}")
        return None

def get_game_board(token: str, game_id: str):
    # Метод получения доски по game_id
    url = f"{base_url.rstrip('/')}/api/game/game"
    try:
        res = requests.get(url, params={"game_id": game_id, "token": token}, timeout=10)
        return res.json() if res.status_code == 200 else None
    except Exception as e:
        print(f"Ошибка get_game_board: {e}")
        return None


def make_chess_move(token: str, game_id: str, from_to: str):
    """
    GET /api/game/move
    Сделать ход (передаем строку движения, например 'e2e4')
    """
    url = f"{base_url.rstrip('/')}/api/game/move"
    params = {
        "game_id": game_id,
        "from_to": from_to,
        "token": token
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка GET /api/game/move [{response.status_code}]: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка сети в make_chess_move: {e}")
        return None


def surrender_game(token: str, user_id: str):
    """
    POST /api/game/surrender
    Сдаться в текущей игре
    """
    url = f"{base_url.rstrip('/')}/api/game/surrender"
    # Так как параметры передаются в Query (судя по схеме параметров Swagger), используем params вместо json/data
    params = {
        "user_id": user_id,
        "token": token
    }
    try:
        response = requests.post(url, params=params)
        if response.status_code == 200:
            return response.json()  # Или response.text, если там возвращается просто строка "Successfully surrendered"
        else:
            print(f"Ошибка POST /api/game/surrender [{response.status_code}]: {response.text}")
            return None
    except Exception as e:
        print(f"Ошибка сети в surrender_game: {e}")
        return None