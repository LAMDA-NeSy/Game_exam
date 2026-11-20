"""Check native score and tic evidence from the isolated live simulator."""
import math

from instance_schema import SCENARIOS


def validate_action_tics(actions, decisions, total_tics, ended):
    if not isinstance(actions, list) or len(actions) != decisions:
        raise ValueError("invalid ViZDoom per-action tic ledger")
    actual_tics = 0
    for index, pair in enumerate(actions, 1):
        if not isinstance(pair, list) or len(pair) != 2 or any(type(value) is not int for value in pair):
            raise ValueError("invalid ViZDoom requested/actual tic pair")
        requested, actual = pair
        if not 1 <= actual <= requested or (actual != requested and not (ended and index == decisions)):
            raise ValueError("invalid ViZDoom action duration")
        actual_tics += actual
    if actual_tics != total_tics:
        raise ValueError("ViZDoom tic ledger disagrees with the native total")


def validate_metrics(final, instance):
    metrics = final["metrics"]
    scene = SCENARIOS[instance["family"]]
    fields = {"native_return", "native_tics", "decisions", "native_terminated", "native_truncated", "player_dead"}
    stats = {name.lower() for name in scene.get("stats", ())}
    fields |= stats
    if scene["goal"]:
        fields |= {"objective_success", "objective_progress"}
    variable = instance["tics_per_decision"] == 1
    if variable:
        fields.add("action_tics")
    if set(metrics) != fields:
        raise ValueError("invalid ViZDoom metric fields")
    if any(type(metrics[name]) is not int for name in stats):
        raise ValueError("invalid ViZDoom native statistics")
    score = metrics["native_return"]
    if type(score) not in (int, float) or not math.isfinite(score) or not math.isclose(
        score, final["return"], rel_tol=1e-10, abs_tol=1e-10
    ):
        raise ValueError("inconsistent ViZDoom native return")
    decisions, tics = metrics["decisions"], metrics["native_tics"]
    timeout, repeat = instance["timeout_tics"], instance["tics_per_decision"]
    if type(decisions) is not int or decisions != final["steps"] or type(tics) is not int or tics < 0 or (timeout and tics > timeout):
        raise ValueError("invalid ViZDoom decision or tic count")
    terminated, truncated, dead = (metrics[k] for k in ("native_terminated", "native_truncated", "player_dead"))
    if (any(type(v) is not bool for v in (terminated, truncated, dead)) or
            terminated != final["terminated"] or truncated != final["truncated"]):
        raise ValueError("inconsistent ViZDoom native ending flags")
    if decisions == 0:
        if tics != 0 or score != 0 or terminated or truncated:
            raise ValueError("ViZDoom episode progressed without a decision")
    if variable:
        stopped = terminated or truncated or final["reason"] == "time_limit"
        validate_action_tics(metrics["action_tics"], decisions, tics, stopped)
    elif decisions > 0:
        if not (decisions - 1) * repeat < tics <= decisions * repeat:
            raise ValueError("invalid ViZDoom fixed action length")
        if not (terminated or truncated) and tics != decisions * repeat:
            raise ValueError("ViZDoom stopped inside a nonterminal action")
    if truncated and (not timeout or tics != timeout):
        raise ValueError("ViZDoom native timeout before the tic limit")
    if dead and not terminated:
        raise ValueError("ViZDoom player death must terminate the episode")
    if not scene["goal"]:
        if final["success"] is not False:
            raise ValueError("score-only scenarios do not assign objective success")
        return
    goal = 100 if scene["goal"] == "green-vest" else 1
    progress = metrics["objective_progress"]
    if type(progress) is not int or progress not in (0, goal):
        raise ValueError("unexpected scenario objective progress")
    success = progress == goal
    if (type(metrics["objective_success"]) is not int or metrics["objective_success"] != int(success) or
            final["success"] != success or (success and not terminated)):
        raise ValueError("inconsistent ViZDoom objective evidence")
    if instance["family"] in {"basic", "my-way-home", "deadly-corridor"} and terminated != (success or dead):
        raise ValueError("inconsistent objective or death termination")
