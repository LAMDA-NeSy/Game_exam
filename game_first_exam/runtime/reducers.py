"""Versioned, explicit aggregation policies. Changes require a new registry key."""
import math
from statistics import mean


def family_macro(rows, complete):
    return {}


def crafter_achievements(rows, complete):
    if not rows:
        return {"crafter_score": None, "observed_crafter_score": None, "achievement_success_rates": {}}
    keys = set(rows[0]["native_metrics"]["achievements"])
    if not keys or any(set(row["native_metrics"]["achievements"]) != keys for row in rows):
        raise ValueError("incompatible achievement vectors")
    for row in rows:
        if any(type(v) is not int or v not in (0, 1) for v in row["native_metrics"]["achievements"].values()):
            raise ValueError("invalid binary achievement vector")
    rates = {key: mean(row["native_metrics"]["achievements"][key] for row in rows) for key in sorted(keys)}
    score = math.expm1(mean(math.log1p(100 * rate) for rate in rates.values()))
    return {"achievement_success_rates": rates, "observed_crafter_score": score,
            "crafter_score": score if complete else None}


def vgc_win_rate(rows, complete):
    """Win rate across a family of frozen battle instances (each a single episode)."""
    if not rows:
        return {"win_rate": None, "observed_win_rate": None, "wins": 0, "games": 0}
    for row in rows:
        win = row.get("native_metrics", {}).get("win")
        if type(win) is not int or win not in (0, 1):
            raise ValueError("invalid VGC win flag")
    wins = sum(1 for row in rows if row["native_metrics"]["win"] == 1)
    games = len(rows)
    rate = wins / games
    return {"wins": wins, "games": games, "observed_win_rate": rate,
            "win_rate": rate if complete else None}


REGISTRY = {("family_macro", "1.0.0"): family_macro,
            ("crafter_achievements", "1.0.0"): crafter_achievements,
            ("vgc_win_rate", "1.0.0"): vgc_win_rate}


def resolve(name, version):
    try:
        return REGISTRY[(name, version)]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unsupported reducer: {name!r}@{version!r}") from exc
