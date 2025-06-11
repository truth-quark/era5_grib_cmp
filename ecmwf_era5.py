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
import datetime
import sys
import xarray as xr
import numpy as np

from PIL import Image


grib_path = sys.argv[1]

assert "stats" in os.listdir(".")


ds = xr.open_dataset(grib_path, engine="cfgrib", decode_timedelta=False)
total_cells = np.multiply(*ds.r.shape[-2:])

height, width = ds.r.shape[-2:]
spacing = len(str(total_cells))

# colours for viewing RH & outside 0-100 range
RED = (200, 0, 0)
DARK_RED = (100, 0, 0)
BLUE = (0, 0, 200)


for t in ds.time.data:
    dt = datetime.datetime.fromisoformat(str(t))
    # csv_path = f"stats/{dt.year}-{dt.month:02d}-{dt.day:02d}_T{dt.hour:02d}{dt.minute:02d}.csv"

    for level in ds.isobaricInhPa.data:
        png_path = f"PNG/{dt.year}-{dt.month:02d}-{dt.day:02d}_T{dt.hour:02d}{dt.minute:02d}-{int(level):04d}hPa_nodata.png"

        raw_data = ds.r.sel(time=t, isobaricInhPa=level, method="nearest").data

        assert len(raw_data.shape) == 2

        # roughly scale negative data away from 0 (while *increasing* RH)
        # quick/dirty data skmi shows -10% < rh < 170%
        image = Image.new(mode="RGB", size=(width, height))
        idata = image.load()

        r = raw_data.astype(np.uint8) + 10

        underflow = False
        overflow = False

        # TODO: pixel by pixel access to is slow, check API for passing arrays to PIL
        for x in range(image.size[0]):
            for y in range(image.size[1]):
                rv = raw_data[y, x]
                if rv < 0.0:
                    underflow = True  # negative RH
                    idata[x,y] = RED
                elif rv > 100.0:
                    overflow = True
                    idata[x, y] = BLUE
                else:
                    pixel = int(rv) + 10  # offset brings RH=0 off black
                    idata[x, y] = (pixel, pixel, pixel)  # should be greyscale

        if underflow:
            print(f"Negative RH detected: {png_path}")
            underflow = False
        if overflow:
            print(f"> 100% RH detected: {png_path}")
            overflow = False

        image.save(png_path)

        #
        # image = Image.fromarray(combined, mode="RGB")

        # if negative_data.any():
        #     negative_count = np.count_nonzero(negative_data)
        #     n_percent = (negative_count / total_cells) * 100
        # else:
        #     negative_count = 0
        #     n_percent = 0.0
        #
        #
        #
        # if overflow_data.any():
        #     overflow_count = np.count_nonzero(overflow_data)
        #     o_percent = (overflow_count / total_cells) * 100
        # else:
        #     overflow_count = 0
        #     o_percent = 0.0
        #
        # row = [level, data.min(), data.max(),
        #        negative_count, n_percent,
        #        overflow_count, o_percent]
