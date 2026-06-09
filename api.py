from wsgiref import headers
import requests
from config import secureToken, base_url

def get_token():
    headers = {'token': secureToken}
    resp = requests.post(f'{base_url}/api/auth/create-token', headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.json()['jwt']

def reg_user(token: str, unique: str, first_name: str, password: str, tg_id: int):
    payload = {'unique': unique, 'first_name': first_name, 'password': password, 'tg_id': tg_id}
    params = {'token': token}
    return requests.post(f'{base_url}/api/user/register', params=params, json=payload)

def get_user(token: str, tg_id: int):
    payload = {'tg_id': tg_id}
    params = {'token': token}
    return requests.post(f'{base_url}/api/user/search/', params=params, json=payload).json()

def get_user_by_unique(token: str, unique: str):
    payload = {'unique': unique}
    params = {'token': token}
    resp = requests.post(f'{base_url}/api/user/search/', params=params, json=payload)
    data = resp.json()
    if data.get('searched') and len(data['searched']) > 0:
        return data['searched'][0]
    return None

def get_user_stats(token: str, user_uuid: str):
    """
    GET /api/user/stats/user_id/{user_uuid}
    Получить статистику по внутреннему UUID пользователя из БД
    """
    url = f"{base_url.rstrip('/')}/api/user/stats/user_id/{user_uuid}"
    params = {'token': token}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        return None

def update_user(token: str, user_id: str, payload: dict):
    params = {'token': token}
    return requests.post(f"{base_url.rstrip('/')}/api/user/update/user_id/{user_id}", params=params, json=payload)

def delete_user(token: str, unique: str, password: str):
    payload = {'unique': unique, 'password': password}
    params = {'token': token}
    return requests.post(f"{base_url.rstrip('/')}/api/user/remove", params=params, json=payload)

def get_friends_list(token: str, user_id: str):
    params = {'token': token}
    return requests.get(f"{base_url.rstrip('/')}/api/friends/get_list/user_id/{user_id}", params=params).json()

def get_friend_requests_for_me(token: str, user_id: str):
    params = {'token': token}
    resp = requests.get(f"{base_url.rstrip('/')}/api/friends/get_requests_for_me/user_id/{user_id}", params=params)
    return resp.json()

def get_friend_requests_my(token: str, user_id: str):
    params = {'token': token}
    resp = requests.get(f"{base_url.rstrip('/')}/api/friends/get_requests_my/user_id/{user_id}", params=params)
    return resp.json()

def send_friend_request(token: str, user_id: str, friend_unique: str):
    friend = get_user_by_unique(token, friend_unique)
    if not friend:
        return None
    payload = {'user_id': user_id, 'friend_id': friend.get('id')}
    params = {'token': token}
    return requests.post(f"{base_url.rstrip('/')}/api/friends/send_request", params=params, json=payload)

def delete_friend_from_api(token: str, user_uuid: str, friend_uuid: str):
    url = f"{base_url.rstrip('/')}/api/friends/friend"
    params = {'user_id': user_uuid, 'friend_id': friend_uuid, 'token': token}
    return requests.delete(url, params=params)

def update_friend_request(token: str, request_id: str, status: bool):
    payload = {'request_id': request_id, 'status': status}
    params = {'token': token}
    return requests.post(f"{base_url.rstrip('/')}/api/friends/update_request", params=params, json=payload)

def cancel_friend_request(token: str, request_id: str):
    params = {'token': token}
    return requests.get(f"{base_url.rstrip('/')}/api/friends/cancel_request/request_id/{request_id}", params=params)

def start_search_opponent(token: str, user_id: str):
    url = f"{base_url.rstrip('/')}/api/opponents/search/start"
    try:
        res = requests.post(url, params={'user_id': user_id, 'token': token}, timeout=10)
        return res
    except Exception as e:
        return None

def await_opponent(token: str, user_id: str, retries: int=5):
    """Long-polling запрос ожидания оппонента с агрессивной обработкой сетевых ошибок"""
    url = f"{base_url.rstrip('/')}/api/opponents/await"
    for attempt in range(retries):
        try:
            res = requests.get(url, params={'user_id': user_id, 'token': token}, timeout=120, stream=False)
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 404:
                return '404'
            else:
                return None
        except requests.exceptions.Timeout:
            return '404'
        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError, requests.exceptions.ContentDecodingError) as e:
            error_name = type(e).__name__
            if attempt < retries - 1:
                wait_time = 2 ** (attempt + 1)
                import time
                time.sleep(wait_time)
                continue
            else:
                return '404'
        except Exception as e:
            error_name = type(e).__name__
            return None
    return '404'

def stop_search_opponent(token: str, user_id: str):
    url = f"{base_url.rstrip('/')}/api/opponents/search/stop"
    try:
        res = requests.post(url, params={'user_id': user_id, 'token': token}, timeout=10)
        return res
    except Exception as e:
        return None

def get_game_board(token: str, game_id: str):
    url = f"{base_url.rstrip('/')}/api/game/game"
    try:
        res = requests.get(url, params={'game_id': game_id, 'token': token}, timeout=10)
        return res.json() if res.status_code == 200 else None
    except Exception as e:
        return None

def make_chess_move(token: str, game_id: str, from_to: str, promotion: str=None):
    """
    GET /api/game/move
    Сделать ход (передаем строку движения, например 'e2e4')
    promotion: 'q' для ферзя, 'r' для ладьи, 'b' для слона, 'n' для коня (опционально)
    """
    url = f"{base_url.rstrip('/')}/api/game/move"
    params = {'game_id': game_id, 'from_to': from_to, 'token': token}
    if promotion:
        params['promotion'] = promotion
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            try:
                return response.json()
            except Exception:
                return {'status': 'error', 'detail': response.text}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}

def start_ai_game(token, user_id, user_color='white', ai_difficulty=3):
    """
    POST /api/game/ai/start
    Запуск игры с ИИ
    """
    url = f"{base_url.rstrip('/')}/api/game/ai/start"
    params = {'user_id': user_id, 'user_color': user_color, 'ai_difficulty': ai_difficulty, 'token': token}
    try:
        response = requests.post(url, params=params, timeout=15)
        return response
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None

def make_ai_move(token, game_id):
    """
    POST /api/game/ai/move
    Запрос на ответный ход ИИ
    """
    url = f"{base_url.rstrip('/')}/api/game/ai/move"
    params = {'game_id': game_id, 'token': token}
    try:
        response = requests.post(url, params=params, timeout=20)
        return response
    except requests.exceptions.Timeout:
        return None
    except Exception as e:
        return None

def start_game_analysis(token, game_id, depth=3):
    """
    POST /api/game/analysis/start
    Исправленная версия: корректно достает jobId из ответа сервера
    """
    import requests
    url = f"{base_url.rstrip('/')}/api/game/analysis/start"
    params = {'game_id': str(game_id), 'depth': int(depth), 'token': str(token)}
    try:
        response = requests.post(url, params=params)
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and 'jobId' in data:
                    return str(data.get('jobId'))
                elif isinstance(data, dict) and 'job_id' in data:
                    return str(data.get('job_id'))
            except Exception:
                text_res = response.text.strip().replace('"', '').replace("'", '')
                return text_res
        else:
            try:
                return response.json()
            except Exception:
                return {'status': 'error', 'detail': f'Код сервера: {response.status_code}'}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}

def get_analysis_status(token, job_id):
    """GET /api/game/analysis/status/{job_id}"""
    import requests
    url = f"{base_url.rstrip('/')}/api/game/analysis/status/{str(job_id)}"
    params = {'token': str(token)}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            try:
                return response.json()
            except Exception:
                return response.text.strip().replace('"', '')
        else:
            try:
                return response.json()
            except Exception:
                return {'status': 'error', 'detail': f'Код сервера: {response.status_code}'}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}

def surrender_game(token: str, user_id: str):
    """
    POST /api/game/surrender
    Сдаться в текущей игре
    """
    url = f"{base_url.rstrip('/')}/api/game/surrender"
    params = {'user_id': user_id, 'token': token}
    try:
        response = requests.post(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        return None
