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
    url = f"{base_url.rstrip('/')}/api/oponents/search/start"
    return requests.post(url, params={"user_id": user_id, "token": token}, timeout=10)

def await_opponent(token: str, user_id: str):
    url = f"{base_url.rstrip('/')}/api/oponents/await"
    try:
        with requests.get(url, params={"user_id": user_id, "token": token}, timeout=120, stream=True) as res:
            return res.json() if res.status_code == 200 else None
    except:
        return None

def stop_search_opponent(token: str, user_id: str):
    url = f"{base_url.rstrip('/')}/api/oponents/search/stop"
    return requests.post(url, params={"user_id": user_id, "token": token}, timeout=10)