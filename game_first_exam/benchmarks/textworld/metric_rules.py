"""TextWorld's native cumulative score and explicit win flag."""
import math


def validate_metrics(final, instance):
    metrics = final["metrics"]
    if metrics["max_score"] != instance["max_score"] or metrics["max_score"] <= 0:
        raise ValueError("wrong maximum score")
    if not 0 <= metrics["score"] <= metrics["max_score"]:
        raise ValueError("invalid native score")
    if not math.isclose(metrics["normalized_score"], metrics["score"] / metrics["max_score"]):
        raise ValueError("inconsistent normalized score")
    if metrics["score"] != final["return"]:
        raise ValueError("cumulative score was not converted to deltas correctly")
    for key in ("won", "lost"):
        if type(metrics[key]) is not int or metrics[key] not in (0, 1):
            raise ValueError("invalid outcome flag")
    if final["success"] != (bool(metrics["won"]) and not final["sim_error"]):
        raise ValueError("inconsistent TextWorld win")
    if metrics["won"] and metrics["lost"]:
        raise ValueError("contradictory outcome")
    if type(metrics["native_moves"]) is not int or not 0 <= metrics["native_moves"] <= final["steps"]:
        raise ValueError("invalid native move count")
