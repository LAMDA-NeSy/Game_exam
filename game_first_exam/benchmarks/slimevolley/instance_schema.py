"""Frozen native pixel match configuration, shared by preflight, sim and verifier."""

from config_schema import validate_engine_versions

SCHEMA_VERSION = "1.0.0"
BENCHMARK = "slimevolley"
FIELDS = {"engine_versions", "engine_commit", "native_max_steps", "opponent"}
METRICS = {"native_return"}
PROFILES = {"native-rgb-v1"}
REDUCERS = {("family_macro", "1.0.0")}
ENGINE_COMMIT = "8ac22434fc5a587a3395311f7854aeda17d10303"
ENGINE_VERSIONS = {
    "slimevolleygym": "0.1.0",
    "gym": "0.25.0",
    "numpy": "1.26.4",
    "opencv-python-headless": "4.11.0.86",
}


def validate(value):
    validate_engine_versions(value["engine_versions"], ENGINE_VERSIONS)
    if value["engine_commit"] != ENGINE_COMMIT or value["opponent"] != "native-baseline":
        raise ValueError("unsupported SlimeVolley engine or opponent")
    if (value["env_id"] != "SlimeVolleyNoFrameskip-v0" or value["family"] != "pixel-vs-baseline"
            or type(value["native_max_steps"]) is not int or value["native_max_steps"] != 3000
            or value["max_steps"] is not None):
        raise ValueError("unsupported native SlimeVolley match configuration")
    if value["capabilities"] != {
        "images": True, "action_mode": "enum", "timing": "action-stepped", "native_truncation": True,
    }:
        raise ValueError("SlimeVolley requires the native RGB action-stepped profile")
