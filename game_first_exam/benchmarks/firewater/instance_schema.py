SCHEMA_VERSION = "1.0.0"
BENCHMARK = "firewater"
FIELDS = {"engine_commit"}
METRICS = {"success"}
PROFILES = {"native-rgb-v1"}
REDUCERS = {("family_macro", "1.0.0")}


def validate(value):
    if value["engine_commit"] != "e5ddb16df85b91a1d17bb0577621cc7c5e65d738":
        raise ValueError("unknown GameWorld-Games version")
    if (value["env_id"], value["family"], value["max_steps"]) != ("forest-temple-level-1", "forest-exit", 800):
        raise ValueError("unknown GameWorld task configuration")
