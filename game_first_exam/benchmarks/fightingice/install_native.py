"""Install a hash-checked native release outside the task source tree; stdlib only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile


def checked(data, expected):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('upstream file digest mismatch')
    return data


def verify(destination):
    destination = Path(destination)
    installed = json.loads((destination / 'installation.json').read_text())
    source = json.loads(Path(__file__).with_name('SOURCE.json').read_text())
    if installed['source'] != source or 'FightingICE.jar' not in installed['files']:
        raise ValueError('native installation does not match the frozen source')
    for name, digest in installed['files'].items():
        checked((destination / name).read_bytes(), digest)
    for name, digest in source['resources'].items():
        checked((destination / name).read_bytes(), digest)


def install(destination, engine_archive=None, resources_archive=None, resources_dir=None):
    source = json.loads(Path(__file__).with_name('SOURCE.json').read_text())
    destination = Path(destination)
    if destination.exists():
        raise ValueError('choose a new native installation directory')
    with tempfile.TemporaryDirectory() as temporary:
        def archive(supplied, url, name):
            if supplied:
                return Path(supplied)
            target = Path(temporary) / name
            with urllib.request.urlopen(url, timeout=120) as response, target.open('wb') as stream:
                shutil.copyfileobj(response, stream)
            return target

        engine = archive(engine_archive, source['engine_url'], 'engine.zip')
        checked(engine.read_bytes(), source['engine_sha256'])
        selected = {}
        with zipfile.ZipFile(engine) as bundle:
            for info in bundle.infolist():
                relative = Path(*Path(info.filename).parts[1:])
                if info.is_dir() or relative.is_absolute() or '..' in relative.parts:
                    continue
                if str(relative) == 'FightingICE.jar' or (relative.parts[0] == 'lib' and relative.suffix == '.jar'):
                    selected[str(relative)] = bundle.read(info)
        if resources_dir:
            for name, digest in source['resources'].items():
                selected[name] = checked((Path(resources_dir) / name).read_bytes(), digest)
        else:
            resources = archive(resources_archive, source['resources_url'], 'resources.zip')
            with zipfile.ZipFile(resources) as bundle:
                for name, digest in source['resources'].items():
                    selected[name] = checked(bundle.read(name), digest)
        for name, data in selected.items():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (destination / 'data/ai').mkdir(parents=True)
        (destination / 'installation.json').write_text(json.dumps({
            'source': source, 'files': {name: hashlib.sha256(data).hexdigest() for name, data in selected.items()}
        }, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--engine-archive', type=Path)
    parser.add_argument('--resources-archive', type=Path)
    parser.add_argument('--resources-dir', type=Path)
    args = parser.parse_args()
    install(args.destination, args.engine_archive, args.resources_archive, args.resources_dir)
