"""MiniGrid-only return semantics, checked outside the agent container."""
import math


def validate_metrics(final, instance):
    metrics = final["metrics"]
    if metrics != {"success": int(final["success"]), "native_return": final["return"]}:
        raise ValueError("inconsistent native metrics")
    if final["reason"] == "sim_error":
        return
    if final["success"] != (final["terminated"] and final["return"] > 0):
        raise ValueError("inconsistent MiniGrid success")
    if final["success"]:
        expected = 1 - 0.9 * final["steps"] / instance["native_max_steps"]
        if not math.isclose(final["return"], expected, abs_tol=1e-9):
            raise ValueError("inconsistent MiniGrid return")
    elif final["return"] != (-1 if instance["family"] == "dynamic-obstacles" and final["terminated"] else 0):
        raise ValueError("inconsistent MiniGrid failure return")
