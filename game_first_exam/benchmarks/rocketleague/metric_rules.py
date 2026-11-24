"""Grade GameWorld 25_01 at the first goal."""
def validate_metrics(final, instance):
    metrics = final["metrics"]
    score = metrics["goals_for"], metrics["goals_against"]
    if any(type(goals) is not int for goals in score) or score not in {(0, 0), (1, 0), (0, 1)}:
        raise ValueError("Invalid first-goal score")
    won = score == (1, 0)
    if final["terminated"] != (score != (0, 0)):
        raise ValueError("Terminal flag disagrees with the scoreboard")
    if (final["success"], final["return"], metrics["success"]) != (won, float(won), int(won)):
        raise ValueError("Reward disagrees with the scoreboard")
