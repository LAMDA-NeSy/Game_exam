"""Execution settings, separate from the unchanged native environment instance."""
import hashlib
import json
import math


def validate_mode(config):
    if not isinstance(config, dict):
        raise ValueError('unsupported game execution settings')
    expected_version = {'privileged': '1.0.0', 'realtime': '1.1.0'}.get(config.get('mode'))
    if expected_version is None or config.get('version') != expected_version:
        raise ValueError('unsupported game execution settings version')
    if config.get('mode') == 'privileged':
        if set(config) != {'mode', 'version', 'max_actions'} or type(config['max_actions']) is not int or not 0 < config['max_actions'] <= 10000:
            raise ValueError('invalid replay action limit')
    elif config.get('mode') == 'realtime':
        if set(config) != {'mode', 'version', 'tick_seconds', 'idle_action', 'max_plan_steps'}:
            raise ValueError('invalid realtime settings')
        dt = config['tick_seconds']
        if type(dt) not in (int, float) or not math.isfinite(dt) or not .01 <= dt <= 10:
            raise ValueError('invalid tick interval')
        if config['idle_action'] != 'noop' or type(config['max_plan_steps']) is not int or not 1 <= config['max_plan_steps'] <= 256:
            raise ValueError('unsupported idle action or plan bound')
    else:
        raise ValueError('unsupported execution mode')
    return config


def mode_hash(config):
    validate_mode(config)
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
