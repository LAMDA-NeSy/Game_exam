def validate_metrics(final, instance):
    metrics = final["metrics"]
    score, deaths, success = (metrics[k] for k in ("score", "deaths", "success"))
    if type(score) is not int or score < 0:
        raise ValueError("Invalid native score")
    if type(deaths) is not int or deaths < 0:
        raise ValueError("Invalid native death count")
    if type(success) is not int or success not in (0, 1) or success != int(score >= 600):
        raise ValueError("Score and goal disagree")
    won = bool(success)
    if final["terminated"] != bool(won or deaths):
        raise ValueError("Terminal flag disagrees with native result")
    if final["success"] != won or final["return"] != float(won):
        raise ValueError("Reward disagrees with native result")
