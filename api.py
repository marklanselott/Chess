import requests
from config import secureToken, base_url

def get_token():
    headers = {
        "token": secureToken
    }
    resp = requests.post(f"{base_url}/api/auth/create-token", headers=headers)
    data = resp.json()
    return data["jwt"]

def reg_user(token:str, unique:str, first_name:str, password:str, tg_id:int):
    payload = {
        "unique": unique,
        "first_name": first_name,
        "password": password,
        "tg_id": tg_id
        
    }
    # print(payload)
    params = {
        "token": token
    }
    resp = requests.post(f"{base_url}/api/user/register", params=params, json=payload)
    # print(resp.json())

def get_user(token:str, tg_id:int):
    payload = {
        "tg_id": tg_id
    }
    params = {
        "token": token
    }

    resp = requests.post(f"{base_url}/api/user/search/", params=params, json=payload)
    data = resp.json()
    return data

def get_user_by_unique(token: str, unique: str):
    payload = {"unique": unique}
    params = {"token": token}
    resp = requests.post(f"{base_url}/api/user/search/", params=params, json=payload)
    data = resp.json()
    
    if data.get("searched") and len(data["searched"]) > 0:
        return data["searched"][0]
    return None
    


# token = get_token()
# print(token)
# print(reg_user(token,"Dane4ka", "Danya", "Debik", "Eblanovi4", "dimasex", 88005553535, "danyasuka@gmail.com", 0))