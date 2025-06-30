"""
ECMWF ERA5 Exploratory Data Analysis

This script analyses NCI's ECMWF ERA5 NetCDF files to determine if `tco3` or
total column of ozone files contain NODATA values.

USAGE:  python3 era5_nodata.py [NC_DIR]
"""

import os
import sys
import pathlib
# import datetime
import collections
import warnings

import numpy as np
import xarray as xr


TIME = "time"
VALID_TIME = "valid_time"
DEBUG = "DEBUG" in os.environ
SUBSET = "SUBSET" in os.environ  # limit calculations to Antarctic area

# HACK: temp implement argparse later
STATS_PATH = os.environ.get("STATS_PATH")


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

# TODO: tmp ugly option to configure dynamic xr dataset selection ops
_selection_args = {"latitude": slice(-60, -90)} if SUBSET else {}


# TODO: work on an assumption this script takes ERA5 year dirs
#  each dir of single level files contains 12 months
#  - detect filename variable, match to NC variable
#  - feed in NODATA, valid min/max


def workflow(input_dir_paths):
    results = collections.defaultdict(dict)
    stats = collections.defaultdict(dict)

    for input_dir_path in input_dir_paths:
        # TODO: potentially convert to funcs & return data?
        for file_path, var in netcdf_search(input_dir_path):
            ds = xr.open_dataset(file_path, decode_timedelta=False)

            for time, geo_area in get_geo_area(ds, var):
                time_s = str(time.data)[:19]

                for res in check_nodata(
                    geo_area,
                    ERA5_SINGLE_LEVEL_NC_MIN[var],
                    ERA5_SINGLE_LEVEL_NC_MAX[var]
                ):
                    if res:
                        # contains values potentially NODATA, too low or too high
                        results[file_path][time_s] = res

                summary_stats = get_summary_stats(geo_area)
                stats[file_path][time_s] = summary_stats

    # FIXME: expand to work with pressure-levels? CSV by equivalent level?
    print_report(results)

    if stats and STATS_PATH:
        with open(STATS_PATH, "w") as sf:
            # NB: var shouldn't change unless search is too high in dir tree
            dump_stats(sf, stats, var)


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


def print_report(results):
    # quick report
    if results:
        for path_key in sorted(results.keys()):
            print(f"File: {path_key}")

            for time_key in sorted(results[path_key].keys()):
                print(f"\n{time_key}:")

                for r in results[path_key][time_key]:
                    print(r)

            print()  # split report outputs by month


def dump_stats(file_like, stats, var: str):
    file_like.write(f"TIMESTEP ({var}),MIN,MEAN,MAX\n")

    for path_key in sorted(stats.keys()):
        for time_key in sorted(stats[path_key].keys()):
            mmm = ",".join(str(v) for v in stats[path_key][time_key])
            file_like.write(f"{time_key},{mmm}\n")


def get_variable_name(file_path):
    for v, nv in zip(ERA5_SINGLE_LEVEL_VARIABLES, ERA5_SINGLE_LEVEL_NC_VARIABLES):
        if file_path.startswith(v):
            return nv


def get_geo_area(ds, var: str):
    """
    Yields geospatial areas for each time step in the Dataset.
    :param ds:
    :param var:

    Yields time, xarray.DataArray
    """
    # ERA5 time dimension differs between source & NCI data. Original ERA5 data
    # uses "valid_time", NCI shortens this to "time". Dynamically handle both.
    time_var = TIME if hasattr(ds, TIME) else VALID_TIME

    # NB: ugly, uses module scope variable to dynamically adjust sel() query
    # TODO: pass in kwargs?
    for t in getattr(ds, time_var):
        _selection_args[time_var] = t
        geo_area = ds[var].sel(**_selection_args)
        yield t, geo_area


def check_nodata(geo_area: xr.DataArray, min_valid, max_valid):
    n_latitudes, n_longitudes = geo_area.shape
    total_cells = n_latitudes * n_longitudes
    res = []

    # NB: all 3 check operations take ~1-2 seconds on NCI
    #  Slower aspect is checking 24 time steps over 28-31 days per month
    if not geo_area.notnull().all():
        res.append("Contains nulls")

    raw_data = geo_area.data
    below_min_valid_mask = raw_data < min_valid

    if below_min_valid_mask.any():
        n_low_values = np.count_nonzero(below_min_valid_mask)
        low_percent = n_low_values / total_cells

        msgs = [f"Contains {n_low_values} values < {min_valid} ({low_percent:.2%})",
                f"Unique min values are {np.unique(raw_data[below_min_valid_mask])}"]
        res.extend(msgs)

    above_max_valid_mask = raw_data > max_valid

    if above_max_valid_mask.any():
        n_high_values = np.count_nonzero(above_max_valid_mask)
        high_percent = n_high_values / total_cells

        msgs = [f"Contains {n_high_values} positive values > {max_valid} ({high_percent:.2%})",
                f"Unique max values are {np.unique(raw_data[above_max_valid_mask])}"]
        res.extend(msgs)

    yield res


def get_summary_stats(geo_area: xr.DataArray):
    return float(geo_area.min()), float(geo_area.mean()), float(geo_area.max())


if __name__ == "__main__":
    workflow([pathlib.Path(i) for i in sys.argv[1:]])
