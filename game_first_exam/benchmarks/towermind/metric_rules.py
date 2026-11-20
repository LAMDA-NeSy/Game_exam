"""Validate native outcome evidence without loading Unity."""
import math

from instance_schema import DECISION_PERIOD, REWARD_TOLERANCE, REWARD_UNITS_PER_BREACH


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
    feedback = metrics["native_action_feedback_events"]
    if type(feedback) is not int or not 0 <= feedback <= DECISION_PERIOD * final["steps"]:
        raise ValueError("invalid TowerMind action feedback count")
    expected = health - initial - feedback / REWARD_UNITS_PER_BREACH
    if not math.isclose(reward, expected, rel_tol=0, abs_tol=REWARD_TOLERANCE * max(1, final["steps"])):
        raise ValueError("TowerMind sparse return disagrees with base health and action feedback")
    won = final["reason"] == "native_terminated" and health > 0
    if type(metrics["native_success"]) is not int or metrics["native_success"] != int(won) or final["success"] != won:
        raise ValueError("TowerMind success requires a completed native level with the base alive")
