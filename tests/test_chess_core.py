import httpx

from .helpers import check_step


def chess_core_move(client: httpx.Client, chess_core_base: str, fen: str, from_: str, to_: str) -> dict:
    response = client.post(
        f"{chess_core_base}/api/chess/move",
        json={"fen": fen, "from": from_, "to": to_},
        timeout=10,
    )
    assert response.status_code == 200, f"{from_}{to_} failed: {response.text}"
    result = response.json()
    assert result["isLegal"], f"{from_}{to_} should be legal: {result}"
    assert result["newFen"], f"{from_}{to_} should return newFen: {result}"
    return result


def test_chess_core_checkmate_sequence(chess_core_base, start_fen):
    fen = start_fen
    moves = [
        ("e2", "e4", False, False),
        ("e7", "e5", False, False),
        ("d1", "h5", False, False),
        ("b8", "c6", False, False),
        ("f1", "c4", False, False),
        ("g8", "f6", False, False),
        ("h5", "f7", True, True),
    ]

    with httpx.Client() as client:
        for from_, to_, expected_check, expected_mate in moves:
            check_step(f"Chess Core move {from_}{to_}")
            result = chess_core_move(client, chess_core_base, fen, from_, to_)
            assert result["isCheck"] is expected_check
            assert result["isCheckmate"] is expected_mate
            fen = result["newFen"]

        check_step("Chess Core rejects move after checkmate")
        illegal_after_mate = client.post(
            f"{chess_core_base}/api/chess/move",
            json={"fen": fen, "from": "e8", "to": "f7"},
            timeout=10,
        )
        assert illegal_after_mate.status_code == 200, illegal_after_mate.text
        illegal_result = illegal_after_mate.json()
        assert illegal_result["isLegal"] is False
        assert illegal_result["newFen"] is None
