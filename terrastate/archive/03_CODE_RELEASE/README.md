Code for training and evaluating TerraState.

This package provides the TerraState model, training and evaluation
interfaces, frozen Q1--Q3 protocol implementations, and reported reference
metrics. Data and model weights are not included.

- `models/`, `train/`, and `eval/`: model and executable entry points.
- `configs/` and `protocols/`: frozen settings for Q1--Q3.
- `data/` and `manifests/`: GreenEarthNet adapter and split metadata.
- `results/`: reported reference metrics.

Install: `python -m pip install -r requirements.txt`

Data layout: `DATA_ROOT/<season>/<minicube>.nc`; use the public GreenEarthNet
NetCDF fields consumed by `data/dataset.py`.

Train: `python train/train_terrastate.py --config configs/terrastate.yaml --data-root DATA_ROOT --initial-checkpoint CHECKPOINT --teacher-checkpoint TEACHER_CHECKPOINT --future-state-cache FUTURE_STATE_CACHE --output-dir OUTPUT_DIR`

Q1: `python eval/evaluate_forecast.py --config configs/terrastate.yaml --data-root DATA_ROOT --manifest manifests/q1_files.json --checkpoint CHECKPOINT --output results/q1_metrics.json`

Q2: `python eval/evaluate_state_load_bearing.py --config configs/terrastate.yaml --data-root DATA_ROOT --checkpoint CHECKPOINT --output results/q2_metrics.json`

Q3: `python eval/evaluate_weather_response.py --config configs/terrastate.yaml --data-root DATA_ROOT --manifest manifests/q3_pairs.json --checkpoint CHECKPOINT --output results/q3_metrics.json`

Outputs are `q1_metrics.json`, `q2_metrics.json`, and `q3_metrics.json`.
See `LICENSES.md`.
