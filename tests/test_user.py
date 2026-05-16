from uuid import uuid4

from .helpers import check_step


def test_user_lifecycle(api_client, test_users, cleanup_test_users):
    user_data = test_users["max"].copy()

    check_step("Register user")
    user = api_client.register_user(user_data)

    check_step("Search registered user by unique")
    search = api_client.search_user("unique", user["unique"])
    assert search["searched"][0]["id"] == user["id"]

    check_step("Get registered user by id")
    fetched_user = api_client.get_user(user["id"])
    assert fetched_user["id"] == user["id"]

    check_step("Get missing user returns 404")
    missing_user = api_client.get_user_response(str(uuid4()))
    assert missing_user.status_code == 404

    check_step("Update user email")
    updated_user = api_client.update_user(user["id"], "email", "new_email@example.com")
    assert updated_user["email"] == "new_email@example.com"

    check_step("Remove user and verify search is empty")
    api_client.remove_user(user["unique"], user_data["password"])
    search_after_removal = api_client.search_user("unique", user["unique"])
    assert search_after_removal["searched"] == []
