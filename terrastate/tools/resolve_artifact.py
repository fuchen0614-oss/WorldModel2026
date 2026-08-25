#!/usr/bin/env python
"""Resolve a LOGICAL artifact id to a verified on-disk path.

Why this exists
---------------
Every TerraState weight has been selected by *basename* at least once in this project's
history (`checkpoint_last.pt` vs `checkpoint_best.pt` vs `checkpoint_boundary80.pt` all
live in the same directory and three of them share a byte count).  Basename selection is
not a provenance statement.  This resolver makes the *logical id* the only thing a
launcher, test, or eval script names, and refuses to hand back a path whose content does
not hash to the id's registered `file_sha256`.

Layout
------
    <store>/objects/sha256/<first2>/<sha256>.pt      immutable, content-addressed
    <store>/aliases/<alias>.json                     mutable pointer -> logical id
    terrastate/artifacts/weight_registry.json        logical id -> object + provenance

Usage
-----
    # print a verified absolute path (verifies sha256 by default)
    python tools/resolve_artifact.py terrastate/v2/legacy-boundary11904@v1

    # follow a mutable alias
    python tools/resolve_artifact.py --alias terrastate/v2/default-training-anchor

    # full record as JSON
    python tools/resolve_artifact.py --json terrastate/v2/historical-full14880@v1

    # skip hashing (large files, path-only lookup) -- NOT allowed for launches
    python tools/resolve_artifact.py --no-verify <id>

    # library use
    from tools.resolve_artifact import resolve
    path = resolve("terrastate/v2/legacy-boundary11904@v1")     # verifies, returns Path

Exit codes: 0 ok · 2 unknown id/alias · 3 object missing · 4 sha256 mismatch (fail closed).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REGISTRY = REPO / "artifacts" / "weight_registry.json"
CHUNK = 8 << 20


class ResolveError(RuntimeError):
    def __init__(self, msg: str, code: int):
        super().__init__(msg)
        self.code = code


def load_registry(path=None) -> dict:
    p = Path(path) if path else REGISTRY
    if not p.is_file():
        raise ResolveError(f"registry not found: {p}", 2)
    return json.loads(p.read_text())


def sha256_file(path, chunk: int = CHUNK) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def store_root(reg: dict) -> Path:
    return Path(reg["store"])


def resolve_alias(alias: str, reg: dict | None = None) -> str:
    """Mutable alias -> logical id.  Aliases live in the STORE (not in git) so that
    re-pointing an anchor is an operational act with its own record, not a code diff."""
    reg = reg or load_registry()
    apath = store_root(reg) / "aliases" / f"{alias.replace('/', '__')}.json"
    if not apath.is_file():
        known = sorted(p.stem.replace("__", "/") for p in (store_root(reg) / "aliases").glob("*.json"))
        raise ResolveError(f"unknown alias {alias!r}; known={known}", 2)
    blob = json.loads(apath.read_text())
    return blob["logical_id"]


def record(logical_id: str, reg: dict | None = None) -> dict:
    reg = reg or load_registry()
    arts = reg["artifacts"]
    if logical_id not in arts:
        raise ResolveError(f"unknown logical id {logical_id!r}; known={sorted(arts)}", 2)
    return arts[logical_id]


def resolve(logical_id: str, *, verify: bool = True, reg: dict | None = None,
            alias: bool = False) -> Path:
    """Return the verified absolute object path for a logical id (or alias).

    `verify=True` re-hashes the object.  Callers that are about to LAUNCH training or
    publish a result must keep verification on; only cheap interactive lookups may
    disable it.
    """
    reg = reg or load_registry()
    if alias:
        logical_id = resolve_alias(logical_id, reg)
    rec = record(logical_id, reg)
    kind = rec.get("kind", "object")
    if kind == "path-registered":
        # Large data artifacts (future-state caches) are registered IN PLACE: they are not
        # copied into the object store.  Identity is size + the provenance SHAs the
        # trainer itself asserts, plus an optional recorded file sha256.
        p = Path(rec["path"])
        if not p.is_file():
            raise ResolveError(f"registered path missing: {p}", 3)
        size = p.stat().st_size
        if size != rec["file_bytes"]:
            raise ResolveError(f"{logical_id}: size {size} != registered {rec['file_bytes']}", 4)
        if verify and rec.get("file_sha256"):
            got = sha256_file(p)
            if got != rec["file_sha256"]:
                raise ResolveError(f"{logical_id}: sha256 {got} != registered "
                                   f"{rec['file_sha256']}", 4)
        return p

    p = store_root(reg) / rec["object_relpath"]
    if not p.is_file():
        raise ResolveError(f"object missing for {logical_id}: {p}", 3)
    size = p.stat().st_size
    if size != rec["file_bytes"]:
        raise ResolveError(f"{logical_id}: size {size} != registered {rec['file_bytes']}", 4)
    if verify:
        got = sha256_file(p)
        if got != rec["file_sha256"]:
            raise ResolveError(f"{logical_id}: sha256 {got} != registered {rec['file_sha256']} "
                               f"(FAIL CLOSED — do not use this file)", 4)
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("id", help="logical artifact id, or alias name with --alias")
    ap.add_argument("--alias", action="store_true", help="treat `id` as a mutable alias")
    ap.add_argument("--no-verify", action="store_true", help="skip sha256 re-hash (lookup only)")
    ap.add_argument("--json", action="store_true", help="print the full registry record")
    ap.add_argument("--registry", default=None)
    a = ap.parse_args()
    try:
        reg = load_registry(a.registry)
        lid = resolve_alias(a.id, reg) if a.alias else a.id
        path = resolve(lid, verify=not a.no_verify, reg=reg)
    except ResolveError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return e.code
    if a.json:
        out = dict(record(lid, reg))
        out["logical_id"] = lid
        out["resolved_path"] = str(path)
        out["sha256_verified"] = not a.no_verify
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
