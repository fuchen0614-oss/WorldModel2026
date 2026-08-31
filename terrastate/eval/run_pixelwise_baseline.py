#!/usr/bin/env python3
"""Run an upstream GreenEarthNet pixelwise baseline (persistence / climatology /
previous year) under NumPy 2.x.

Those scripts still spell `np.NaN`, removed in NumPy 2.0. Rather than patch a
vendored upstream checkout that belongs to another repo, restore the alias in this
process and hand over. Nothing else about the script changes, so the predictions
stay the published implementation's.

  run_pixelwise_baseline.py <upstream_script.py> [args...]
"""
import runpy
import sys

import numpy as np

for old, new in (("NaN", "nan"), ("NAN", "nan"), ("Inf", "inf"), ("NINF", "-inf")):
    if not hasattr(np, old):
        setattr(np, old, getattr(np, new) if isinstance(new, str) and hasattr(np, new)
                else float(new))

script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
