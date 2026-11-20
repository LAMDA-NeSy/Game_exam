#!/usr/bin/env python3
"""Derived game scores from Harbor evidence; never schedules or runs trials."""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "game_first_exam/runtime"))
from config_schema import validate_metric_spec
from game_runtime import (
    RUNNER_VERSION,
    validate_report_code,
)
from game_schemas import is_scenario_score
from reducers import resolve
from write_task_results import classify, load_json


def summarize_trial(path):
    result = json.loads(path.read_text())
    rewards = (result.get("verifier_result") or {}).get("rewards") or {}
    status, reason, _ = classify(path.parent, result, rewards)
    final = load_json(path.parent / "artifacts/data/final.json") or load_json(path.parent / "verifier/final.json")
    metrics = load_json(path.parent / "verifier/metrics.json")
    error_category = metrics.get("error_category") or final.get("error_category")
    if status == "not_a_result" and not error_category:
        error_category = "infrastructure"
    return {
        "error_category": error_category,
        "outcome_class": error_category or ("success" if status == "success" else "game_failure"),
        "model_usage": {
            k: (result.get("agent_result") or {}).get(k)
            for k in ("n_input_tokens", "n_output_tokens", "n_cache_tokens", "cost_usd")
        },
        "task": result.get("task_name", "").rsplit("/", 1)[-1],
        "trial": path.parent.name,
        "valid": status != "not_a_result",
        "status": status,
        "invalid_reason": reason,
        "success": rewards.get("success"),
        "steps": rewards.get("steps"),
        "return": rewards.get("return"),
        "native_metrics": metrics.get("native_metrics", final.get("metrics")) or {},
        "invalid_actions": final.get("invalid_actions"),
        "terminal_reason": final.get("reason"),
        "elapsed_seconds": final.get("elapsed_seconds"),
        "resource_monitor_missing": rewards.get("resource_monitor_missing"),
        "resource_enforced": rewards.get("resource_enforced"),
        "exception": (result.get("exception_info") or {}).get("exception_type"),
        "artifacts": str(path.parent / "artifacts"),
    }


def aggregate(trials, records):
    unexpected = {row["task"] for row in trials} - records.keys()
    if unexpected:
        raise ValueError(f"trials outside frozen suite: {sorted(unexpected)}")
    groups = {}
    for name, record in records.items():
        spec = record["metric_spec"]
        validate_metric_spec(spec)
        scored = is_scenario_score(record)
        group = groups.setdefault(
            record["benchmark"],
            {
                "expected": 0,
                "valid": 0,
                "missing": 0,
                "infra_errors": 0,
                "environment_errors": 0,
                "infrastructure_errors": 0,
                "evidence_errors": 0,
                "metric_spec": None,
                "successes": 0,
                "success_label": None,
                "primary_metric": None,
                "families": {},
                "rows": [],
                "scored_expected": 0,
                "completion_expected": 0,
            },
        )
        if scored:
            group["scored_expected"] += 1
        else:
            if group["metric_spec"] is None:
                group.update(metric_spec=spec, primary_metric=spec["primary"], success_label=spec["success_label"])
            if group["metric_spec"] != spec:
                raise ValueError("incompatible metric definitions within benchmark")
            group["completion_expected"] += 1
        group["expected"] += 1
        family = group["families"].setdefault(record["family"], {"expected": 0, "rows": [], "spec": spec, "scored": scored})
        if family["spec"] != spec:
            raise ValueError("incompatible metric definitions within task family")
        family["expected"] += 1
        matches = [row for row in trials if row["task"] == name]
        if not matches:
            group["missing"] += 1
            continue
        if len(matches) != 1:
            raise ValueError(f"multiple attempts for {name}; void infrastructure attempts explicitly first")
        row = matches[0]
        row.update({k: record[k] for k in ("benchmark", "family", "seed", "digest")})
        row["primary_metric"] = spec["primary"]
        row["primary_score"] = row["native_metrics"].get(spec["primary"])
        if not row["valid"]:
            group["infra_errors"] += 1
            category = row.get("error_category") or "infrastructure"
            group[
                {"environment": "environment_errors", "evidence": "evidence_errors"}.get(
                    category, "infrastructure_errors"
                )
            ] += 1
            continue
        if type(row["primary_score"]) not in (int, float) or not math.isfinite(row["primary_score"]):
            raise ValueError(f"missing or nonfinite primary score in valid trial: {name}")
        group["valid"] += 1
        if scored:
            row.update(success=None, status="scored", outcome_class="scored")
        else:
            group["successes"] += int(row["success"] == 1)
        group["rows"].append(row)
        family["rows"].append(row)
    for group in groups.values():
        rows = group.pop("rows")
        group["complete"] = group["valid"] == group["expected"]
        scored_expected = group.pop("scored_expected")
        expected = group.pop("completion_expected")
        objectives = [row for row in rows if row.get("status") != "scored"]
        objective_valid = len(objectives)
        objective_complete = objective_valid == expected
        group["mean_primary_score"] = mean(row["primary_score"] for row in objectives) if objectives else None
        group["success_rate"] = group["successes"] / objective_valid if objectives else None
        group["mean_steps"] = mean(row["steps"] for row in rows) if rows else None
        observed = []
        for family in group["families"].values():
            selected = family.pop("rows")
            spec = family.pop("spec")
            scored = family.pop("scored")
            family["valid"] = len(selected)
            family["successes"] = None if scored else sum(row["success"] == 1 for row in selected)
            family["mean_primary_score"] = mean(row["primary_score"] for row in selected) if selected else None
            if scored_expected:
                family["primary_metric"] = spec["primary"]
            if selected and not scored:
                observed.append(family["mean_primary_score"])
        group["macro_primary_score"] = mean(observed) if objective_complete and observed else None
        group["observed_macro_primary_score"] = mean(observed) if observed else None
        if scored_expected:
            group["completion_expected"] = expected
            group["completion_valid"] = objective_valid
            group["scored_expected"] = scored_expected
            group["scored_valid"] = group["valid"] - objective_valid
        spec = group["metric_spec"]
        if spec is not None:
            extra = resolve(spec["reducer"], spec["reducer_version"])(objectives, objective_complete)
            if extra.keys() & group.keys():
                raise ValueError("reducer cannot overwrite common completeness/accounting fields")
            group.update(extra)
    valid = sum(group["valid"] for group in groups.values())
    return {
        "benchmarks": groups,
        "expected_trials": len(records),
        "valid_trials": valid,
        "complete": valid == len(records),
    }


def write_report(job, snapshot, output=None, configuration_link="suite-snapshot.json"):
    validate_report_code(snapshot)
    output_dir = Path(output) if output is not None else job
    output_dir.mkdir(parents=True, exist_ok=True)
    trials = [summarize_trial(path) for path in sorted(job.glob("*/result.json"))]
    summary = {
        **snapshot,
        "report_runner_version": RUNNER_VERSION,
        "trials": trials,
        **aggregate(trials, snapshot["tasks"]),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    fields = [
        "task",
        "benchmark",
        "family",
        "seed",
        "valid",
        "status",
        "invalid_reason",
        "success",
        "primary_metric",
        "primary_score",
        "return",
        "steps",
        "terminal_reason",
        "elapsed_seconds",
        "resource_monitor_missing",
        "resource_enforced",
        "invalid_actions",
        "error_category",
        "outcome_class",
        "digest",
        "trial",
    ]
    with (output_dir / "episodes.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(trials)
    fmt = lambda value: "—" if value is None else f"{value:.4f}"
    lines = [
        "# Game evaluation",
        "",
        f"Suite: {snapshot['suite']}; agent: {snapshot['agent']}; model: {snapshot['model']}.",
        "",
        f"Valid episodes: {summary['valid_trials']}/{summary['expected_trials']}; complete: {summary['complete']}.",
        "",
        "| Benchmark | Valid / planned | Primary metric | Observed mean | Complete family macro | Success definition | Successes |",
        "| --- | ---: | --- | ---: | ---: | --- | ---: |",
    ]
    notes = []
    for benchmark, group in summary["benchmarks"].items():
        lines.append(
            f"| {benchmark} | {group['valid']}/{group['expected']} | {group['primary_metric']} | "
            f"{fmt(group['mean_primary_score'])} | {fmt(group['macro_primary_score'])} | "
            f"{group['success_label'] or '—'} | "
            + (f"{group['successes']}/{group.get('completion_valid', group['valid'])} |"
               if group.get('completion_expected', group['expected']) else "— |")
        )
        if "crafter_score" in group:
            notes += [
                "",
                f"Crafter achievement score: {fmt(group['crafter_score'])} (0–100); individual achievement rates in summary.json.",
                "",
            ]
    lines += notes
    if any("scored_expected" in group for group in summary["benchmarks"].values()):
        lines += [
            "",
            "## Per-scenario results",
            "",
            "| Task | Status | Objective completed | Native return | Native tics | Native statistics |",
            "| --- | --- | --- | ---: | ---: | --- |",
        ]
        for row in trials:
            if "scored_expected" not in summary["benchmarks"][row["benchmark"]]:
                continue
            metrics = row["native_metrics"]
            keys = ("killcount", "health", "armor", "ammo2", "itemcount", "selected_weapon", "selected_weapon_ammo")
            stats = ", ".join(f"{key}: {metrics[key]}" for key in keys if key in metrics) or "—"
            objective = ("yes" if row["success"] else "no") if row["valid"] and row["success"] is not None else "—"
            lines.append(f"| {row['task']} | {row['status']} | {objective} | {fmt(row['return'])} | "
                         f"{metrics.get('native_tics', '—')} | {stats} |")
        lines += ["", "The success denominator covers objective tasks only. Native returns are reported by scenario."]
    lines += [
        "",
        "No cross-benchmark score is computed. A Crafter milestone failure is still a valid achievement score.",
        "One fresh session per frozen instance; no automatic retries. Valid failures remain counted.",
        "Environment faults, infrastructure failures and invalid evidence are separate invalid outcomes, not model failures.",
        "Live grading trusts the isolated simulator and collection boundary. Privileged grading independently replays the submitted actions in the verifier.",
        "Partial observed means are labelled; complete macro scores require every planned episode to be valid.",
        "This is a fixed-model public-network integration track, not the original RL training protocol or an official leaderboard reproduction.",
        "",
        f"[Episode CSV](episodes.csv) · [Full summary and evidence paths](summary.json) · [Harbor run lock]({configuration_link})",
    ]
    (output_dir / "REPORT.md").write_text("\n".join(lines) + "\n")
    return summary


def write_harbor_report(job):
    """Read task identity and run settings from Harbor's lock, not a second run snapshot."""
    from harbor.publisher.packager import Packager
    from config_schema import validate_instance
    from game_schemas import register_schemas

    job = Path(job).resolve()
    provenance = json.loads((job / "game-provenance.json").read_text())
    validate_report_code(provenance)
    lock = json.loads((job / "lock.json").read_text())
    config = json.loads((job / "config.json").read_text())
    register_schemas()
    records = {}
    agents = set()
    for trial in lock["trials"]:
        task = trial["task"]
        if task["type"] != "local" or not task.get("path"):
            raise ValueError("game summary requires retained local task copies")
        name = task["name"]
        if name in records:
            raise ValueError("game summary requires one attempt and one agent per task")
        path = Path(task["path"])
        actual, _ = Packager.compute_content_hash(path)
        if "sha256:" + actual != task["digest"]:
            raise ValueError(f"{name}: task contents differ from Harbor lock")
        instance = json.loads((path / "tests/instance.json").read_text())
        validate_instance(instance)
        records[name] = {k: instance[k] for k in ("benchmark", "family", "seed", "metric_spec")}
        records[name]["digest"] = task["digest"]
        agents.add((trial["agent"].get("name"), trial["agent"].get("model_name")))
    if not records or len(agents) != 1:
        raise ValueError("game summary requires a nonempty single-agent job")
    # Result locks must belong to the same planned task contents; rejected attempts
    # cannot silently replace a task or improve the denominator.
    for result in job.glob("*/result.json"):
        trial_lock = json.loads((result.parent / "lock.json").read_text())
        task = trial_lock["task"]
        if task["name"] not in records or task["digest"] != records[task["name"]]["digest"]:
            raise ValueError("trial task differs from Harbor job lock")
    agent, model = next(iter(agents))
    context = {
        "suite": config["job_name"],
        "agent": agent,
        "model": model,
        "tasks": records,
        "report_code_sha256": provenance["report_code_sha256"],
        "configuration_source": "../config.json",
        "lock_source": "../lock.json",
    }
    return write_report(job, context, output=job / "game-report", configuration_link="../lock.json")


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    args = parser.parse_args()
    summary = write_harbor_report(args.job)
    print(json.dumps(summary["benchmarks"], indent=2))
    return 0 if summary["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
