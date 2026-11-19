"""Thin trusted entry point for externally installed native V-MAGE Race."""
import importlib.util
from pathlib import Path
try:
    from ..common.vmage_bridge import NativeAdapter
except ImportError:
    from vmage_bridge import NativeAdapter

_spec = importlib.util.spec_from_file_location('_vmage_race_schema', Path(__file__).with_name('instance_schema.py'))
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
BENCHMARK = 'vmage_race'

class Adapter(NativeAdapter):
    GAME = 'race'
    SCHEMA = _schema
