"""2026 archive schedule and result columns, without executing archive code."""
import csv
from itertools import combinations, groupby
import json
import math
from pathlib import Path
import re
from statistics import mean
import sys


TRACKS = {
    "rushdown": ("GARNET", "MctsAi23i", ("comboCount", "ProximityScore", "corneredFrames")),
    "zoning": ("NEZ", "MctsAiZoning", ("ProjectileScore", "ProximityScore", "AntiAirCount")),
}
DUEL_PLAYERS = ("model-a", "model-b")
SPEEDRUN_PROFILE = "speedrun-mcts-framedata-v1"
SPEEDRUN_LOSS_FRAMES = 4200


def duel_schedule(track, pairs):
    if type(pairs) is not int or pairs < 1:
        raise ValueError("side-swapped pair count must be a positive integer")
    a, b = DUEL_PLAYERS
    return [
        dict(track=track, league="standard", character=TRACKS[track][0], p1=p1, p2=p2, game=i)
        for i in range(1, pairs + 1) for p1, p2 in ((a, b), (b, a))
    ]


def round_points(hp, other):
    return 1 if hp > other else .5 if hp == other else 0


def schedule(track, entries, league, mcts_only=False):
    character, mcts, _ = TRACKS[track]
    names = list(entries)
    if (not names or len(set(names)) != len(names)
            or any(not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", n) or n == "organizer" for n in names)):
        raise ValueError("use distinct lowercase controller names, excluding official baselines")
    opponents = [mcts] if mcts_only or league == "speedrun" else [mcts, "organizer"]
    if league == "standard":
        pairs, count = combinations([*names, *opponents], 2), 1
    elif league in ("style", "speedrun"):
        pairs, count = ((entry, foe) for entry in names for foe in opponents), 5
    else:
        raise ValueError("unknown league")
    return [
        dict(track=track, league=league, character=character, p1=a, p2=b, game=i)
        for p1, p2 in pairs for a, b in ((p1, p2), (p2, p1)) for i in range(1, count + 1)
    ]


def read_match(track, point_file, style_file):
    with point_file.open(newline="") as stream:
        points = [tuple(map(int, row)) for row in csv.reader(stream)]
    if len(points) != 3 or any(len(row) != 4 or row[0] != i or not 1 <= row[3] <= 3600
                               or max(row[1:3]) > 400 for i, row in enumerate(points, 1)):
        raise ValueError("invalid three-round native point CSV")
    fields = [f"P{side}_{field}" for side in (1, 2) for field in TRACKS[track][2]]
    with style_file.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != fields:
            raise ValueError("unexpected native style columns")
        style = [{key: float(row[key]) for key in fields} for row in reader]
    if len(style) != 3 or not all(math.isfinite(n) for row in style for n in row.values()):
        raise ValueError("invalid three-round native style CSV")
    return {"points": points, "style": style}


def summarize(schedule_rows, results):
    """Return archive-derived metrics. Never invent a combined style ranking."""
    if not schedule_rows or len(results) != len(schedule_rows):
        raise ValueError("incomplete match matrix")
    league, track = schedule_rows[0]["league"], schedule_rows[0]["track"]
    _, mcts, fields = TRACKS[track]
    baselines = {mcts, "organizer"}
    totals = {}
    for match, result in zip(schedule_rows, results, strict=True):
        if match["track"] != track or match["league"] != league:
            raise ValueError("report one track and league at a time")
        p1, p2 = match["p1"], match["p2"]
        for side, name, foe in ((1, p1, p2), (2, p2, p1)):
            if league == "style" and name in baselines:
                continue
            row = totals.setdefault(name, dict(games=0, round_points=0, remaining_hp=0,
                                               speed_frames=0, style={field: [] for field in fields}))
            row["games"] += 1
            for (_, hp1, hp2, frames), values in zip(result["points"], result["style"], strict=True):
                hp, other = (hp1, hp2) if side == 1 else (hp2, hp1)
                row["round_points"] += round_points(hp, other)
                row["remaining_hp"] += hp
                if league == "style" and foe in baselines:
                    row["speed_frames"] += frames if hp >= other else SPEEDRUN_LOSS_FRAMES
                for field in fields:
                    row["style"][field].append(values[f"P{side}_{field}"])
    for row in totals.values():
        row["style"] = {field: mean(values) for field, values in row["style"].items()}
        if league == "standard":
            del row["speed_frames"]
    report = {"track": track, "league": league, "controllers": totals}
    if league == "standard":
        ordered = sorted(totals, key=lambda name: (-totals[name]["round_points"],
                                                   -totals[name]["remaining_hp"], name))
        standings, previous = [], None
        for index, name in enumerate(ordered, 1):
            score = totals[name]["round_points"], totals[name]["remaining_hp"]
            if score != previous:
                standings.append({"rank": index, "controllers": []})
                previous = score
            standings[-1]["controllers"].append(name)
        report["standings"] = standings
    return report


def duel_report(rows, results, models):
    report = summarize(rows, results)
    report.update(mode="duel", models=models, pairs=len(rows) // 2, audio=False, matches=[
        {**match, "rounds": result["points"],
         "round_points": {match["p1"]: sum(round_points(hp1, hp2) for _, hp1, hp2, _ in result["points"]),
                          match["p2"]: sum(round_points(hp2, hp1) for _, hp1, hp2, _ in result["points"])}}
        for match, result in zip(rows, results, strict=True)
    ])
    return report


def speedrun_report(rows, results, models=None):
    if not rows or len(rows) != len(results):
        raise ValueError("incomplete speedrun match matrix")
    track = rows[0]["track"]
    _, baseline, _ = TRACKS[track]
    entries = dict.fromkeys(name for match in rows for name in (match["p1"], match["p2"]) if name != baseline)
    if rows != schedule(track, entries, "speedrun"):
        raise ValueError("speedrun requires five matches on each side against the track's MCTS")
    totals = {entry: dict(games=0, wins=0, draws=0, losses=0, speed_frames=0) for entry in entries}
    matches = []
    for match, result in zip(rows, results, strict=True):
        entry_is_p1 = match["p2"] == baseline
        entry = match["p1"] if entry_is_p1 else match["p2"]
        total = totals[entry]
        total["games"] += 1
        points = result["points"]
        if len(points) != 3:
            raise ValueError("incomplete speedrun rounds")
        rounds = []
        for number, hp1, hp2, frames in points:
            hp, other = (hp1, hp2) if entry_is_p1 else (hp2, hp1)
            outcome = "loss" if hp < other else "win" if hp > other else "draw"
            scored = SPEEDRUN_LOSS_FRAMES if outcome == "loss" else frames
            total[{"win": "wins", "draw": "draws", "loss": "losses"}[outcome]] += 1
            total["speed_frames"] += scored
            rounds.append(dict(round=number, p1_hp=hp1, p2_hp=hp2, elapsed_frames=frames,
                               scored_frames=scored, outcome=outcome))
        matches.append({**match, "entry": entry, "rounds": rounds})
    for total in totals.values():
        total["rounds"] = total["games"] * 3
        total["penalty_rounds"] = total["losses"]
        total["average_frames"] = total["speed_frames"] / total["rounds"]
        total["average_seconds"] = total["average_frames"] / 60

    def score(entry):
        # Every entry plays the same number of rounds, so compare integer totals.
        return totals[entry]["speed_frames"]

    standings, rank = [], 1
    for _, group in groupby(sorted(entries, key=lambda entry: (score(entry), entry)), key=score):
        controllers = list(group)
        standings.append(dict(rank=rank, controllers=controllers))
        rank += len(controllers)
    report = dict(profile=SPEEDRUN_PROFILE, league="speedrun", track=track, baseline=baseline, audio=False,
                  controllers=totals, standings=standings, matches=matches)
    if models:
        report["models"] = models
    return report


def verify_evidence(folder, match):
    points, = (folder / "engine/log/point").glob("*.csv")
    style, = (folder / "engine/log/style").glob("*.csv")
    native = read_match(match["track"], points, style)
    recorded = json.loads((folder / "match-result.json").read_text())
    callbacks = recorded.pop("callbacks")
    points = [list(row) for row in native["points"]]
    if recorded != {"points": points, "style": native["style"]}:
        raise ValueError("engine result disagrees with native CSVs")
    expected = {str(side) for side, name in enumerate((match["p1"], match["p2"]), 1)
                if name != TRACKS[match["track"]][1]}
    if set(callbacks) != expected:
        raise ValueError("missing or unknown callback evidence")
    for record in callbacks.values():
        if (record["controller_disconnected"] is not False or record["round_results"] != points
                or type(record["callbacks"]) is not int or record["callbacks"] < 1):
            raise ValueError("controller failed or native round callbacks disagree with the point CSV")
    return native


if __name__ == "__main__":
    print(json.dumps(verify_evidence(Path(sys.argv[1]), json.loads(sys.argv[2]))))
