"""
ECMWF ERA5 Exploratory Data Analysis

This rough script reads & analyses ECMWF ERA5 NC files for invalid `z` geopotential
data. It compares NC file Z variables & to analyse data differences.

USAGE:  python3 era5_z_check.py [NC_FILE_0] [NC_FILE_1]
"""

import sys
import xarray as xr


z0_path, z1_path = sys.argv[1:]
is_nc = z0_path.endswith(".nc") and z1_path.endswith(".nc")

z0_ds = xr.open_dataset(z0_path, decode_timedelta=False)
z1_ds = xr.open_dataset(z1_path, decode_timedelta=False)

# TODO: test geopotential decreases with elevation
# TODO: test geopotential is equivalent at same time & elevation across different datasets

for t in z0_ds.time.data:
    levels = z0_ds.level.data if is_nc else z0_ds.isobaricInhPa.data
    level_key = "level" if is_nc else "isobaricInhPa"

    for level in levels:
        level = int(level)
        kwargs = {"time": t, "method": "nearest", level_key: level}

        # ensure data not equivalent at same levels
        z0_raw_data = z0_ds.z.sel(**kwargs).data
        z1_raw_data = z1_ds.z.sel(**kwargs).data
        diffs = z0_raw_data - z1_raw_data

        print(f"\nTime: {str(t)[:13]}  Level: {level}")
        print(f"z0 min={z0_raw_data.min()} mean={z0_raw_data.mean()} max={z0_raw_data.max()}")
        print(f"z1 min={z1_raw_data.min()}, mean={z1_raw_data.mean()} max={z1_raw_data.max()}")

        assert not (diffs == 0.0).all(), f"z0, z1 difference:\n{diffs}"
