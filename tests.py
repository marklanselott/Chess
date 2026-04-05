from dotenv import load_dotenv; load_dotenv()
import httpx, os

test_user1 = {
    "unique": "max",
    "email": "max@example.com",
    "password": "secure_password",
   "first_name": "Max"
}

test_user2 = {
    "unique": "john",
    "email": "john@example.com",
    "password": "secure_password",
    "first_name": "John"
}


base = "http://127.0.0.1:9538"
# base = "http://5.161.254.136:9538"


class Auth:
    def get_token():
        url = f"{base}/api/auth/create-token"
        headers = {
            "token": os.getenv("SECURE_TOKEN")
        }
        response = httpx.post(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to get token: {response.text}")
        return response.json()

class User:
    def register_user(token: str, test_user: dict):
        url = f"{base}/api/user/register"

        payload = test_user
        params = {
            "token": token
        }
        
        response = httpx.post(url, json=payload, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to register user: {response.text}")
        return response.json()

    def search_user(token: str, key: str, value: str):
        url = f"{base}/api/user/search/"
        params = {
            "token": token
        }
        payload = {
            key: value
        }
        
        response = httpx.post(url, params=params, json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to search user: {response.text}")
        return response.json()

    def update_user(token: str, user_id: str, key: str, value: str):
        url = f"{base}/api/user/update/user_id/{user_id}"
        params = {
            "token": token
        }
        payload = {
            "user_id": user_id,
            key: value
        }
        
        response = httpx.post(url, params=params, json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to update user: {response.text}")
        return response.json()

    def remove_user(token: str, unique: str, password: str):
        url = f"{base}/api/user/remove"
        params = {
            "token": token
        }
        payload = {
            "unique": unique,
            "password": password
        }
        
        response = httpx.post(url, params=params, json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to remove user: {response.text}")
        return response.json()

    def test():
        print("\033[94m[STEP]\033[0m Tests User...")
        try:
            token = Auth.get_token()
            print("\033[92m[SUCCESS]\033[0m Token received")
        except Exception as e:
            raise Exception(f"Failed to get token")

        try:
            test_user = test_user1.copy()
            new_user = User.register_user(token, test_user)
            print("\033[92m[SUCCESS]\033[0m User registered")
        except Exception as e:
            raise Exception(f"Failed to register user")
        
        try:
            searched_user = User.search_user(token, "unique", test_user["unique"])
            print("\033[92m[SUCCESS]\033[0m User found")
        except Exception as e:
            raise Exception(f"Failed to search user")
        
        try:
            updated_user = User.update_user(token, new_user["id"], "email", "new_email@example.com")
            print("\033[92m[SUCCESS]\033[0m User updated")
        except Exception as e:
            raise Exception(f"Failed to update user")
        
        try:
            removed_user = User.remove_user(token, test_user["unique"], test_user["password"])
            print("\033[92m[SUCCESS]\033[0m User removed")
        except Exception as e:
            raise Exception(f"Failed to remove user")
        
        try:
            searched_user = User.search_user(token, "unique", test_user["unique"])
            print("\033[92m[SUCCESS]\033[0m Search complete")
        except Exception as e:
            raise Exception(f"Failed to search user")

class Friendship:
    def get_friends(token: str, user_id: str):
        url = f"{base}/api/friends/get_list/user_id/{user_id}"
        params = {
            "token": token
        }
        
        response = httpx.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to get friends: {response.text}")
        return response.json()
    
    def send_friend_request(token: str, user_id: str, friend_id: str):
        url = f"{base}/api/friends/send_friend_request"
        params = {
            "token": token
        }
        payload = {
            "user_id": user_id,
            "friend_id": friend_id
        }
        
        response = httpx.post(url, params=params, json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to send friend request: {response.text}")
        return response.json()

    def update_friend_request(token: str, request_id: str, accept: bool):
        url = f"{base}/api/friends/update_friend_request"
        params = {
            "token": token
        }
        payload = {
            "request_id": request_id,
            "status": accept
        }
        
        response = httpx.post(url, params=params, json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to update friend request: {response.text}")
        return response.json()

    def test():
        print("\033[94m[STEP]\033[0m Tests Friendship...")
        try:
            token = Auth.get_token()
            print("\033[92m[SUCCESS]\033[0m Token received")
        except Exception as e:
            raise Exception(f"Failed to get token")

        try:
            test_usr1 = User.register_user(token, test_user1)
            test_usr2 = User.register_user(token, test_user2)
            print("\033[92m[SUCCESS]\033[0m Users registered")
        except Exception as e:
            raise Exception(f"Failed to register users")

        try:
            friends = Friendship.get_friends(token, test_usr1["id"])
            print("\033[92m[SUCCESS]\033[0m List received")
        except Exception as e:
            raise Exception(f"Failed to get friends")

        try:
            friend_request = Friendship.send_friend_request(token, test_usr1["id"], test_usr2["id"])
            print("\033[92m[SUCCESS]\033[0m Request sent")
        except Exception as e:
            raise Exception(f"Failed to send friend request")

        try:
            accept_request = Friendship.update_friend_request(token, friend_request["id"], True)
            print("\033[92m[SUCCESS]\033[0m Request accepted")
        except Exception as e:
            raise Exception(f"Failed to accept friend request")

        try:
            accept_request = Friendship.update_friend_request(token, friend_request["id"], False)
            print("\033[92m[SUCCESS]\033[0m Request updated")
        except Exception as e:
            raise Exception(f"Failed to update friend request")


        try:
            User.remove_user(token, test_user1["unique"], test_user1["password"])
            User.remove_user(token, test_user2["unique"], test_user2["password"])
            print("\033[92m[SUCCESS]\033[0m Cleanup finished")
        except Exception as e:
            raise Exception(f"Failed cleanup")

if __name__ == "__main__":
    for module in [User, Friendship]:
        try: module.test()
        except Exception as e:
            print(f"\033[91m[ERROR]\033[0m {e}")

