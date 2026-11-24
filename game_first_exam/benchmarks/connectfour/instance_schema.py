"""Frozen Connect Four settings shared by the host and isolated verifier."""

BENCHMARK = "connectfour"
SCHEMA_VERSION = "1.0.0"
FIELDS = {"engine_version", "opponent_policy", "opponent_seed", "controlled_agent"}
PROFILES = {"native-rgb-board-v1"}
METRICS = {"success"}
REDUCERS = {("family_macro", "1.0.0")}


def validate(value):
    expected = {
        "env_id": "connect_four_v3", "family": "fixed-opponent",
        "engine_version": "1.26.1", "controlled_agent": "player_0",
        "opponent_policy": "block-win-hash-v1", "opponent_seed": 2117382936,
        "capabilities": {"images": True, "action_mode": "enum", "timing": "action-stepped",
                         "native_truncation": True},
        "metric_spec": {"primary": "success", "reducer": "family_macro",
                        "reducer_version": "1.0.0", "success_label": "native_red_win"},
    }
    for key, frozen in expected.items():
        if value[key] != frozen:
            raise ValueError(f"Unsupported Connect Four {key}")
    if value["max_steps"] != 21:
        raise ValueError("Connect Four has at most 21 Red turns")
