"""Stdlib installer and verifier for the pinned, externally fetched native payload.

No V-MAGE implementation or asset bytes are distributed by this module.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import urllib.request

COMMIT = '95d5d4a445bb0b75cce765c93107d87f84613e4d'
ARCHIVE_SHA256 = '1047daa50004003eb9848205e1c420679e51d54d9a38acd3155da4aa8680e919'
URL = 'https://codeload.github.com/CSU-JPG/V-MAGE/tar.gz/' + COMMIT


def manifest(path=None):
    return json.loads(Path(path or Path(__file__).with_name('SOURCE.json')).read_text())


def manifest_digest(value):
    return hashlib.sha256(json.dumps(value['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify_source(root, metadata=None):
    root = Path(root).resolve()
    metadata = metadata or manifest()
    if metadata['upstream_commit'] != COMMIT or metadata['archive_sha256'] != ARCHIVE_SHA256:
        raise ValueError('untrusted V-MAGE provenance')
    if manifest_digest(metadata) != metadata['source_manifest_sha256']:
        raise ValueError('V-MAGE manifest mismatch')
    for relative, expected in metadata['files'].items():
        p = PurePosixPath(relative)
        if p.is_absolute() or '..' in p.parts:
            raise ValueError('unsafe native manifest path')
        path = root.joinpath(*p.parts)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('native source/asset mismatch: ' + relative)
    return metadata


def install(destination, archive=None):
    metadata = manifest()
    if archive:
        data = Path(archive).read_bytes()
    else:
        with urllib.request.urlopen(URL, timeout=180) as response:
            data = response.read()
    if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
        raise ValueError('V-MAGE archive hash mismatch')
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError('native destination must be empty')
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        prefix = 'V-MAGE-' + COMMIT + '/'
        for relative, digest in metadata['files'].items():
            member = tar.getmember(prefix + relative)
            if not member.isfile():
                raise ValueError('native runtime payload must contain regular files')
            content = tar.extractfile(member).read()
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError('archive member hash mismatch: ' + relative)
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            path.chmod(0o644)
    verify_source(destination, metadata)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', required=True)
    parser.add_argument('--archive', help='Optional fixed archive for offline builds')
    args = parser.parse_args()
    install(args.destination, args.archive)
