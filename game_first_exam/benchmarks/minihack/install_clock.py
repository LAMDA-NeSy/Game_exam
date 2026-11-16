"""Build unmodified libfaketime against the simulator's libc; no engine patch."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

VERSION = '0.9.12'
SHA256 = '4fc32218697c052adcdc5ee395581f2554ca56d086ac817ced2be0d6f1f8a9fa'


def main():
    url = f'https://codeload.github.com/wolfcw/libfaketime/tar.gz/refs/tags/v{VERSION}'
    with urllib.request.urlopen(url, timeout=90) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('libfaketime source digest mismatch')
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / 'clock.tar.gz'
        archive.write_bytes(data)
        with tarfile.open(archive) as source:
            source.extractall(tmp, filter='data')
        source = Path(tmp) / f'libfaketime-{VERSION}'
        subprocess.run(['make', '-C', str(source / 'src'), 'libfaketime.so.1'], check=True)
        shutil.copyfile(source / 'src/libfaketime.so.1', '/usr/local/lib/minihack-clock.so')
        license_dir = Path('/usr/local/share/doc/minihack-clock')
        license_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / 'COPYING', license_dir / 'COPYING')


if __name__ == '__main__':
    main()
