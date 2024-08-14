def get_default_session_data(user_id, mode):
    data = {
        "user_id": user_id,
        "players_name": ["player1", "player2"],
        "left_score": 0,
        "right_score": 0,
        "mode": mode,
    }
    if mode == "tournament":
        data["game_round"] = 1
        data["win_history"] = []
        data["match_history"] = []
        data["players_name"].extend(["player3", "player4"])
    return data