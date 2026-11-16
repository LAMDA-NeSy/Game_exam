"""Bounded-memory live evidence recording; rendering never decides the grade."""
import json
from pathlib import Path

import imageio.v2 as imageio
from PIL import Image


class Recorder:
    def __init__(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.writer = None
        self.error = None

    def event(self, record):
        with (self.output / "episode.jsonl").open("a") as stream:
            stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")

    def frame(self, frame):
        if frame is None or self.error:
            return
        try:
            if self.writer is None:
                self.writer = imageio.get_writer(self.output / "replay.mp4", fps=6,
                                                 codec="libx264", macro_block_size=1)
            self.writer.append_data(frame)
            Image.fromarray(frame).save(self.output / "replay.last.png")
        except Exception as exc:  # noqa: BLE001 - recording failure must not discard the trusted game result
            self.error = f"{type(exc).__name__}: {exc}"

    def close(self):
        if self.writer:
            try:
                self.writer.close()
            except Exception as exc:  # noqa: BLE001 - recording failure must not discard the trusted game result
                self.error = f"{type(exc).__name__}: {exc}"
        (self.output / "recording.json").write_text(json.dumps({
            "video_source": "live", "render_error": self.error,
        }, indent=2) + "\n")
