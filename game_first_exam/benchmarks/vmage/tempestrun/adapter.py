"""Thin trusted entry point for externally installed native V-MAGE TempestRun."""
import importlib.util
from pathlib import Path
try:
    from ..common.vmage_bridge import NativeAdapter
except ImportError:
    from vmage_bridge import NativeAdapter

_spec = importlib.util.spec_from_file_location('_vmage_tempestrun_schema', Path(__file__).with_name('instance_schema.py'))
_schema = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_schema)
BENCHMARK = 'vmage_tempestrun'

class Adapter(NativeAdapter):
    GAME = 'tempestrun'
    SCHEMA = _schema
