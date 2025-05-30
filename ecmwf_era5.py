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

import os
import csv
import datetime
import sys
import xarray as xr
import numpy as np

from PIL import Image


grib_path = sys.argv[1]

assert "stats" in os.listdir(".")


ds = xr.open_dataset(grib_path, engine="cfgrib", decode_timedelta=False)
total_cells = np.multiply(*ds.r.shape[-2:])
spacing = len(str(total_cells))


for t in ds.time.data:
    dt = datetime.datetime.fromisoformat(str(t))
    csv_path = f"stats/{dt.year}-{dt.month:02d}-{dt.day:02d}_T{dt.hour:02d}{dt.minute:02d}.csv"

    with open(csv_path, "w") as cf:
        writer = csv.writer(cf)
        header = ["Pressure hPa", "Min RH", "Max RH",
                  "Negative RH Count", "Negative RH %",
                  "Overflow RH Count", "Overflow RH %"]

        writer.writerow(header)

        for level in ds.isobaricInhPa.data:
            png_path = f"stats/{dt.year}-{dt.month:02d}-{dt.day:02d}_T{dt.hour:02d}{dt.minute:02d}-{int(level):04d}hPa.png"

            data = ds.r.sel(time=t, isobaricInhPa=level, method="nearest").data

            # roughly scale negative data away from 0 (while *increasing* RH)
            # quick/dirty data skmi shows -10% < rh < 170%
            image = Image.fromarray(data.astype(np.uint8) + 20)
            image.save(png_path)

            # TODO: visualise negative data in the PNGs
            negative_data = data < 0

            if negative_data.any():
                negative_count = np.count_nonzero(negative_data)
                n_percent = (negative_count / total_cells) * 100
            else:
                negative_count = 0
                n_percent = 0.0

            overflow_data = data > 100

            if overflow_data.any():
                overflow_count = np.count_nonzero(overflow_data)
                o_percent = (overflow_count / total_cells) * 100
            else:
                overflow_count = 0
                o_percent = 0.0

            row = [level, data.min(), data.max(),
                   negative_count, n_percent,
                   overflow_count, o_percent]

            writer.writerow(row)
