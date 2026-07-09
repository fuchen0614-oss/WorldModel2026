from pathlib import Path

import numpy as np

from data.datasets.earthnet2021 import (
    EarthNet2021Config,
    EarthNet2021Dataset,
    _canonical_cubename,
)


def _write_synthetic_cube(root: Path) -> Path:
    train_dir = root / "train" / "32UMC"
    train_dir.mkdir(parents=True)
    name = (
        "32UMC_2017_01_01_2017_05_31_"
        "100_228_100_228_10_90_10_90.npz"
    )
    path = train_dir / name

    rng = np.random.default_rng(7)
    high = rng.uniform(0.05, 0.8, size=(128, 128, 7, 30)).astype(np.float32)
    high[0, 0, 0, 0] = np.nan
    high[0, 1, 1, 1] = np.inf
    high[:, :, 6, :] = 0.0
    # Dedicated [H,W,T] mask takes precedence and marks one cloudy quadrant.
    high_mask = np.zeros((128, 128, 30), dtype=np.float32)
    high_mask[:32, :32, 0] = np.nan
    high_mask[:64, :64, 12] = 1
    meso = rng.normal(size=(80, 80, 5, 150)).astype(np.float32)
    meso[:, :, 0, :] = 100.0
    meso[39:41, 39:41, 0, :] = 1.0
    meso[:, :, 2, :] = 100.0
    meso[39:41, 39:41, 2, :] = 2.0
    high_static = np.full((128, 128, 1), 500.0, dtype=np.float32)
    meso_static = np.zeros((80, 80, 1), dtype=np.float32)
    np.savez_compressed(
        path,
        highresdynamic=high,
        highresmask=high_mask,
        mesodynamic=meso,
        highresstatic=high_static,
        mesostatic=meso_static,
    )
    return path


def _write_synthetic_drivers(root: Path, cube_path: Path) -> None:
    root.mkdir(parents=True)
    days = np.arange(150, dtype=np.float32)
    np.savez_compressed(
        root / cube_path.name,
        vpd=0.5 + days * 0.001,
        solar_radiation=10.0 + days * 0.01,
    )


def test_earthnet_loader_with_external_drivers(tmp_path):
    cube = _write_synthetic_cube(tmp_path)
    driver_root = tmp_path / "drivers"
    _write_synthetic_drivers(driver_root, cube)

    cfg = EarthNet2021Config(
        root=str(tmp_path),
        split="train",
        model_img_size=32,
        use_train_holdout=False,
        external_driver_root=str(driver_root),
        external_driver_required=True,
    )
    sample = EarthNet2021Dataset(cfg)[0]

    assert sample["x_context"].shape == (10, 4, 32, 32)
    assert sample["x_target"].shape == (20, 4, 32, 32)
    assert sample["x_context"].isfinite().all()
    assert sample["x_target"].isfinite().all()
    assert sample["context_mask"][0, :8, :8].sum().item() == 0
    assert sample["context_mask"].shape == (10, 32, 32)
    assert sample["target_mask"].shape == (20, 32, 32)
    assert sample["D"].shape == (20, 9)
    assert sample["D_mask"].shape == (20, 9)
    assert sample["D_mask"].bool().all()
    np.testing.assert_allclose(
        sample["D"][0, 2:5].numpy(),
        [5.0, 1.0, 2.0],
    )
    assert sample["G"].shape == (1, 32, 32)
    assert np.isclose(sample["G"].mean().item(), 0.25)
    assert sample["h"].tolist() == [float(day) for day in range(5, 101, 5)]
    # Target frame 2 is source frame 12, so the cloudy quadrant must survive
    # the [H,W,T] -> [T,H,W] conversion and nearest-neighbor resize.
    assert sample["target_mask"][2, :16, :16].sum().item() == 0
    assert sample["start_date"] == "2017-01-01"


def test_canonical_cubename_strips_official_prefix():
    name = "context_32UMC_2017_01_01_2017_05_31_1_2_3_4_5_6_7_8.npz"
    assert _canonical_cubename(name).startswith("32UMC_2017_01_01")
    assert not _canonical_cubename(name).endswith(".npz")
