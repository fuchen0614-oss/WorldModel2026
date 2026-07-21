# Official Contextformer weights (vendored via git for the training end)

These are the OFFICIAL published GreenEarthNet / Contextformer weights, shipped
through git only because the training server's route to Zenodo is ~76 KiB/s
(≈8h) and there is no scp/rsync channel between the dev box and the server.

## What is here
- `contextformer6M/seed42.ckpt` — the published **6.1M-param Contextformer SOTA**
  (`contextformer6M`, PVT-v2-B0 encoder), seed 42. Loaded & verified locally:
  223 tensors, 6.06M params, forward OK. This is the ONLY seed we ship first
  (single-seed end-to-end for Gate-0; seeds 27/97 come later for 3-seed B0).

## Provenance
- Source: Zenodo record **10793870** (`model_weights.zip`, 2.3 GB), path inside
  the zip: `model_weights/contextformer/contextformer6M/seed=42.ckpt`.
- Paper: Benson et al., "Multi-modal Learning for Geospatial Vegetation
  Forecasting", CVPR 2024.
- Official config: `third_party/greenearthnet/model_configs/contextformer/contextformer6M/seed=42.yaml`
  (pvt=True, patch_size=4, n_hidden=256, n_heads=8, depth=3, n_weather=24,
  context=10→target=20, mask_clouds=True, add_last_ndvi=True).
- Renamed `seed=42.ckpt` → `seed42.ckpt` (drop the `=` for path sanity).

## Integrity
```
sha256  ec6706e8a904bba8a195d542921f54c6ce058f8d0d7a9aaeb91f117237d4a4fa  contextformer6M/seed42.ckpt
```
Verify on the server after `git pull`:
```bash
sha256sum checkpoints/contextformer_official/contextformer6M/seed42.ckpt
```

## Loader
`models/encoders/pvt_contextformer_q.py::PVTContextformerQ.from_official(<ckpt>)`
strips the Lightning `model.` prefix and loads into the vendored
`contextformer_official.ContextFormer` (see `scripts/smoke_contextformer_load.py`).
