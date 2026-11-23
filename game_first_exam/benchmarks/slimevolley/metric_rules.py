"""Validate the native match result and Game Exam's end flags."""


def validate_metrics(final, instance):
    metrics = final["metrics"]
    right, left = (metrics[key] for key in ("right_lives", "left_lives"))
    if any(type(lives) is not int or not 0 <= lives <= 5 for lives in (right, left)) or right == left == 0:
        raise ValueError("invalid SlimeVolley lives")
    steps = final["steps"]
    if (type(metrics["native_steps"]) is not int or metrics["native_steps"] != steps
            or not 5 * 2 - right - left <= steps <= instance["native_max_steps"]):
        raise ValueError("invalid SlimeVolley native step count")
    terminated = min(right, left) == 0
    truncated = not terminated and steps == instance["native_max_steps"]
    if (final["terminated"], final["truncated"]) != (terminated, truncated):
        raise ValueError("inconsistent SlimeVolley ending")
    if final["success"] != ((terminated or truncated) and right > left):
        raise ValueError("inconsistent SlimeVolley success")
    expected = {"points_for": 5 - left, "points_against": 5 - right, "native_return": right - left}
    if (any(type(metrics[key]) is not int or metrics[key] != value for key, value in expected.items())
            or final["return"] != expected["native_return"]):
        raise ValueError("inconsistent SlimeVolley score")
