"""Native achievement metrics and an explicitly separate milestone success flag."""
import math


def validate_metrics(final, instance):
    metrics = final["metrics"]
    achievements = metrics.get("achievements")
    if not isinstance(achievements, dict) or set(achievements) != set(instance["achievement_names"]):
        raise ValueError("wrong achievement vector")
    if any(type(value) is not int or value not in (0, 1) for value in achievements.values()):
        raise ValueError("invalid achievement value")
    count = sum(achievements.values())
    if metrics["achievement_count"] != count or not math.isclose(metrics["achievement_fraction"], count / len(achievements)):
        raise ValueError("inconsistent achievement aggregate")
    if metrics["native_return"] != final["return"]:
        raise ValueError("inconsistent native return")
    milestone = achievements[instance["milestone"]]
    if metrics["milestone_success"] != milestone or final["success"] != (bool(milestone) and not final["sim_error"]):
        raise ValueError("inconsistent milestone")
    if type(metrics["health"]) is not int or not 0 <= metrics["health"] <= 9:
        raise ValueError("invalid health")
    if final["steps"] == 0 and count:
        raise ValueError("achievements without an action")
