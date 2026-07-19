#!/usr/bin/env python
"""Safely synchronize one EarthNet2021x split from the official S3 store.

Unlike the original ad-hoc downloader, this script compares exact remote byte
sizes, downloads to ``.part``, validates NetCDF metadata, and only then replaces
the destination. Re-running it is safe after interruption.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ENDPOINT = "https://s3.bgc-jena.mpg.de:9000"
REGION = "thuringia"
DATASET = "earthnet2021x"
REMOTE_ROOT = f"earthnet/{DATASET}"
SPLITS = ("train", "iid", "ood", "extreme", "seasonal")
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

# HDF5/netCDF4 has non-reentrant global state; a single process-wide lock keeps
# concurrent worker downloads while serializing NetCDF validation opens.
_HDF5_VALIDATE_LOCK = threading.Lock()


@dataclass(frozen=True)
class RemoteObject:
    remote_path: str
    relative_path: str
    size: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        required=True,
        help="EarthNet parent or earthnet2021x root.",
    )
    parser.add_argument("--split", required=True, choices=SPLITS)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--manifest-workers",
        type=int,
        default=4,
        help="Concurrent region listings used while building the remote manifest.",
    )
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--manifest",
        help="Manifest JSON path; defaults below the dataset root.",
    )
    parser.add_argument(
        "--rescan",
        action="store_true",
        help="Ignore a cached manifest and query official S3 again.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report missing/size-mismatched files without downloading.",
    )
    parser.add_argument(
        "--max-downloads",
        type=int,
        default=0,
        help="Limit repairs/downloads for a smoke run; 0 means all.",
    )
    parser.add_argument(
        "--no-netcdf-validation",
        action="store_true",
        help="Skip metadata validation of newly downloaded files.",
    )
    parser.add_argument("--proxy")
    parser.add_argument("--report")
    return parser.parse_args()


def resolve_dataset_root(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.name.lower() == DATASET:
        return path
    return path / DATASET


def make_s3(proxy: str | None):
    import s3fs

    config_kwargs: dict[str, Any] = {
        "connect_timeout": 15,
        "read_timeout": 90,
        "retries": {"max_attempts": 4, "mode": "standard"},
    }
    if proxy:
        config_kwargs["proxies"] = {"http": proxy, "https": proxy}
    return s3fs.S3FileSystem(
        anon=True,
        client_kwargs={"endpoint_url": ENDPOINT, "region_name": REGION},
        config_kwargs=config_kwargs,
    )


def metadata_size(metadata: dict[str, Any]) -> int:
    for key in ("size", "Size", "ContentLength"):
        if key in metadata:
            return int(metadata[key])
    return -1


def load_manifest(
    manifest_path: Path,
    split: str,
    proxy: str | None,
    rescan: bool,
    manifest_workers: int,
) -> list[RemoteObject]:
    if manifest_path.exists() and not rescan:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if payload.get("dataset") != DATASET or payload.get("split") != split:
            raise ValueError(
                f"Manifest {manifest_path} belongs to "
                f"{payload.get('dataset')}/{payload.get('split')}, not "
                f"{DATASET}/{split}."
            )
        objects = [RemoteObject(**item) for item in payload["objects"]]
        print(
            f"[sync] loaded cached manifest with {len(objects)} objects: "
            f"{manifest_path}",
            flush=True,
        )
        return objects

    prefix = f"{REMOTE_ROOT}/{split}"
    print(
        f"[sync] listing region prefixes for official {split} split",
        flush=True,
    )
    s3 = make_s3(proxy)
    entries = s3.ls(prefix, detail=True)
    region_prefixes = []
    direct_details: dict[str, dict[str, Any]] = {}
    for entry in entries:
        name = str(entry.get("name", "")).rstrip("/")
        if not name:
            continue
        if name.endswith(".nc"):
            direct_details[name] = entry
        else:
            region_prefixes.append(name)
    region_prefixes = sorted(set(region_prefixes))
    print(
        f"[sync] found {len(region_prefixes)} region prefixes; "
        f"scanning with {manifest_workers} workers",
        flush=True,
    )
    details = dict(direct_details)
    if region_prefixes:
        with ThreadPoolExecutor(
            max_workers=min(manifest_workers, len(region_prefixes))
        ) as executor:
            futures = {
                executor.submit(find_remote_region, region, proxy): region
                for region in region_prefixes
            }
            completed = 0
            for future in as_completed(futures):
                region = futures[future]
                region_details = future.result()
                details.update(region_details)
                completed += 1
                print(
                    f"[sync] remote regions {completed}/{len(region_prefixes)}; "
                    f"latest={Path(region).name}; objects={len(details)}",
                    flush=True,
                )
    elif not direct_details:
        raise RuntimeError(
            f"Official S3 listing returned no regions or NetCDF files for {prefix}"
        )
    objects = []
    for remote_path, metadata in details.items():
        if not remote_path.endswith(".nc"):
            continue
        size = metadata_size(metadata)
        if size < 0:
            raise ValueError(f"Remote object has no size metadata: {remote_path}")
        objects.append(
            RemoteObject(
                remote_path=remote_path,
                relative_path=remote_path[len(prefix) + 1 :],
                size=size,
            )
        )
    objects.sort(key=lambda item: item.relative_path)
    payload = {
        "dataset": DATASET,
        "split": split,
        "endpoint": ENDPOINT,
        "created_unix": time.time(),
        "objects": [asdict(item) for item in objects],
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    print(
        f"[sync] cached {len(objects)} remote objects: {manifest_path}",
        flush=True,
    )
    return objects


def find_remote_region(
    region_prefix: str,
    proxy: str | None,
) -> dict[str, dict[str, Any]]:
    details = make_s3(proxy).find(region_prefix, detail=True)
    return {
        path: metadata
        for path, metadata in details.items()
        if path.endswith(".nc")
    }


def plan_sync(
    split_root: Path,
    objects: list[RemoteObject],
) -> tuple[list[RemoteObject], list[RemoteObject], list[RemoteObject]]:
    missing = []
    mismatched = []
    matching = []
    for index, item in enumerate(objects, start=1):
        if index == 1 or index % 1000 == 0 or index == len(objects):
            print(f"[sync] checking local sizes {index}/{len(objects)}", flush=True)
        path = split_root / item.relative_path
        if not path.exists():
            missing.append(item)
        elif path.stat().st_size != item.size:
            mismatched.append(item)
        else:
            matching.append(item)
    return missing, mismatched, matching


def validate_netcdf(path: Path) -> None:
    import xarray as xr

    # HDF5/netCDF4 is not thread-safe: concurrent opens from the worker pool
    # corrupt the library's global state and crash the process (SIGSEGV/SIGABRT).
    # Serialize validation so downloads stay parallel but opens never overlap.
    with _HDF5_VALIDATE_LOCK:
        with xr.open_dataset(path, decode_times=False, cache=False) as cube:
            missing = sorted(set(REQUIRED_VARIABLES) - set(cube.variables))
            if missing:
                raise ValueError(f"missing variables: {missing}")
            for dimension in ("time", "lat", "lon"):
                if int(cube.sizes.get(dimension, 0)) <= 0:
                    raise ValueError(f"missing or empty dimension: {dimension}")


def download_chunk(
    items: list[RemoteObject],
    split_root: Path,
    proxy: str | None,
    retries: int,
    validate: bool,
) -> dict[str, Any]:
    s3 = make_s3(proxy)
    repaired = []
    failures = []
    for item_index, item in enumerate(items, start=1):
        destination = split_root / item.relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.stat().st_size == item.size:
            continue
        part = destination.with_name(destination.name + ".part")
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                if part.exists():
                    part.unlink()
                s3.download(item.remote_path, str(part))
                downloaded_size = part.stat().st_size
                if downloaded_size != item.size:
                    raise ValueError(
                        f"size {downloaded_size}, expected {item.size}"
                    )
                if validate:
                    validate_netcdf(part)
                os.replace(part, destination)
                repaired.append(item.relative_path)
                last_error = None
                break
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < retries:
                    time.sleep(min(2**attempt, 10))
        if last_error is not None:
            failures.append(
                {
                    "relative_path": item.relative_path,
                    "error": last_error,
                }
            )
        if item_index == 1 or item_index % 50 == 0 or item_index == len(items):
            print(
                f"[sync-worker] processed {item_index}/{len(items)}; "
                f"failures={len(failures)}",
                flush=True,
            )
    return {"repaired": repaired, "failures": failures}


def split_chunks(items: list[RemoteObject], workers: int) -> list[list[RemoteObject]]:
    worker_count = max(1, min(workers, len(items)))
    return [items[index::worker_count] for index in range(worker_count)]


def main() -> int:
    args = parse_args()
    if args.workers < 1:
        raise ValueError("--workers must be at least 1.")
    if args.manifest_workers < 1:
        raise ValueError("--manifest-workers must be at least 1.")
    dataset_root = resolve_dataset_root(Path(args.root))
    split_root = dataset_root / args.split
    default_manifest = (
        dataset_root / ".manifests" / f"{DATASET}_{args.split}.json"
    )
    manifest_path = Path(args.manifest).resolve() if args.manifest else default_manifest
    objects = load_manifest(
        manifest_path,
        args.split,
        args.proxy,
        args.rescan,
        args.manifest_workers,
    )
    missing, mismatched, matching = plan_sync(split_root, objects)
    todo = [*missing, *mismatched]
    initial = {
        "dataset_root": str(dataset_root),
        "split": args.split,
        "remote_objects": len(objects),
        "matching_files": len(matching),
        "missing_files": len(missing),
        "size_mismatched_files": len(mismatched),
        "missing_preview": [item.relative_path for item in missing[:20]],
        "mismatched_preview": [item.relative_path for item in mismatched[:20]],
    }
    print(json.dumps(initial, indent=2), flush=True)
    if args.dry_run or not todo:
        final = {
            **initial,
            "dry_run": args.dry_run,
            "status": "COMPLETE" if not todo else "NEEDS_SYNC",
        }
        write_report(args.report, final)
        return 0 if not todo else 2

    total_todo = len(todo)
    if args.max_downloads > 0:
        todo = todo[: args.max_downloads]
    print(
        f"[sync] downloading/repairing {len(todo)} files with "
        f"{args.workers} workers",
        flush=True,
    )
    repaired = []
    failures = []
    chunks = split_chunks(todo, args.workers)
    with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
        futures = [
            executor.submit(
                download_chunk,
                chunk,
                split_root,
                args.proxy,
                args.retries,
                not args.no_netcdf_validation,
            )
            for chunk in chunks
        ]
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            repaired.extend(result["repaired"])
            failures.extend(result["failures"])
            completed += len(result["repaired"]) + len(result["failures"])
            print(
                f"[sync] completed {completed}/{len(todo)}; "
                f"failures={len(failures)}",
                flush=True,
            )

    final = {
        **initial,
        "requested_downloads": len(todo),
        "deferred_downloads": total_todo - len(todo),
        "repaired_files": len(repaired),
        "failures": failures,
        "status": (
            "SYNCED"
            if not failures and len(todo) == total_todo
            else "PARTIAL"
        ),
    }
    print(json.dumps(final, indent=2), flush=True)
    write_report(args.report, final)
    return 0 if not failures else 1


def write_report(path: str | None, report: dict[str, Any]) -> None:
    if not path:
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
