"""
ECMWF ERA5 Exploratory Data Analysis

This script analyses ECMWF ERA5 GRIB files for invalid `rh` relative humidity
data. ERA5 GRIB files should contain a `rh` variable. Relative humidity is a
percentage, therefore the axiom `0 <= rh <= 100` should hold.

Working with ERA5 data for the DE Antarctica project shows the published data
is faulty, with negative `rh` and "overflow", where `rh` is above 100.

This script reads GRIB files to report high level data issues.

USAGE:  python3 ecmwf_era5.py [GRIB_FILE]
"""

import sys
import xarray as xr
import numpy as np

grib_path = sys.argv[1]

ds = xr.open_dataset(grib_path, engine="cfgrib", decode_timedelta=False)
total_cells = np.multiply(*ds.r.shape[-2:])
spacing = len(str(total_cells))


for t in ds.time.data:
    print(f"time={t}")

    for level in ds.isobaricInhPa.data:
        data = ds.r.sel(time=t, isobaricInhPa=level, method="nearest").data

        negative_data = data < 0
        if negative_data.any():
            negative_count = np.count_nonzero(negative_data)
            n_percent = (negative_count / total_cells) * 100
            msg = f"{int(level):4d} hPa  Negative RH, {negative_count:>8} / {total_cells} cells ({n_percent:.2f}%)"
            print(msg)

        overflow_data = data > 100
        if overflow_data.any():
            overflow_count = np.count_nonzero(overflow_data)
            o_percent = (overflow_count / total_cells) * 100
            msg = f"{int(level):4d} hPa  Overflow RH, {overflow_count:>8} / {total_cells} cells ({o_percent:.2f}%)"
            print(msg)

    print()
