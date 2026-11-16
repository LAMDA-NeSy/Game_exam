"""Verify the staged Python-only TextWorld runtime against the native dependency lock.

The official wheel is tagged x86 because it bundles authoring executables. Frozen .z8
execution uses native Jericho, not those executables; this is an explicit packaging profile.
"""
from importlib import metadata
from pathlib import Path

import jericho
import textworld
from packaging.requirements import Requirement

assert metadata.version('textworld') == '1.7.0'
assert metadata.version('jericho') == '3.3.1'
for dependency in metadata.requires('textworld') or []:
    requirement = Requirement(dependency)
    if requirement.marker is None or requirement.marker.evaluate({'extra': ''}):
        assert metadata.version(requirement.name) in requirement.specifier, dependency
assert not list(Path(textworld.__file__).parent.rglob('*.so')), 'unexpected Python native extensions in staged wheel'
assert jericho.FrotzEnv is not None
print('TextWorld Python runtime dependencies checked; native Jericho imports successfully.')
