"""
ECMWF ERA5 Exploratory Data Analysis

This script analyses NCI's ECMWF ERA5 NetCDF files to determine if `tco3` or
total column of ozone files contain NODATA values.

USAGE:  python3 era5_nodata.py [NC_DIR]
"""

import os
import sys
import pathlib

import xarray as xr


def workflow(input_dir_path):
    results = []

    for dirpath, dirnames, filenames in os.walk(input_dir_path):
        dirpath = pathlib.Path(dirpath)

        for fname in filenames:
            file_path = dirpath / fname

            if file_path.name.endswith(".nc") or file_path.name.endswith(".nc4"):
                for time, res in check_nodata(file_path):
                    if res:
                        print(fname, time)
                        for r in res:
                            print(f"  - {r}")

                        # roughly dump results somewhere for now
                        results.append((fname, time, res))

    if results:
        print("Some NODATA, negatives or high values found")


def check_nodata(path: pathlib.Path):
    res = []
    ds = xr.open_dataset(path, decode_timedelta=False)

    for t in ds.time.data:
        timeslice = ds.tco3.sel(time=t)

        # TODO: is this a slow operation?
        if not timeslice.notnull().all():
            res.append("Contains nulls")

        raw_data = timeslice.data

        if (raw_data < 0).any():
            res.append("Contains negatives (possible NCI NODATA?)")

        if (raw_data > 1e3).any():
            res.append("Contains higher positives (possible ERA5 NODATA?)")

        yield t, res


if __name__ == "__main__":
    # TODO:
    #  - get a dir, look for all NCs recursively
    #  - for each file, open, read data, look for +ve & -ve values near NODATA & report

    for i in sys.argv[1:]:
        input_dir = pathlib.Path(i)
        workflow(input_dir)
