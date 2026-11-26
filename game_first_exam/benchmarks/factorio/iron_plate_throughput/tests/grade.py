"""Feed the sealed numeric trajectory to FLE's original Inspect scorer."""
import hashlib
import json
import math
from pathlib import Path


def validate(episode, task):
    if episode["task"] != task.task_key or episode["sealed"] is not True or episode["fault"] is not None:
        raise ValueError("Unsealed, mismatched or failed FLE episode")
    steps = episode["steps"]
    if task.trajectory_length != 64 or not isinstance(steps, list) or len(steps) > task.trajectory_length:
        raise ValueError("Invalid trajectory budget")
    for n, step in enumerate(steps, start=1):
        if step["number"] != n or hashlib.sha256(step["code"].encode()).hexdigest() != step["code_sha256"]:
            raise ValueError("Invalid step trace")
        for key in ("reward", "production_score", "automated_production_score"):
            if type(step[key]) not in (int, float) or not math.isfinite(step[key]):
                raise ValueError(f"Invalid {key}")
        if any(type(step[k]) is not bool for k in ("terminated", "truncated", "error_occurred")):
            raise ValueError("Invalid native step flags")
        if n < len(steps) and (step["terminated"] or step["truncated"]):
            raise ValueError("Actions after native termination")
    return steps


def grade(episode, output):
    from fle.eval.inspect.eval_set import create_throughput_task
    from fle.eval.inspect.integration.solver import TrajectoryData
    from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import iron_plate_throughput as task
    from inspect_ai import eval as evaluate
    from inspect_ai.solver import solver
    from inspect_ai.util import store_as

    steps = validate(episode, task)

    @solver
    def recorded_trajectory():
        async def solve(state, generate):
            trajectory = store_as(TrajectoryData)
            trajectory.scores = [step["production_score"] for step in steps]
            trajectory.total_steps = len(steps)
            trajectory.final_score = trajectory.scores[-1] if steps else 0.0
            trajectory.production_score = trajectory.final_score
            return state
        return solve

    evaluation = create_throughput_task(task.task_key, target=task.quota, solver=recorded_trajectory())
    log, = evaluate(evaluation, model="mockllm/model", log_dir=str(output / "inspect"),
                    log_realtime=False, display="none")
    if log.status != "success" or not log.samples or log.samples[0].error:
        raise RuntimeError("FLE Inspect grading failed (see the verifier Inspect log)")
    score, = log.samples[0].scores.values()
    if not score.metadata or score.metadata.get("has_error") is not False:
        raise ValueError("Upstream scorer did not return a valid trajectory score")
    rewards = {"fle_inspect_score": float(score.value),
               "iron_plate_goal_reached": int(bool(steps and steps[-1]["terminated"]))}
    (output / "reward.json").write_text(json.dumps(rewards, allow_nan=False))


if __name__ == "__main__":
    grade(json.loads(Path("/evidence/episode.json").read_text()), Path("/logs/verifier"))
