from __future__ import annotations

from scripts.audit_greenearthnet_layout import audit_layout, main


def _touch(root, directory: str, tile: str, name: str = "cube.nc") -> None:
    path = root / directory / tile / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"netcdf-placeholder")


def test_layout_audit_keeps_raw_and_chopped_roots_separate(tmp_path):
    raw = tmp_path / "EarthNet2021" / "earthnet2021x"
    tracks = tmp_path / "GreenEarthNet"
    _touch(raw, "train", "32ABC")
    for split in ("iid", "ood", "extreme", "seasonal"):
        _touch(raw, split, "32ABC")
    _touch(tracks, "val_chopped", "32ABC")
    _touch(tracks, "ood-t_chopped", "32DEF")
    _touch(tracks, "iid_chopped", "32GHI")

    report = audit_layout(raw.parent, eval_root=tracks)

    assert report["raw_root"] == str(raw.resolve())
    assert report["evaluation_root"] == str(tracks.resolve())
    assert report["raw_release_groups"]["train"]["num_netcdf_files"] == 1
    assert report["greenearthnet_track_groups"]["ood-t_chopped"]["num_netcdf_files"] == 1
    assert report["readiness"]["layout_ready_for_greenearthnet_main"]
    assert "raw/chopped roots" in " ".join(report["notes"])


def test_layout_audit_reports_missing_validation_without_blocking_dev_data(tmp_path):
    raw = tmp_path / "earthnet2021x"
    tracks = tmp_path / "GreenEarthNet"
    _touch(raw, "train", "32ABC")
    _touch(tracks, "ood-t_chopped", "32DEF")

    report = audit_layout(raw, eval_root=tracks)

    readiness = report["readiness"]
    assert readiness["raw_train_available"]
    assert readiness["official_ood_t_available"]
    assert not readiness["official_validation_available"]
    assert not readiness["layout_ready_for_greenearthnet_main"]
    assert "train-only development holdout" in readiness["recommendation"]


def test_strict_cli_returns_nonzero_for_incomplete_green_main(tmp_path, monkeypatch):
    raw = tmp_path / "earthnet2021x"
    tracks = tmp_path / "GreenEarthNet"
    _touch(raw, "train", "32ABC")
    _touch(tracks, "ood-t_chopped", "32DEF")
    output = tmp_path / "report.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_greenearthnet_layout.py",
            "--raw-root",
            str(raw),
            "--eval-root",
            str(tracks),
            "--strict-main",
            "--output",
            str(output),
        ],
    )

    assert main() == 2
    assert output.is_file()
