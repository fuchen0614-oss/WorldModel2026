"""Rank-zero observability only; never reads or changes training state/RNG."""
import json
import math
import time
from pathlib import Path


class ProgressWriter:
    def __init__(self, output_dir, every_steps=1, max_seconds=10.0, clock=time.monotonic):
        if every_steps < 1 or not math.isfinite(max_seconds) or max_seconds <= 0:
            raise ValueError("progress intervals must be positive and finite")
        self.path = Path(output_dir) / "progress.json"
        self.every_steps, self.max_seconds, self.clock = every_steps, max_seconds, clock
        self.pending = None
        self.last_step = None
        self.last_time = None

    def update(self, progress, force=False):
        self.pending = dict(progress)
        now = self.clock()
        if (force or self.last_step is None
                or progress["step"] - self.last_step >= self.every_steps
                or now - self.last_time >= self.max_seconds):
            self.flush(now=now)

    def flush(self, now=None):
        if self.pending is None:
            return
        tmp = self.path.with_name("progress.json.tmp")
        tmp.write_text(json.dumps(self.pending, allow_nan=False), encoding="utf-8")
        tmp.replace(self.path)
        self.last_step = self.pending["step"]
        self.last_time = self.clock() if now is None else now
        self.pending = None
