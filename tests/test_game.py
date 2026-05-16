from uuid import uuid4

from .helpers import check_step


def assert_rating_change(change, user_id, before, min_delta, max_delta):
    assert change["user_id"] == user_id
    assert min_delta <= change["delta"] <= max_delta
    assert change["before"] == before
    assert change["after"] == max(0, before + change["delta"])


def assert_stats(stats, games, wins, losses, draws, rating):
    assert stats["games_total"] == games
    assert stats["games_finished"] == wins + losses + draws
    assert stats["games_active"] == games - stats["games_finished"]
    assert stats["wins"] == wins
    assert stats["losses"] == losses
    assert stats["draws"] == draws
    assert stats["rating"] == rating
    assert stats["user"]["rating"] == rating

    if losses:
        assert stats["win_loss_ratio"] == round(wins / losses, 2)
    else:
        assert stats["win_loss_ratio"] is None

    if stats["games_finished"]:
        assert stats["win_rate"] == round((wins / stats["games_finished"]) * 100, 2)
    else:
        assert stats["win_rate"] == 0.0


def test_opponent_search_and_game_flow(api_client, test_users, cleanup_test_users, start_fen):
    missing_user_id = str(uuid4())

    check_step("Opponent search for missing user returns 404")
    missing_search = api_client.start_search_opponent_response(missing_user_id)
    assert missing_search.status_code == 404

    check_step("Stop search for missing user returns 404")
    missing_stop = api_client.stop_search_opponent_response(missing_user_id)
    assert missing_stop.status_code == 404

    check_step("Surrender for missing user returns 404")
    missing_surrender = api_client.surrender_response(missing_user_id)
    assert missing_surrender.status_code == 404

    check_step("AI game for missing user returns 404")
    missing_ai_game = api_client.start_ai_game_response(missing_user_id)
    assert missing_ai_game.status_code == 404

    check_step("Stats for missing user returns 404")
    missing_stats = api_client.get_user_stats_response(missing_user_id)
    assert missing_stats.status_code == 404

    check_step("Register users for game flow")
    user1 = api_client.register_user(test_users["max"])
    user2 = api_client.register_user(test_users["john"])
    user3 = api_client.register_user(test_users["kate"])
    mate_user1 = api_client.register_user(test_users["mate_white"])
    mate_user2 = api_client.register_user(test_users["mate_black"])

    check_step("Await opponent without active search returns 404")
    await_without_search = api_client.await_opponent_response(user1["id"], timeout=3)
    assert await_without_search.status_code == 404

    check_step("Start opponent search")
    first_search = api_client.start_search_opponent(user1["id"])
    assert first_search["user"]["id"] == user1["id"]
    assert first_search["opponent"] is None

    check_step("Duplicate opponent search is rejected")
    duplicate_search = api_client.start_search_opponent_response(user1["id"])
    assert duplicate_search.status_code == 400
    assert "already searching" in duplicate_search.text

    check_step("Stop active opponent search")
    stopped_search = api_client.stop_search_opponent(user1["id"])
    assert stopped_search["detail"] == "Successfully stopped searching for opponent"

    check_step("Match two users through opponent search")
    api_client.start_search_opponent(user1["id"])
    api_client.start_search_opponent(user2["id"])

    user1_match = api_client.await_opponent(user1["id"])
    assert user1_match["user"]["id"] == user1["id"]
    assert user1_match["opponent"]["id"] == user2["id"]
    assert user1_match["game"]["id"]
    assert user1_match["game"]["white"] in [user1["id"], user2["id"]]
    assert user1_match["game"]["black"] in [user1["id"], user2["id"]]
    assert user1_match["game"]["white"] != user1_match["game"]["black"]
    assert user1_match["game"]["board"]["fen"] == start_fen

    check_step("Second player can receive the found game too")
    user2_match = api_client.await_opponent(user2["id"], timeout=3)
    assert user2_match["user"]["id"] == user2["id"]
    assert user2_match["opponent"]["id"] == user1["id"]
    assert user2_match["game"]["id"] == user1_match["game"]["id"]
    assert user2_match["game"]["white"] == user1_match["game"]["white"]
    assert user2_match["game"]["black"] == user1_match["game"]["black"]
    assert user2_match["game"]["board"]["fen"] == start_fen

    check_step("Load created game board")
    game = api_client.get_board(user1_match["game"]["id"])
    assert game["game"]["id"] == user1_match["game"]["id"]
    assert {game["game"]["white"], game["game"]["black"]} == {user1["id"], user2["id"]}

    check_step("Make e2e4 and verify board is persisted")
    initial_fen = game["game"]["board"]["fen"]
    move_result = api_client.move_piece(user1_match["game"]["id"], "e2e4")
    assert move_result["chess_core"]["isLegal"] is True
    assert move_result["game"]["board"]["fen"] != initial_fen

    game_after_move = api_client.get_board(user1_match["game"]["id"])
    assert game_after_move["game"]["board"]["fen"] == move_result["game"]["board"]["fen"]

    check_step("Stop search while in game is rejected")
    stop_in_game = api_client.stop_search_opponent_response(user1["id"])
    assert stop_in_game.status_code == 400

    check_step("Start search while in game is rejected")
    start_search_in_game = api_client.start_search_opponent_response(user1["id"])
    assert start_search_in_game.status_code == 400

    check_step("Surrender game and apply rating changes")
    user1_rating_before_surrender = api_client.get_user(user1["id"])["rating"]
    user2_rating_before_surrender = api_client.get_user(user2["id"])["rating"]
    surrender = api_client.surrender(user1["id"])
    assert surrender["result"]["reason"] == "surrender"
    assert_rating_change(
        surrender["result"]["loser"],
        user1["id"],
        user1_rating_before_surrender,
        -55,
        -45,
    )
    assert_rating_change(
        surrender["result"]["winner"],
        user2["id"],
        user2_rating_before_surrender,
        20,
        25,
    )
    assert api_client.get_user(user1["id"])["rating"] == surrender["result"]["loser"]["after"]
    assert api_client.get_user(user2["id"])["rating"] == surrender["result"]["winner"]["after"]

    check_step("Get player stats after surrender")
    user1_stats = api_client.get_user_stats(user1["id"])
    user2_stats = api_client.get_user_stats(user2["id"])
    assert_stats(user1_stats, games=1, wins=0, losses=1, draws=0, rating=surrender["result"]["loser"]["after"])
    assert_stats(user2_stats, games=1, wins=1, losses=0, draws=0, rating=surrender["result"]["winner"]["after"])

    check_step("Create an AI game and request an AI move through Chess Core")
    invalid_ai_difficulty = api_client.start_ai_game_response(user3["id"], user_color="white", ai_difficulty=6)
    assert invalid_ai_difficulty.status_code == 422

    ai_match = api_client.start_ai_game(user3["id"], user_color="white", ai_difficulty=4)
    ai_game_id = ai_match["game"]["id"]
    assert ai_match["user"]["id"] == user3["id"]
    assert ai_match["opponent"]["unique"] == "chess_ai"
    assert ai_match["game"]["white"] == user3["id"]
    assert ai_match["game"]["black"] == ai_match["opponent"]["id"]
    assert ai_match["game"]["board"]["fen"] == start_fen
    assert ai_match["game"]["ai_difficulty"] == 4

    ai_before_player = api_client.move_ai_response(ai_game_id)
    assert ai_before_player.status_code == 400
    assert "not AI's turn" in ai_before_player.text

    search_while_ai_game = api_client.start_search_opponent_response(user3["id"])
    assert search_while_ai_game.status_code == 400
    assert "in the game" in search_while_ai_game.text

    player_ai_move = api_client.move_piece(ai_game_id, "e2e4")
    assert player_ai_move["chess_core"]["isLegal"] is True
    assert player_ai_move["game"]["ai_difficulty"] == 4

    ai_move = api_client.move_ai(ai_game_id)
    assert ai_move["chess_core"]["isLegal"] is True
    assert ai_move["chess_core"]["moveFrom"]
    assert ai_move["chess_core"]["moveTo"]
    assert ai_move["game"]["ai_difficulty"] == 4
    assert ai_move["from_to"] == [
        ai_move["chess_core"]["moveFrom"],
        ai_move["chess_core"]["moveTo"],
    ]
    assert ai_move["game"]["board"]["fen"] != player_ai_move["game"]["board"]["fen"]

    ai_game_after_move = api_client.get_board(ai_game_id)
    assert ai_game_after_move["game"]["board"]["fen"] == ai_move["game"]["board"]["fen"]

    ai_surrender = api_client.surrender(user3["id"])
    assert ai_surrender["result"]["reason"] == "surrender"

    check_step("Create another game and finish it with checkmate")
    api_client.start_search_opponent(mate_user1["id"])
    api_client.start_search_opponent(mate_user2["id"])
    mate_match = api_client.await_opponent(mate_user1["id"])
    mate_game_id = mate_match["game"]["id"]

    for move in ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6"]:
        move_result = api_client.move_piece(mate_game_id, move)
        assert move_result["chess_core"]["isLegal"] is True
        assert move_result["result"] is None

    white_id = mate_match["game"]["white"]
    black_id = mate_match["game"]["black"]
    white_rating_before_mate = api_client.get_user(white_id)["rating"]
    black_rating_before_mate = api_client.get_user(black_id)["rating"]
    mate_result = api_client.move_piece(mate_game_id, "h5f7")
    assert mate_result["chess_core"]["isLegal"] is True
    assert mate_result["chess_core"]["isCheck"] is True
    assert mate_result["chess_core"]["isCheckmate"] is True
    assert mate_result["result"]["reason"] == "checkmate"
    assert_rating_change(
        mate_result["result"]["winner"],
        white_id,
        white_rating_before_mate,
        20,
        25,
    )
    assert_rating_change(
        mate_result["result"]["loser"],
        black_id,
        black_rating_before_mate,
        -25,
        -20,
    )
    assert api_client.get_user(white_id)["rating"] == mate_result["result"]["winner"]["after"]
    assert api_client.get_user(black_id)["rating"] == mate_result["result"]["loser"]["after"]

    check_step("Get player stats after checkmate")
    white_stats = api_client.get_user_stats(white_id)
    black_stats = api_client.get_user_stats(black_id)
    assert_stats(white_stats, games=1, wins=1, losses=0, draws=0, rating=mate_result["result"]["winner"]["after"])
    assert_stats(black_stats, games=1, wins=0, losses=1, draws=0, rating=mate_result["result"]["loser"]["after"])

    check_step("Await after stopped search returns 404")
    api_client.start_search_opponent(user1["id"])
    api_client.stop_search_opponent(user1["id"])
    await_after_stop = api_client.await_opponent_response(user1["id"], timeout=3)
    assert await_after_stop.status_code == 404

    check_step("Cleanup game test users")
    for user_data in test_users.values():
        api_client.remove_user_if_exists(user_data)
        search_after_cleanup = api_client.search_user("unique", user_data["unique"])
        assert search_after_cleanup["searched"] == []
