"""Verify immutable live evidence. Game-specific metric rules never run in the agent."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from config_schema import PROTOCOL, validate_instance


def grade(final, instance, validate_metrics):
    """Validate isolated live evidence, NOT replay/prove a trajectory or authenticate a hostile simulator."""
    validate_instance(instance)
    encoded = json.dumps(instance, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if final.get("instance_sha256") != hashlib.sha256(encoded).hexdigest():
        raise ValueError("frozen instance mismatch")
    for key in ("benchmark", "env_id", "seed", "max_steps"):
        if final.get(key) != instance[key]:
            raise ValueError(f"instance mismatch: {key}")
    if final.get("schema") != PROTOCOL or final.get("finalized") is not True:
        raise ValueError("absent or unsupported live verdict")
    for key in ("terminated", "truncated", "budget_exhausted", "result_valid"):
        if type(final.get(key)) is not bool:
            raise ValueError(f"invalid {key}")
    if type(final.get("steps")) is not int or (final["steps"] < 0 or (instance["max_steps"] is not None and final["steps"] > instance["max_steps"])):
        raise ValueError("invalid step count")
    for key in ("return", "elapsed_seconds"):
        if type(final.get(key)) not in (int, float) or not math.isfinite(final[key]):
            raise ValueError(f"invalid {key}")
    if final["elapsed_seconds"] < 0 or final["budget_exhausted"] != (instance["max_steps"] is not None and final["steps"] == instance["max_steps"]):
        raise ValueError("inconsistent budget accounting")
    if type(final.get("invalid_actions")) is not int or final["invalid_actions"] < 0:
        raise ValueError("invalid rejected-action count")
    reason = final.get("reason")
    sources = {"native_terminated": "native", "native_truncated": "native", "step_limit": "budget",
               "time_limit": "budget", "agent_finished": "agent", "environment_error": "environment"}
    if reason not in sources or final.get("end_source") != sources[reason]:
        raise ValueError("unknown/inconsistent end reason")
    if reason == "environment_error":
        if final["result_valid"] or final.get("error_category") != "environment" or final.get("sim_error") != 1:
            raise ValueError("inconsistent environment fault")
        if final.get("success") is not None or final.get("metrics") is not None or not isinstance(final.get("error"), dict):
            raise ValueError("a broken environment cannot supply a model score")
        return {"success": 0.0, "infra_error": 1, "environment_error": 1, "sim_error": 1,
                "result_valid": False, "error_category": "environment", "reason": reason,
                "error": final["error"], "steps": final["steps"], "primary_score": None,
                "native_metrics": {}, "graded_by_live": 1}
    if not final["result_valid"] or final.get("error_category") is not None or final.get("error") is not None or final.get("sim_error") != 0:
        raise ValueError("inconsistent valid result")
    if final.get("initial_state_sha256") != instance["initial_state_sha256"]:
        raise ValueError("initial state mismatch")
    if type(final.get("success")) is not bool:
        raise ValueError("invalid success flag")
    if final["truncated"] and not instance["capabilities"]["native_truncation"]:
        raise ValueError("undeclared native truncation")
    if reason == "native_terminated" and not final["terminated"]:
        raise ValueError("native termination flag absent")
    if reason == "native_truncated" and (not final["truncated"] or final["terminated"]):
        raise ValueError("invalid native truncation flags")
    if reason in {"step_limit", "time_limit", "agent_finished"} and (final["terminated"] or final["truncated"]):
        raise ValueError("native flags cannot be assigned to a public end reason")
    if (reason == "step_limit" and not final["budget_exhausted"]) or (reason in {"time_limit", "agent_finished"} and final["budget_exhausted"]):
        raise ValueError("inconsistent public step limit")
    if final["steps"] == 0 and (final["success"] or final["terminated"] or final["truncated"]):
        raise ValueError("completed environment without an action")
    metrics = final.get("metrics")
    if not isinstance(metrics, dict):
        raise TypeError("missing native metrics")
    validate_metrics(final, instance)
    score = metrics[instance["metric_spec"]["primary"]]
    if type(score) not in (int, float) or not math.isfinite(score):
        raise ValueError("invalid primary score")
    return {"success": float(final["success"]), "return": final["return"], "steps": final["steps"],
            "infra_error": 0, "sim_error": 0, "environment_error": 0, "result_valid": True,
            "error_category": None, "graded_by_live": 1, "reason": reason, "native_metrics": metrics,
            "primary_metric": instance["metric_spec"]["primary"], "primary_score": score}


def main():
    from metric_rules import validate_metrics
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", default="/data/final.json")
    parser.add_argument("--instance", default="/tests/instance.json")
    parser.add_argument("--output", default="/logs/verifier")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    try:
        result = grade(json.loads(Path(args.evidence).read_text()),
                       json.loads(Path(args.instance).read_text()), validate_metrics)
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
        result = {"success": 0.0, "infra_error": 1, "result_valid": False, "error_category": "evidence", "error": str(exc)}
    (output / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / "reward.json").write_text(json.dumps({k: v for k, v in result.items()
        if isinstance(v, (int, float))}, indent=2, allow_nan=False) + "\n")
    if result["infra_error"]:
        raise SystemExit("missing or inconsistent trusted evidence")
    (output / "reward.txt").write_text(str(result["success"]) + "\n")


if __name__ == "__main__":
    main()
