import httpx

from .helpers import check_step


def assert_client_error(response):
    assert 400 <= response.status_code < 500, response.text


def test_invalid_uuid_inputs_do_not_return_500(api_client):
    invalid_uuid = "123"

    check_step("Invalid user_id path values return client errors")
    assert_client_error(api_client.get_user_response(invalid_uuid))
    assert_client_error(api_client.get_user_stats_response(invalid_uuid))
    assert_client_error(api_client.get_friend_list_response(invalid_uuid))

    check_step("Invalid user_id query values return client errors")
    assert_client_error(api_client.start_search_opponent_response(invalid_uuid))
    assert_client_error(api_client.await_opponent_response(invalid_uuid, timeout=3))
    assert_client_error(api_client.stop_search_opponent_response(invalid_uuid))
    assert_client_error(api_client.start_ai_game_response(invalid_uuid))
    assert_client_error(api_client.surrender_response(invalid_uuid))

    check_step("Invalid UUID body values return client errors")
    assert_client_error(api_client.send_friend_request_response(invalid_uuid, invalid_uuid))

    check_step("Invalid game_id query values return client errors")
    get_board = httpx.get(
        f"{api_client.base_url}/api/game/game",
        params=api_client.params(game_id=invalid_uuid),
        timeout=10,
    )
    assert_client_error(get_board)

    move_piece = httpx.get(
        f"{api_client.base_url}/api/game/move",
        params=api_client.params(game_id=invalid_uuid, from_to="e2e4"),
        timeout=10,
    )
    assert_client_error(move_piece)

    move_ai = api_client.move_ai_response(invalid_uuid)
    assert_client_error(move_ai)

    start_analysis = api_client.start_analysis_response(invalid_uuid)
    assert_client_error(start_analysis)

    analysis_status = api_client.get_analysis_status_response(invalid_uuid)
    assert_client_error(analysis_status)
