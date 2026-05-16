from uuid import uuid4

from .helpers import check_step


def test_friendship_flow(api_client, test_users, cleanup_test_users):
    check_step("Register two users for friendship flow")
    user1 = api_client.register_user(test_users["max"])
    user2 = api_client.register_user(test_users["john"])

    check_step("Friend list for missing user returns 404")
    missing_list = api_client.get_friend_list_response(str(uuid4()))
    assert missing_list.status_code == 404

    check_step("Friend request to missing user returns 404")
    missing_friend = api_client.send_friend_request_response(user1["id"], str(uuid4()))
    assert missing_friend.status_code == 404

    check_step("Friend request to self is rejected")
    self_request = api_client.send_friend_request_response(user1["id"], user1["id"])
    assert self_request.status_code == 400

    check_step("Send friend request")
    request = api_client.send_friend_request(user1["id"], user2["id"])
    assert request["friend"]["id"] == user2["id"]

    check_step("Recipient sees incoming friend request")
    requests_for_me = api_client.get_friend_requests_for_me(user2["id"])
    assert any(item["id"] == request["id"] for item in requests_for_me)

    check_step("Sender sees outgoing friend request")
    my_requests = api_client.get_my_friend_requests(user1["id"])
    assert any(item["id"] == request["id"] for item in my_requests)

    check_step("Accept friend request and verify friends list")
    api_client.update_friend_request(request["id"], True)
    friends_list = api_client.get_friend_list(user2["id"])
    assert any(friend["id"] == user1["id"] for friend in friends_list)

    check_step("Remove friendship and cancel a new request")
    api_client.update_friend_request(request["id"], False)

    request_to_cancel = api_client.send_friend_request(user2["id"], user1["id"])
    api_client.cancel_friend_request(request_to_cancel["id"])

    requests_after_cancel = api_client.get_friend_requests_for_me(user1["id"])
    assert not any(item["id"] == request_to_cancel["id"] for item in requests_after_cancel)
