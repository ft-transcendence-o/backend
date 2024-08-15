def get_default_session_data(user_id, mode):
    data = {
        "user_id": user_id,
        "players_name": ["player1", "player2"],
        "left_score": 0,
        "right_score": 0,
        "mode": mode,
    }
    if mode == "tournament":
        data["current_match"] = 0
        data["win_history"] = []
        data["match_results"] = []
        data["matches"] = [
            [0, 1],
            [2, 3],
            [None, None],
        ]
        data["players_name"].extend(["player3", "player3"])
    return data