"""
ECMWF ERA5 Exploratory Data Analysis

This script analyses NCI's ECMWF ERA5 NetCDF files to determine if `tco3` or
total column of ozone files contain NODATA values.

USAGE:  python3 era5_nodata.py [NC_DIR]
"""

import os
import sys
import pathlib
import datetime
import collections

import xarray as xr


DEBUG = "DEBUG" in os.environ


def workflow(input_dir_path):
    results = collections.defaultdict(dict)

    for dirpath, dirnames, filenames in os.walk(input_dir_path):
        dirpath = pathlib.Path(dirpath)

        for fname in filenames:
            file_path = dirpath / fname

            if file_path.name.endswith(".nc") or file_path.name.endswith(".nc4"):
                if DEBUG:
                    print(f"Scanning {file_path}")

                for time, res in check_nodata(file_path):
                    if res:
                        # contains possible NODATA or "bad" values
                        results[file_path][time] = res

    # quick report
    if results:
        for path_key in sorted(results.keys()):
            for time_key in sorted(results[path_key].keys()):
                print(f"{path_key} @ {time_key}: {results[path_key][time_key]}")

    if results:
        print("Some NODATA, negatives or high values found")
    else:
        print(f"{input_dir_path} checks out free of NODATA")


def check_nodata(path: pathlib.Path):
    res = []
    ds = xr.open_dataset(path, decode_timedelta=False)

    for t in ds.time.data:
        geo_area = ds.tco3.sel(time=t)

        # NB: all 3 check operations take ~1-2 seconds on NCI
        #  The slower aspect is checking 24 timesteps over 28+ days per month
        if not geo_area.notnull().all():
            res.append("Contains nulls")

        if DEBUG:
            print(f"  Null check completed")

        raw_data = geo_area.data

        if (raw_data < 0).any():
            res.append("Contains negatives (possible NCI NODATA?)")

        if DEBUG:
            print(f"  -ve check completed")

        if (raw_data > 1e3).any():
            res.append("Contains higher positives (possible ERA5 NODATA?)")

        if DEBUG:
            print(f"  +ve overflow check completed")
            print(f"Completed {t} at {datetime.datetime.now()}")

        yield t, res


if __name__ == "__main__":
    for i in sys.argv[1:]:
        input_dir = pathlib.Path(i)
        workflow(input_dir)
