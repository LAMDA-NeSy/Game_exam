"""Consistency checks for the terminal result reported by the native forest level."""


def validate_metrics(final, instance):
    metrics = final["metrics"]
    if metrics["level"] != 1:
        raise ValueError("unexpected forest level")
    for role in ("fireboy", "watergirl"):
        if type(metrics[role]) is not int or metrics[role] < 0:
            raise ValueError(f"invalid diamond count for {role}")

    terminal = (metrics["terminal_outcome"], metrics["terminal_reason"])
    valid_events = {(None, None), ("success", "level_completed"),
                    ("fail", "level_failed"), ("fail", "level_ended")}
    if terminal not in valid_events or final["terminated"] != (terminal != (None, None)):
        raise ValueError("inconsistent native terminal event")
    won = terminal == ("success", "level_completed")
    if final["success"] != won or final["return"] != float(won) or metrics["success"] != int(won):
        raise ValueError("reward disagrees with native level completion")
