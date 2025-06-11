"""
ECMWF ERA5 Exploratory Data Analysis

This script analyses ECMWF ERA5 GRIB files for invalid `rh` relative humidity
data. ERA5 GRIB files should contain a `rh` variable. Relative humidity is a
percentage, therefore the axiom `0 <= rh <= 100` should hold.

Working with ERA5 data for the DE Antarctica project shows the published data
is faulty, with negative `rh` and "overflow", where `rh` is above 100.

This script reads GRIB files to report high level data issues.

USAGE:  python3 ecmwf_era5.py [GRIB_OR_NC_FILE]
"""

import pathlib
import datetime
import sys

import xarray as xr
import numpy as np

from PIL import Image


input_path = sys.argv[1]
is_nc = input_path.endswith(".nc")

ds = xr.open_dataset(input_path, decode_timedelta=False)
total_cells = np.multiply(*ds.r.shape[-2:])

height, width = ds.r.shape[-2:]
spacing = len(str(total_cells))

# colours for viewing RH & outside 0-100 range
RED = (200, 0, 0)
DARK_RED = (100, 0, 0)
BLUE = (0, 0, 200)


for t in ds.time.data:
    dt = datetime.datetime.fromisoformat(str(t))

    levels = ds.level.data if is_nc else ds.isobaricInhPa.data

    for level in levels:
        level = int(level)
        dest_dir = pathlib.Path(f"PNG/{level:04d}hPa")

        if not dest_dir.exists():
            dest_dir.mkdir()

        timestamp = f"{dt.year}-{dt.month:02d}-{dt.day:02d}_T{dt.hour:02d}{dt.minute:02d}"
        png_path = dest_dir / f"{timestamp}-{level:04d}hPa_nodata.png"

        if is_nc:
            raw_data = ds.r.sel(time=t, level=level, method="nearest").data
        else:
            raw_data = ds.r.sel(time=t, isobaricInhPa=level, method="nearest").data

        assert len(raw_data.shape) == 2

        # roughly scale negative data away from 0 (while *increasing* RH)
        # quick/dirty data skmi shows -10% < rh < 170%
        image = Image.new(mode="RGB", size=(width, height))
        idata = image.load()

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
            negative_count = np.count_nonzero(raw_data < 0.0)
            n_percent = round((negative_count / total_cells) * 100, 2)
            print(f" Negative RH detected {n_percent}% of cells: {png_path}")
        if overflow:
            overflow_count = np.count_nonzero(raw_data > 100.0)
            o_percent = round((overflow_count / total_cells) * 100, 2)
            print(f"Over 100% RH detected {o_percent}% of cells: {png_path}")

        image.save(png_path)

    print()  # space out levels in output
