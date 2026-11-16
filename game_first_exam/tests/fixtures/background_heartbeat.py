"""Process-lifetime diagnostic, not a game policy or a scored benchmark episode."""
import json
import os
from pathlib import Path
import sys
import time

output = Path(sys.argv[1])
stop = output.with_suffix('.stop')
with output.open('w') as stream:
    for sequence in range(300):
        if stop.exists():
            break
        stream.write(json.dumps({'pid': os.getpid(), 'sid': os.getsid(0),
                                 'sequence': sequence, 'monotonic': time.monotonic()}) + '\n')
        stream.flush()
        time.sleep(0.2)
