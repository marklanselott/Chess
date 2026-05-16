import httpx


BLUE = "\033[96m"
RESET = "\033[0m"


def check_step(message: str):
    print(f"{BLUE}[check] {message}{RESET}")


class ApiClient:
    def __init__(self, base_url: str, token):
        self.base_url = base_url
        self.token = token

    def params(self, **extra):
        return {"token": self.token, **extra}

    def register_user(self, user_data: dict):
        response = httpx.post(
            f"{self.base_url}/api/user/register",
            params=self.params(),
            json=user_data,
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to register user: {response.text}"
        return response.json()

    def search_user(self, key: str, value):
        response = httpx.post(
            f"{self.base_url}/api/user/search/",
            params=self.params(),
            json={key: value},
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to search user: {response.text}"
        return response.json()

    def update_user(self, user_id: str, key: str, value):
        response = httpx.post(
            f"{self.base_url}/api/user/update/user_id/{user_id}",
            params=self.params(),
            json={"user_id": user_id, key: value},
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to update user: {response.text}"
        return response.json()

    def remove_user(self, unique: str, password: str):
        response = httpx.post(
            f"{self.base_url}/api/user/remove",
            params=self.params(),
            json={"unique": unique, "password": password},
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to remove user: {response.text}"
        return response.json()

    def remove_user_if_exists(self, user_data: dict):
        response = httpx.post(
            f"{self.base_url}/api/user/remove",
            params=self.params(),
            json={"unique": user_data["unique"], "password": user_data["password"]},
            timeout=10,
        )
        assert response.status_code in (200, 404), f"Failed to cleanup user: {response.text}"
        return response

    def get_user(self, user_id: str):
        response = self.get_user_response(user_id)
        assert response.status_code == 200, f"Failed to get user: {response.text}"
        return response.json()

    def get_user_response(self, user_id: str):
        return httpx.get(
            f"{self.base_url}/api/user/user_id/{user_id}",
            params=self.params(),
            timeout=10,
        )

    def get_user_stats(self, user_id: str):
        response = self.get_user_stats_response(user_id)
        assert response.status_code == 200, f"Failed to get user stats: {response.text}"
        return response.json()

    def get_user_stats_response(self, user_id: str):
        return httpx.get(
            f"{self.base_url}/api/user/stats/user_id/{user_id}",
            params=self.params(),
            timeout=10,
        )

    def get_friend_list(self, user_id: str):
        response = self.get_friend_list_response(user_id)
        assert response.status_code == 200, f"Failed to get friends: {response.text}"
        return response.json()

    def get_friend_list_response(self, user_id: str):
        return httpx.get(
            f"{self.base_url}/api/friends/get_list/user_id/{user_id}",
            params=self.params(),
            timeout=10,
        )

    def send_friend_request(self, user_id: str, friend_id: str):
        response = self.send_friend_request_response(user_id, friend_id)
        assert response.status_code == 200, f"Failed to send friend request: {response.text}"
        return response.json()

    def send_friend_request_response(self, user_id: str, friend_id: str):
        return httpx.post(
            f"{self.base_url}/api/friends/send_request",
            params=self.params(),
            json={"user_id": user_id, "friend_id": friend_id},
            timeout=10,
        )

    def update_friend_request(self, request_id: str, accept: bool):
        response = httpx.post(
            f"{self.base_url}/api/friends/update_request",
            params=self.params(),
            json={"request_id": request_id, "status": accept},
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to update friend request: {response.text}"
        return response.json()

    def get_friend_requests_for_me(self, user_id: str):
        response = httpx.get(
            f"{self.base_url}/api/friends/get_requests_for_me/user_id/{user_id}",
            params=self.params(),
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to get friend requests: {response.text}"
        return response.json()

    def get_my_friend_requests(self, user_id: str):
        response = httpx.get(
            f"{self.base_url}/api/friends/get_requests_my/user_id/{user_id}",
            params=self.params(),
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to get my friend requests: {response.text}"
        return response.json()

    def cancel_friend_request(self, request_id: str):
        response = httpx.get(
            f"{self.base_url}/api/friends/cancel_request/request_id/{request_id}",
            params=self.params(),
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to cancel friend request: {response.text}"
        return response.json()

    def start_search_opponent(self, user_id: str):
        response = self.start_search_opponent_response(user_id)
        assert response.status_code == 200, f"Failed to start opponent search: {response.text}"
        return response.json()

    def start_search_opponent_response(self, user_id: str):
        return httpx.post(
            f"{self.base_url}/api/opponents/search/start",
            params=self.params(user_id=user_id),
            timeout=10,
        )

    def await_opponent(self, user_id: str, timeout: int = 10):
        response = self.await_opponent_response(user_id, timeout=timeout)
        assert response.status_code == 200, f"Failed to await opponent: {response.text}"
        return response.json()

    def await_opponent_response(self, user_id: str, timeout: int = 10):
        return httpx.get(
            f"{self.base_url}/api/opponents/await",
            params=self.params(user_id=user_id),
            timeout=timeout,
        )

    def get_board(self, game_id: str):
        response = httpx.get(
            f"{self.base_url}/api/game/game",
            params=self.params(game_id=game_id),
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to get game board: {response.text}"
        return response.json()

    def move_piece(self, game_id: str, from_to: str):
        response = httpx.get(
            f"{self.base_url}/api/game/move",
            params=self.params(game_id=game_id, from_to=from_to),
            timeout=10,
        )
        assert response.status_code == 200, f"Failed to move piece: {response.text}"
        return response.json()

    def start_ai_game(self, user_id: str, user_color: str = "white", ai_difficulty: int = 3):
        response = self.start_ai_game_response(user_id, user_color, ai_difficulty)
        assert response.status_code == 200, f"Failed to start AI game: {response.text}"
        return response.json()

    def start_ai_game_response(self, user_id: str, user_color: str = "white", ai_difficulty: int = 3):
        return httpx.post(
            f"{self.base_url}/api/game/ai/start",
            params=self.params(user_id=user_id, user_color=user_color, ai_difficulty=ai_difficulty),
            timeout=10,
        )

    def move_ai(self, game_id: str):
        response = self.move_ai_response(game_id)
        assert response.status_code == 200, f"Failed to move AI: {response.text}"
        return response.json()

    def move_ai_response(self, game_id: str):
        return httpx.post(
            f"{self.base_url}/api/game/ai/move",
            params=self.params(game_id=game_id),
            timeout=20,
        )

    def stop_search_opponent(self, user_id: str):
        response = self.stop_search_opponent_response(user_id)
        assert response.status_code == 200, f"Failed to stop opponent search: {response.text}"
        return response.json()

    def stop_search_opponent_response(self, user_id: str):
        return httpx.post(
            f"{self.base_url}/api/opponents/search/stop",
            params=self.params(user_id=user_id),
            timeout=10,
        )

    def surrender(self, user_id: str):
        response = self.surrender_response(user_id)
        assert response.status_code == 200, f"Failed to surrender: {response.text}"
        return response.json()

    def surrender_response(self, user_id: str):
        return httpx.post(
            f"{self.base_url}/api/game/surrender",
            params=self.params(user_id=user_id),
            timeout=10,
        )
