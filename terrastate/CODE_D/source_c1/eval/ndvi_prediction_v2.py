import numpy as np
import xarray as xr
from eval.greenearthnet_protocol import PREDICTION_VARIABLE, expected_prediction_times

def make_ndvi_prediction_dataset(target: xr.Dataset, ndvi: np.ndarray) -> xr.Dataset:
    """Build the ndvi_pred cube on the official 20 five-daily target times."""
    times = expected_prediction_times(target)
    ndvi = np.clip(np.asarray(ndvi, dtype=np.float32), -1.0, 1.0)
    expected = (times.size, target.sizes["lat"], target.sizes["lon"])
    if ndvi.shape != expected:
        raise ValueError(f"ndvi shape {ndvi.shape} != expected {expected}")
    return xr.Dataset(
        {
            PREDICTION_VARIABLE: xr.DataArray(
                ndvi,
                coords={"time": times, "lat": target.lat, "lon": target.lon},
                dims=("time", "lat", "lon"),
            )
        }
    )
