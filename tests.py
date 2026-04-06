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

    def get_user(token: str, user_id: str):
        url = f"{base}/api/user/user_id/{user_id}"
        params = {
            "token": token
        }
        response = httpx.get(url, params=params)
        assert response.status_code == 200, f"Failed to get user: {response.text}"
        return response.json()

    def test():
        old_user = test_user1.copy()
        user = User.register_user(Auth.get_token(), old_user)
        try:
            search = User.search_user(Auth.get_token(), "unique", user["unique"])
            assert search['searched'][0]["id"] == user["id"], "User not found in search"
            print("\033[92m[SUCCESS]\033[0m User registered and found in search")
            user_in_geted = User.get_user(Auth.get_token(), user["id"])
            assert user_in_geted["id"] == user["id"], "User not found in get user"
            print("\033[92m[SUCCESS]\033[0m User found in get user")
            updated_user = User.update_user(Auth.get_token(), user["id"], "email", "new_email@example.com")
            assert updated_user["email"] == "new_email@example.com", "User email not updated"
            print("\033[92m[SUCCESS]\033[0m User updated")
            User.remove_user(Auth.get_token(), user["unique"], old_user["password"])
            search_after_removal = User.search_user(Auth.get_token(), "unique", user["unique"])
            assert search_after_removal["searched"] == [], "User not removed properly"
            print("\033[92m[SUCCESS]\033[0m User removed properly")
        except Exception as e: raise e
        finally:
            try: User.remove_user(Auth.get_token(), old_user["unique"], old_user["password"])
            except: pass

class Friendship:
    def get_list(token: str, user_id: str):
        url = f"{base}/api/friends/get_list/user_id/{user_id}"
        params = {
            "token": token
        }
        
        response = httpx.get(url, params=params)
        assert response.status_code == 200, f"Failed to get friends: {response.text}"
        return response.json()
    
    def send_request(token: str, user_id: str, friend_id: str):
        url = f"{base}/api/friends/send_request"
        params = {
            "token": token
        }
        payload = {
            "user_id": user_id,
            "friend_id": friend_id
        }
        
        response = httpx.post(url, params=params, json=payload)
        assert response.status_code == 200, f"Failed to send friend request: {response.text}"
        return response.json()

    def update_request(token: str, request_id: str, accept: bool):
        url = f"{base}/api/friends/update_request"
        params = {
            "token": token
        }
        payload = {
            "request_id": request_id,
            "status": accept
        }
        
        response = httpx.post(url, params=params, json=payload)
        assert response.status_code == 200, f"Failed to update friend request: {response.text}"
        return response.json()

    def get_requests(token: str, user_id: str):
        url = f"{base}/api/friends/get_requests_for_me/user_id/{user_id}"
        params = {
            "token": token
        }
        response = httpx.get(url, params=params)
        assert response.status_code == 200, f"Failed to get friend requests: {response.text}"
        return response.json()
    
    def get_requests_my(token: str, user_id: str):
        url = f"{base}/api/friends/get_requests_my/user_id/{user_id}"
        params = {
            "token": token
        }
        response = httpx.get(url, params=params)
        assert response.status_code == 200, f"Failed to get my friend requests: {response.text}"
        return response.json()
    
    def cancel_request(token: str, request_id: str):
        url = f"{base}/api/friends/cancel_request/request_id/{request_id}"
        params = {
            "token": token
        }
        response = httpx.get(url, params=params)
        assert response.status_code == 200, f"Failed to cancel friend request: {response.text}"
        return response.json()

    def test():
        token = Auth.get_token()
        
        # Cleanup potential leftovers before starting
        try: User.remove_user(token, test_user1["unique"], test_user1["password"])
        except: pass
        try: User.remove_user(token, test_user2["unique"], test_user2["password"])
        except: pass

        # 1. Register two users
        user1 = User.register_user(token, test_user1)
        user2 = User.register_user(token, test_user2)
        print(f"\033[92m[SUCCESS]\033[0m Users {user1['unique']} and {user2['unique']} registered")

        try:
            # 2. Test sending a request (отправка запроса)
            request = Friendship.send_request(token, user1["id"], user2["id"])
            assert request["friend_id"] == user2["id"], "Friend request failed"
            print("\033[92m[SUCCESS]\033[0m Friend request sent")

            # 3. Test viewing requests (просмотр запросов)
            # Check requests for me (полученные)
            requests_for_me = Friendship.get_requests(token, user2["id"])
            assert any(r["id"] == request["id"] for r in requests_for_me), "Request not found in recipient's 'for_me' list"
            print("\033[92m[SUCCESS]\033[0m Request found in recipient's 'for_me' list")

            # Check my requests (отправленные)
            requests_my = Friendship.get_requests_my(token, user1["id"])
            assert any(r["id"] == request["id"] for r in requests_my), "Request not found in sender's 'my' list"
            print("\033[92m[SUCCESS]\033[0m Request found in sender's 'my' list")

            # 4. Test confirming a request (подтверждение запроса)
            Friendship.update_request(token, request["id"], True)
            friends_list = Friendship.get_list(token, user2["id"])
            assert any(f["id"] == user1["id"] for f in friends_list), "Friend not found in list after confirmation"
            print("\033[92m[SUCCESS]\033[0m Friend request confirmed and verified")

            # 5. Test cancelling a request (отмена запроса)
            # IMPORTANT: Remove the existing confirmed friendship first, as friends.py 
            # prevents creating a new request if any friendship/request already exists.
            Friendship.update_request(token, request["id"], False) 
            
            # Create a new request to cancel it
            request_to_cancel = Friendship.send_request(token, user2["id"], user1["id"])
            Friendship.cancel_request(token, request_to_cancel["id"])
            requests_after_cancel = Friendship.get_requests(token, user1["id"])
            assert not any(r["id"] == request_to_cancel["id"] for r in requests_after_cancel), "Request still exists after cancellation"
            print("\033[92m[SUCCESS]\033[0m Friend request cancelled successfully")

        finally:
            # Cleanup users
            User.remove_user(token, test_user1["unique"], test_user1["password"])
            User.remove_user(token, test_user2["unique"], test_user2["password"])
            print("\033[92m[SUCCESS]\033[0m Cleanup: Users removed")

if __name__ == "__main__":
    for module in [User, Friendship]:
        try: module.test()
        except Exception as e:
            print(f"\033[91m[ERROR]\033[0m {e}")

