def validate_metrics(final, instance):
    metrics = final["metrics"]
    deaths = metrics["deaths"]
    if type(deaths) is not int or deaths < 0:
        raise ValueError("Invalid native death count")
    checkpoints = metrics["checkpoints_passed"]
    if type(checkpoints) is not int or not 0 <= checkpoints <= 4:
        raise ValueError("Invalid native checkpoint count")
    success = metrics["success"]
    if type(success) is not int or success not in (0, 1):
        raise ValueError("Invalid native success flag")
    won = success == 1
    if won and deaths:
        raise ValueError("Act 1 requires a deathless finish")
    if final["terminated"] != bool(won or deaths):
        raise ValueError("Terminal flag disagrees with native result")
    if final["success"] != won or final["return"] != float(won):
        raise ValueError("Reward disagrees with native result")
