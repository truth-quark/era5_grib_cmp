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
import warnings

import numpy as np
import xarray as xr


DEBUG = "DEBUG" in os.environ
SUBSET = "SUBSET" in os.environ  # limit calculations to Antarctic area


# NB: this could be replaced with a CSV lookup to avoid code changes
ERA5_SINGLE_LEVEL_VARIABLES = ("2t", "z", "sp", "2d")
ERA5_SINGLE_LEVEL_NC_VARIABLES = ("t2m", "z", "sp", "d2m")

MIN_VALID_TEMPERATURE_K = 179.0  # K https://en.wikipedia.org/wiki/Lowest_temperature_recorded_on_Earth
MAX_VALID_TEMPERATURE_K = 320.0  # K https://en.wikipedia.org/wiki/Highest_temperature_recorded_on_Earth
MIN_VALID_PRESSURE_PA = 60000.0  # https://en.wikipedia.org/wiki/List_of_atmospheric_pressure_records_in_Europe#Land-based_observations_in_Europe
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

    for file_path, var in netcdf_search(input_dir_path):
        if DEBUG:
            print(f"Scanning {file_path}")

        for time, res in check_nodata(file_path, var,
                                      ERA5_SINGLE_LEVEL_NC_MIN[var],
                                      ERA5_SINGLE_LEVEL_NC_MAX[var]):
            if res:
                # contains values potentially NODATA, too low or too high
                results[file_path][time] = res

    print_report(results, input_dir_path)


def netcdf_search(input_dir_path):
    # Can't use simpler pathlib.walk() until Python 3.12
    for dirpath, dirnames, filenames in os.walk(input_dir_path):
        dirpath = pathlib.Path(dirpath)

        for fname in filenames:
            var = get_variable_name(fname)

            if var is None:
                raise NotImplementedError(f"No handler for {fname}")

            file_path = dirpath / fname

            if file_path.name.endswith(".nc") or file_path.name.endswith(".nc4"):
                yield file_path, var
            else:
                warnings.warn(f"Skipping unrecognised {file_path}")


def print_report(results, input_dir_path):
    # quick report
    if results:
        for path_key in sorted(results.keys()):
            print(path_key)

            for time_key in sorted(results[path_key].keys()):
                print(f"{time_key}:")

                for r in results[path_key][time_key]:
                    print(r)

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

    if SUBSET:
        geo_area = ds[var].sel(time=ds.time.data[0], latitude=slice(-60, -90))
        n_latitudes, n_longitudes = geo_area.shape

        if geo_area.latitude[0] != -60.0:
            raise RuntimeError(f"Why is 1st latitude {var.latitude[0]} not -60?")
    else:
        _, n_latitudes, n_longitudes = ds[var].shape

    total_cells = n_latitudes * n_longitudes

    for t in ds.time.data:
        res = []
        geo_area = ds[var].sel(time=t, latitude=slice(-60, -90)) if SUBSET else ds[var].sel(time=t)

        # NB: all 3 check operations take ~1-2 seconds on NCI
        #  The slower aspect is checking 24 timesteps over 28+ days per month
        if not geo_area.notnull().all():
            res.append("Contains nulls")

        # if DEBUG:
        #     print(f"  Null check completed")

        raw_data = geo_area.data
        below_min_valid_mask = raw_data < min_valid

        if below_min_valid_mask.any():
            n_low_values = np.count_nonzero(below_min_valid_mask)
            low_percent = n_low_values / total_cells

            msgs = [f"Contains {n_low_values} values < {min_valid} ({low_percent:.2%})",
                    f"Unique min values are {np.unique(raw_data[below_min_valid_mask])}"]
            res.extend(msgs)

        # if DEBUG:
        #     print(f"  Below min valid check completed")

        above_max_valid_mask = raw_data > max_valid

        if above_max_valid_mask.any():
            n_high_values = np.count_nonzero(above_max_valid_mask)
            high_percent = n_high_values / total_cells

            msgs = [f"Contains {n_high_values} positive values > {max_valid} ({high_percent:.2%})",
                    f"Unique max values are {np.unique(raw_data[above_max_valid_mask])}"]
            res.extend(msgs)

        # if DEBUG:
        #     print(f"  Above max valid check completed")
        #     print(f"Completed {t} check at {datetime.datetime.now()}")  # help with timing estimates

        yield t, res


if __name__ == "__main__":
    for i in sys.argv[1:]:
        input_dir = pathlib.Path(i)
        workflow(input_dir)
