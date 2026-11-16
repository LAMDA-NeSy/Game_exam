"""Fail-closed configuration checks shared by preflight, service and verifier; stdlib only."""
import importlib.util
import math
import re
from pathlib import Path

from reducers import resolve

PROTOCOL = "game-standard/2.2"
INSTANCE_SCHEMA = "game-instance/2.2"
SUITE_SCHEMA = "game-suite/2.1"
ADAPTER_VERSION = "1.0.0"
HASH = re.compile(r"[0-9a-f]{64}")
COMMON = {"schema_version", "protocol", "adapter_version", "capabilities", "benchmark", "env_id", "family",
          "seed", "max_steps", "initial_state_sha256", "observation_profile", "metric_spec"}
# Only trusted host code may register schemas. Containers load one fixed sibling file.
_SCHEMAS = {}


def register_instance_schema(schema):
    name = schema.BENCHMARK
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_-]+", name):
        raise ValueError("invalid schema benchmark")
    if schema.SCHEMA_VERSION != "1.0.0" or not callable(schema.validate):
        raise ValueError("unsupported instance schema contract")
    for field in ("FIELDS", "METRICS", "PROFILES"):
        values = getattr(schema, field)
        if not isinstance(values, (set, frozenset)) or any(not isinstance(v, str) or not v for v in values):
            raise ValueError("invalid schema declaration: " + field)
    if schema.FIELDS & COMMON:
        raise ValueError("game fields must not override common fields")
    for reducer in schema.REDUCERS:
        resolve(*reducer)
    if name in _SCHEMAS and _SCHEMAS[name] is not schema:
        raise ValueError("duplicate trusted schema registration: " + name)
    _SCHEMAS[name] = schema
    return schema


def instance_schema(benchmark):
    if benchmark not in _SCHEMAS:
        # No sys.path search, environment override, or instance-supplied import path.
        path = Path(__file__).resolve().with_name("instance_schema.py")
        if path.is_file():
            spec = importlib.util.spec_from_file_location("_bundled_game_schema", path)
            schema = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(schema)
            if schema.BENCHMARK != benchmark:
                raise ValueError("bundled schema does not match benchmark")
            register_instance_schema(schema)
    if benchmark not in _SCHEMAS:
        raise ValueError("unknown benchmark schema")
    return _SCHEMAS[benchmark]


def validate_engine_versions(actual, expected):
    if actual != expected:
        raise ValueError("engine versions disagree with the supported frozen profile")
    if not actual or any(not isinstance(v, str) or not re.fullmatch(r"\d+(?:\.\d+)+(?:[a-z0-9.-]*)", v) for v in actual.values()):
        raise ValueError("engine versions must be exact versions")


def mapping(value, required, allowed=None, label="configuration"):
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    missing = set(required) - value.keys()
    unknown = value.keys() - (set(required) if allowed is None else set(allowed))
    if missing or unknown:
        raise ValueError(f"{label}: missing={sorted(missing)}, unknown={sorted(unknown)}")


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")


def positive(value, label):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{label} must be finite and positive")


def validate_capabilities(value):
    mapping(value, {"images", "action_mode", "timing", "native_truncation"}, label="capabilities")
    for key in ("images", "native_truncation"):
        if type(value[key]) is not bool:
            raise ValueError(f"capability {key} must be boolean")
    if value["timing"] != "action-stepped" or value["action_mode"] not in {"enum", "text"}:
        raise ValueError("unsupported timing or action mode for this protocol")


def validate_metric_spec(value):
    mapping(value, {"primary", "reducer", "reducer_version", "success_label"}, label="metric_spec")
    for key, item in value.items():
        text(item, f"metric_spec.{key}")
    resolve(value["reducer"], value["reducer_version"])


def validate_instance(value):
    if not isinstance(value, dict) or not isinstance(value.get("benchmark"), str):
        raise TypeError("instance benchmark must be a string")
    benchmark = value["benchmark"]
    schema = instance_schema(benchmark)
    mapping(value, COMMON | schema.FIELDS, label="instance")
    if value["schema_version"] != INSTANCE_SCHEMA or value["protocol"] != PROTOCOL:
        raise ValueError("unsupported instance schema or protocol version")
    if value["adapter_version"] != ADAPTER_VERSION:
        raise ValueError("unsupported adapter contract version")
    for key in ("env_id", "family", "initial_state_sha256"):
        text(value[key], key)
    if not HASH.fullmatch(value["initial_state_sha256"]):
        raise ValueError("initial_state_sha256 must be a SHA256 digest")
    if type(value["seed"]) is not int or not 0 <= value["seed"] < 2**31:
        raise ValueError("seed must be an integer in [0, 2**31)")
    if value["max_steps"] is not None and (type(value["max_steps"]) is not int or value["max_steps"] < 1):
        raise ValueError("max_steps must be a positive integer or null (no public action cap)")
    if value["observation_profile"] not in schema.PROFILES:
        raise ValueError("unsupported observation profile")
    validate_metric_spec(value["metric_spec"])
    if value["metric_spec"]["primary"] not in schema.METRICS:
        raise ValueError("unknown primary metric for benchmark")
    if (value["metric_spec"]["reducer"], value["metric_spec"]["reducer_version"]) not in schema.REDUCERS:
        raise ValueError("reducer not supported by benchmark")
    validate_capabilities(value["capabilities"])
    schema.validate(value)
    return value


def validate_spec(spec, instance):
    if not isinstance(spec, dict) or not {"action_schema", "capabilities", "adapter_version"} <= spec.keys():
        raise ValueError("adapter spec lacks required contract fields")
    if spec["adapter_version"] != instance["adapter_version"] or spec["capabilities"] != instance["capabilities"]:
        raise ValueError("adapter spec disagrees with frozen capabilities/version")
    validate_capabilities(spec["capabilities"])
    schema = spec["action_schema"]
    mode = spec["capabilities"]["action_mode"]
    field = "enum" if mode == "enum" else "pattern"
    mapping(schema, {"type", field}, {"type", field, "max_length"}, "action_schema")
    if schema["type"] != "string":
        raise ValueError("only string actions are supported")
    if "max_length" in schema and (type(schema["max_length"]) is not int or not 1 <= schema["max_length"] <= 4096):
        raise ValueError("invalid max_length")
    if mode == "enum":
        choices = schema["enum"]
        if not isinstance(choices, list) or not choices or any(not isinstance(v, str) or not v for v in choices) or len(set(choices)) != len(choices):
            raise ValueError("invalid action enum")
    else:
        text(schema["pattern"], "pattern")
        re.compile(schema["pattern"])
    return spec


def validate_suite(suite):
    mapping(suite, {"schema_version", "name", "tier", "version", "files_images", "tasks"}, label="suite")
    if suite["schema_version"] != SUITE_SCHEMA or suite["tier"] not in {"smoke", "development", "evaluation"}:
        raise ValueError("unsupported suite schema/tier")
    text(suite["name"], "suite name"); text(suite["version"], "suite version")
    images = suite["files_images"]
    if not isinstance(images, list) or not images or any(not isinstance(n, str) or not re.fullmatch(r"[a-z0-9-]+", n) for n in images) or len(set(images)) != len(images):
        raise ValueError("invalid files_images")
    if not isinstance(suite["tasks"], list) or not suite["tasks"]:
        raise ValueError("empty task suite")
    names = set()
    for row in suite["tasks"]:
        mapping(row, {"name", "benchmark", "family"}, label="suite task")
        for key, value in row.items():
            text(value, key)
        instance_schema(row["benchmark"])
        if Path(row["name"]).name != row["name"] or row["name"] in names:
            raise ValueError("invalid/duplicate task or unknown benchmark")
        names.add(row["name"])
