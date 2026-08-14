# Code Package QA

Overall status: **PASS**

## Scope and content

The archive contains one top-level `TerraState_CodeData/` directory with 27
files: the public TerraState model, training entry, frozen configuration,
GreenEarthNet adapter, Q1--Q3 evaluation entries, protocol notes, frozen
manifests, reported reference metrics, licenses, and a CPU example. It contains
no dataset, weight, training log, cache, or unrelated experiment. No Media ZIP
was created.

The README states the release boundary directly: the package provides the
model, training and evaluation interfaces, frozen Q1--Q3 protocol
implementations, and reported reference metrics, while data and model weights
are not included. The package supplies no complete construction pipeline for
precursor artifacts, teacher artifacts, or future-state caches.

The author confirmed that the submitted Q1--Q3 results correspond to the
completed 40-epoch, 14,880-update run. Stale intermediate provenance is
excluded from the package. No checkpoint is included because no local weight
was unambiguously identifiable as the final distributable submitted weight.

## Validation matrix

| Check | Method | Status |
|---|---|---|
| Archive integrity | 7-Zip extraction plus Python `zipfile` CRC test | PASS |
| One top-level directory | ZIP member-list assertion | PASS |
| File inventory | 27 regular files; expected directories only | PASS |
| Git/cache/log cleanup | scan for `.git`, bytecode, caches, logs, and temporary files | PASS |
| Links | filesystem and archive inspection; no symlink | PASS |
| Python syntax | `compileall` with bytecode redirected outside extraction | PASS |
| Core import | import `TerraState`; construct on CPU | PASS |
| Parameter count | 7,180,896 | PASS |
| CLI parsing | training, Q1, Q2, Q3, and smoke `--help` | PASS |
| Requirements | every requirement parses; runtime dependencies are declared | PASS |
| Configuration | YAML parse; 40 epochs and 14,880 updates asserted | PASS |
| Reference results | all JSON files parse | PASS |
| Training dry run | prints `epochs=40 optimizer_updates=14880 global_batch=64` | PASS |
| CPU model smoke | full, state removal, identity transition, mean weather, serialization, strict reload | PASS |
| Scorer CPU smoke | perfect synthetic forecast gives \(R^2=1\), RMSE \(=0\), NSE \(=1\) | PASS |
| Weight-key compatibility | source and public model state keys and tensor shapes are identical | PASS |
| Old-name scan | required `rg` pattern plus excluded-update patterns | PASS (zero matches) |
| Identity scan | names, accounts, emails, host fragments, private paths, and repository links | PASS (zero matches) |
| Absolute-path scan | Unix home/mount/temp and Windows-drive patterns | PASS (zero matches) |
| Configuration/result consistency | compared with PDF and final evidence | PASS |
| SHA256 | archive digest recorded in `SHA256SUMS.txt` | PASS |

All executable tests were run from a clean extraction with
`CUDA_VISIBLE_DEVICES` empty.

## NOT RUN

- Full training: requires the complete GreenEarthNet data, initialization,
  teacher, future-state cache, eight-GPU environment, and the full training
  budget.
- Full Q1--Q3 evaluation: requires the complete data and a final checkpoint.
- Final-weight clean load: no final checkpoint is distributed.
- Precursor, teacher, and future-state-cache construction: complete builders
  are outside the release boundary and are not included.

These omissions are dependencies of the full experiment, not failures of the
packaged CPU smoke tests. The current local environment also lacks `httpx`,
which the installed `timm` stack warns about while importing; `httpx` and
`huggingface-hub` are explicitly declared in `requirements.txt`, and all
compile, import, CLI, model, serialization, and scorer tests pass.

## Reproducibility notes

- Q1 uses the 1,904-file frozen OOD-t manifest and the
  minicube/land-cover-balanced scorer.
- Q2 changes only the state contribution or transition computation on aligned
  samples and uses 10,000 paired bootstrap replicates.
- Q3 changes only future weather on the frozen 84-pair, 31-cluster manifest
  and uses complete-window masked loss plus the geographic-cluster bootstrap.
- `results/*.json` are labeled reported reference metrics; they are not outputs
  fabricated by a local checkpoint.
