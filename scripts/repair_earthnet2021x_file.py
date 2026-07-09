#!/usr/bin/env python
"""Check or safely redownload one EarthNet2021x NetCDF object."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


S3_ENDPOINT = "https://s3.bgc-jena.mpg.de:9000"
S3_PREFIX = "earthnet/earthnet2021x"
REQUIRED_VARIABLES = (
    "s2_B02",
    "s2_B03",
    "s2_B04",
    "s2_B8A",
    "s2_mask",
    "eobs_hu",
    "eobs_qq",
    "eobs_rr",
    "eobs_tg",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="EarthNet parent or earthnet2021x root.")
    parser.add_argument(
        "--split",
        required=True,
        choices=("train", "iid", "ood", "extreme", "seasonal"),
    )
    parser.add_argument(
        "--relative-path",
        required=True,
        help="Path below the split, for example 29SND/cube.nc.",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Download, validate, and atomically replace the local file.",
    )
    parser.add_argument("--proxy")
    return parser.parse_args()


def dataset_root(path: Path) -> Path:
    path = path.expanduser().resolve()
    nested = path / "earthnet2021x"
    return nested if nested.is_dir() else path


def validate_netcdf(path: Path) -> dict[str, Any]:
    import xarray as xr

    result: dict[str, Any] = {"ok": False}
    try:
        with xr.open_dataset(path, decode_times=False, cache=False) as cube:
            missing = sorted(set(REQUIRED_VARIABLES) - set(cube.variables))
            result.update(
                {
                    "ok": not missing,
                    "missing_variables": missing,
                    "dimensions": {
                        name: int(value) for name, value in cube.sizes.items()
                    },
                }
            )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def make_s3(proxy: str | None):
    import s3fs

    return s3fs.S3FileSystem(
        anon=True,
        client_kwargs={
            "endpoint_url": S3_ENDPOINT,
            "region_name": "thuringia",
        },
        config_kwargs=(
            {"proxies": {"http": proxy, "https": proxy}} if proxy else {}
        ),
    )


def object_size(metadata: dict[str, Any]) -> int:
    for key in ("size", "Size", "ContentLength"):
        if key in metadata:
            return int(metadata[key])
    return -1


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def object_etag(metadata: dict[str, Any]) -> str | None:
    for key in ("ETag", "etag", "Etag"):
        if key in metadata:
            return str(metadata[key]).strip('"')
    return None


def main() -> int:
    args = parse_args()
    relative = Path(args.relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("--relative-path must stay below the selected split.")

    root = dataset_root(Path(args.root))
    split_root = (root / args.split).resolve()
    local_path = (split_root / relative).resolve()
    if split_root != local_path and split_root not in local_path.parents:
        raise ValueError("Resolved local path escapes the selected split.")
    remote_path = f"{S3_PREFIX}/{args.split}/{relative.as_posix()}"

    print(f"[repair] checking remote object: {remote_path}", flush=True)
    s3 = make_s3(args.proxy)
    metadata = s3.info(remote_path)
    remote_bytes = object_size(metadata)
    local_bytes = local_path.stat().st_size if local_path.exists() else None
    remote_etag = object_etag(metadata)
    local_md5 = file_md5(local_path) if local_path.exists() else None
    local_validation = (
        validate_netcdf(local_path)
        if local_path.exists()
        else {"ok": False, "error": "local file is missing"}
    )
    before = {
        "local_path": str(local_path),
        "remote_path": remote_path,
        "local_bytes": local_bytes,
        "remote_bytes": remote_bytes,
        "local_md5": local_md5,
        "remote_etag": remote_etag,
        "checksum_matches": (
            local_md5 == remote_etag
            if local_md5 is not None
            and remote_etag is not None
            and "-" not in remote_etag
            else None
        ),
        "size_matches": (
            local_bytes == remote_bytes
            if local_bytes is not None and remote_bytes >= 0
            else None
        ),
        "local_validation": local_validation,
    }
    print(json.dumps(before, indent=2, ensure_ascii=False))
    if not args.repair:
        print("[repair] check only; add --repair to replace this file.", flush=True)
        return 0 if local_validation["ok"] else 1
    if (
        local_validation["ok"]
        and local_bytes == remote_bytes
        and (
            remote_etag is None
            or "-" in remote_etag
            or local_md5 == remote_etag
        )
    ):
        print("[repair] local file already matches the remote object; nothing to do.")
        return 0

    local_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = local_path.with_name(local_path.name + ".part")
    if part_path.exists():
        part_path.unlink()
    print(f"[repair] downloading to temporary file: {part_path}", flush=True)
    s3.download(remote_path, str(part_path))
    downloaded_bytes = part_path.stat().st_size
    if remote_bytes >= 0 and downloaded_bytes != remote_bytes:
        raise RuntimeError(
            f"Downloaded size {downloaded_bytes} differs from remote {remote_bytes}; "
            f"temporary file kept at {part_path}"
        )
    downloaded_validation = validate_netcdf(part_path)
    if not downloaded_validation["ok"]:
        raise RuntimeError(
            "Downloaded object still fails NetCDF validation; "
            f"temporary file kept at {part_path}: {downloaded_validation}"
        )
    os.replace(part_path, local_path)
    print(
        json.dumps(
            {
                "status": "REPAIRED",
                "local_path": str(local_path),
                "bytes": downloaded_bytes,
                "validation": downloaded_validation,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
