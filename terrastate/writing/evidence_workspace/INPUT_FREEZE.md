# Input freeze

`INPUT_FREEZE.sha256` contains SHA-256 digests for 47 inspected input files:

- every `.tex` file recursively under `TerraState_AAAI27/paper/`;
- the active `references.bib`;
- the frozen TerraState release evidence assets copied into
  `evidence_workspace/raw/release/`;
- the local OOD-t manifest and all Q3 protocol/manifest files;
- the official GreenEarthNet paper and supplement copied into
  `evidence_workspace/raw/sources/`;
- the locally archived EO-WM, VegSim, LatentTSF, and group-actions source
  material used for claim adjudication;
- `WorldModel2026-planb/TERRASTATE_V2_EVIDENCE.md`.

All entries use absolute paths. No input was missing when the digest list was
generated. The checkpoint binary was not copied or read; its SHA-256 is taken
from the frozen GitHub release asset digest and is repeated in the release
selection record and Q1/Q2 result provenance.

The validation manifest file was not available locally. Its SHA-256 is recorded
in the frozen selection/result JSON but is not represented as a locally hashed
line in `INPUT_FREEZE.sha256`.
