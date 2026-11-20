"""Validate native outcome evidence without loading Unity."""
import math


def validate_metrics(final, instance):
    metrics = final["metrics"]
    health, initial = metrics["base_health"], metrics["initial_base_health"]
    if type(health) is not int or type(initial) is not int or not 0 <= health <= initial or initial < 1:
        raise ValueError("invalid TowerMind base health")
    if type(metrics["native_decisions"]) is not int or metrics["native_decisions"] != final["steps"]:
        raise ValueError("TowerMind decision count disagrees with the service")
    reward = metrics["native_return"]
    if type(reward) not in (int, float) or not math.isclose(reward, final["return"], abs_tol=1e-8):
        raise ValueError("TowerMind cumulative return disagrees with the service")
    if not math.isclose(reward, health - initial, abs_tol=1e-8):
        raise ValueError("TowerMind sparse return disagrees with base health")
    won = final["reason"] == "native_terminated" and health > 0
    if type(metrics["native_success"]) is not int or metrics["native_success"] != int(won) or final["success"] != won:
        raise ValueError("TowerMind success requires a completed native level with the base alive")
