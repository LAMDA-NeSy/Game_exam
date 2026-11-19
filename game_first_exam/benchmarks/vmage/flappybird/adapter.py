"""Thin trusted entry point for externally installed native V-MAGE FlappyBird."""
import importlib.util
from pathlib import Path
try:
    from ..common.vmage_bridge import NativeAdapter
except ImportError:
    from vmage_bridge import NativeAdapter

_spec = importlib.util.spec_from_file_location('_vmage_flappybird_schema', Path(__file__).with_name('instance_schema.py'))
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
BENCHMARK = 'vmage_flappybird'

class Adapter(NativeAdapter):
    GAME = 'flappybird'
    SCHEMA = _schema
