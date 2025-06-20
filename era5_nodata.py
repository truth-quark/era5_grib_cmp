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


# NB: this could be replaced with a CSV lookup to avoid code changes
ERA5_SINGLE_LEVEL_VARIABLES = ("2t", "z", "sp", "2d")
ERA5_SINGLE_LEVEL_NC_VARIABLES = ("t2m", "z", "sp", "d2m")

MIN_VALID_TEMPERATURE_K = 179.0  # K https://en.wikipedia.org/wiki/Lowest_temperature_recorded_on_Earth
MAX_VALID_TEMPERATURE_K = 320.0  # K https://en.wikipedia.org/wiki/Highest_temperature_recorded_on_Earth
MIN_VALID_PRESSURE_PA = 90000.0  # https://en.wikipedia.org/wiki/List_of_atmospheric_pressure_records_in_Europe#Land-based_observations_in_Europe
MAX_VALID_PRESSURE_PA = 107000.0


ERA5_SINGLE_LEVEL_NC_MIN = {"t2m": MIN_VALID_TEMPERATURE_K,
                             "z": None,
                             "sp": MIN_VALID_PRESSURE_PA,
                             "d2m": MIN_VALID_TEMPERATURE_K,
                            }

ERA5_SINGLE_LEVEL_NC_MAX = {"t2m": MAX_VALID_TEMPERATURE_K,
                             "z": None,
                             "sp": MAX_VALID_PRESSURE_PA,
                             "d2m": MAX_VALID_TEMPERATURE_K,
                            }

ERA5_SINGLE_LEVEL_NC_NODATA = {"t2m": None,
                               "z": None,
                               "sp": None,
                               "d2m": None
                               }


# TODO: work on an assumption this script takes ERA5 year dirs
#  each dir of single level files contains 12 months
#  - detect filename variable, match to NC variable
#  - feed in NODATA, valid min/max


def workflow(input_dir_path):
    results = collections.defaultdict(dict)

    for dirpath, dirnames, filenames in os.walk(input_dir_path):
        dirpath = pathlib.Path(dirpath)

        for fname in filenames:
            var = get_variable_name(fname)

            if var is None:
                raise NotImplementedError(f"No handler for {fname}")

            file_path = dirpath / fname

            if file_path.name.endswith(".nc") or file_path.name.endswith(".nc4"):
                if DEBUG:
                    print(f"Scanning {file_path}")

                for time, res in check_nodata(file_path, var,
                                              ERA5_SINGLE_LEVEL_NC_MIN[var],
                                              ERA5_SINGLE_LEVEL_NC_MAX[var]):
                    if res:
                        # contains possible NODATA or "bad" values
                        results[file_path][time] = res

    print_report(results, input_dir_path)


def print_report(results, input_dir_path):
    # quick report
    if results:
        for path_key in sorted(results.keys()):
            print(path_key)

            for time_key in sorted(results[path_key].keys()):
                print(f"{time_key}: {results[path_key][time_key]}")
            print()  # split report outputs by month

    if results:
        print("RESULT: Some NODATA, negatives or high values found")
    else:
        print(f"RESULT: {input_dir_path} checks out free of NODATA")


def get_variable_name(file_path):
    for v, nv in zip(ERA5_SINGLE_LEVEL_VARIABLES, ERA5_SINGLE_LEVEL_NC_VARIABLES):
        if file_path.startswith(v):
            return nv


def check_nodata(path: pathlib.Path, var: str, min_valid, max_valid):
    ds = xr.open_dataset(path, decode_timedelta=False)

    for t in ds.time.data:
        res = []
        geo_area = ds[var].sel(time=t)

        # NB: all 3 check operations take ~1-2 seconds on NCI
        #  The slower aspect is checking 24 timesteps over 28+ days per month
        if not geo_area.notnull().all():
            res.append("Contains nulls")

        if DEBUG:
            print(f"  Null check completed")

        raw_data = geo_area.data
        below_min_valid_mask = raw_data < min_valid

        if below_min_valid_mask.any():
            below_min_values = raw_data[below_min_valid_mask]
            res.append(f"Contains values below {min_valid} (possible NCI NODATA?)")
            res.append(f"Min values are {below_min_values}")

        if DEBUG:
            print(f"  Below min valid check completed")

        above_max_valid_mask = raw_data > max_valid

        if above_max_valid_mask.any():
            above_max_values = raw_data[above_max_valid_mask]
            res.append(f"Contains positive values > {max_valid} (possible ERA5 NODATA?)")
            res.append(f"Max values are {above_max_values}")

        if DEBUG:
            print(f"  Above max valid check completed")
            print(f"Completed {t} check at {datetime.datetime.now()}")  # help with timing estimates

        yield t, res


if __name__ == "__main__":
    for i in sys.argv[1:]:
        input_dir = pathlib.Path(i)
        workflow(input_dir)
