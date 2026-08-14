from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_earthnet2021x.py"
SPEC = importlib.util.spec_from_file_location("sync_earthnet2021x", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_plan_sync_distinguishes_missing_mismatched_and_matching(tmp_path):
    split_root = tmp_path / "earthnet2021x" / "train"
    matching_path = split_root / "tile" / "matching.nc"
    mismatched_path = split_root / "tile" / "mismatched.nc"
    matching_path.parent.mkdir(parents=True)
    matching_path.write_bytes(b"1234")
    mismatched_path.write_bytes(b"12")

    objects = [
        MODULE.RemoteObject("remote/matching.nc", "tile/matching.nc", 4),
        MODULE.RemoteObject("remote/mismatched.nc", "tile/mismatched.nc", 4),
        MODULE.RemoteObject("remote/missing.nc", "tile/missing.nc", 4),
    ]
    missing, mismatched, matching = MODULE.plan_sync(split_root, objects)

    assert [item.relative_path for item in missing] == ["tile/missing.nc"]
    assert [item.relative_path for item in mismatched] == ["tile/mismatched.nc"]
    assert [item.relative_path for item in matching] == ["tile/matching.nc"]


def test_manifest_is_built_region_by_region(tmp_path, monkeypatch):
    class FakeS3:
        def ls(self, prefix, detail):
            assert prefix == "earthnet/earthnet2021x/train"
            assert detail is True
            return [
                {"name": f"{prefix}/29SND", "type": "directory"},
                {"name": f"{prefix}/30ABC", "type": "directory"},
            ]

        def find(self, prefix, detail):
            assert detail is True
            name = f"{prefix}/{Path(prefix).name}_cube.nc"
            return {name: {"name": name, "size": 123}}

    monkeypatch.setattr(MODULE, "make_s3", lambda proxy: FakeS3())
    manifest = tmp_path / "manifest.json"
    objects = MODULE.load_manifest(
        manifest,
        split="train",
        proxy=None,
        rescan=False,
        manifest_workers=2,
    )

    assert len(objects) == 2
    assert {item.size for item in objects} == {123}
    assert manifest.exists()
