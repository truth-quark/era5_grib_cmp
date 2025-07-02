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

# Pressure level variable names for NCI & raw ERA5 data
NCI_LEVEL = "level"
ERA5_LEVEL = "isobaricInhPa"

PRESSURE_LEVELS_SUBSET = [1000, 825, 550, 225, 50, 1]

# HACK: temp implement argparse later
STATS_PATH = os.environ.get("STATS_PATH")


# NB: this could be replaced with a CSV lookup to avoid code changes
ERA5_VARIABLES = ("2t", "z", "sp", "2d", "tco3", "r", "t")  # file path variable name
ERA5_NC_VARIABLES = ("t2m", "z", "sp", "d2m", "tco3", "r", "t")  # NetCDF data variable name

MIN_VALID_TEMPERATURE_K = 179.0  # K https://en.wikipedia.org/wiki/Lowest_temperature_recorded_on_Earth
MAX_VALID_TEMPERATURE_K = 320.0  # K https://en.wikipedia.org/wiki/Highest_temperature_recorded_on_Earth
MIN_VALID_PRESSURE_PA = 60000.0  # https://en.wikipedia.org/wiki/List_of_atmospheric_pressure_records_in_Europe#Land-based_observations_in_Europe
MAX_VALID_PRESSURE_PA = 107000.0
MIN_VALID_TOTAL_COLUMN_OZONE_KGM2 = 0.0021  # ~98 Dobson units
MAX_VALID_TOTAL_COLUMN_OZONE_KGM2 = 0.015  # ~700 Dobson units

MIN_RELATIVE_HUMIDITY = 0.0  # use MODTRAN min
MAX_RELATIVE_HUMIDITY = 100.0  # MODTRAN max


ERA5_SINGLE_LEVEL_NC_MIN = {"t2m": MIN_VALID_TEMPERATURE_K,
                             "z": None,
                             "sp": MIN_VALID_PRESSURE_PA,
                             "d2m": MIN_VALID_TEMPERATURE_K,
                             "tco3": MIN_VALID_TOTAL_COLUMN_OZONE_KGM2,
                            }

ERA5_SINGLE_LEVEL_NC_MAX = {"t2m": MAX_VALID_TEMPERATURE_K,
                             "z": None,
                             "sp": MAX_VALID_PRESSURE_PA,
                             "d2m": MAX_VALID_TEMPERATURE_K,
                             "tco3": MAX_VALID_TOTAL_COLUMN_OZONE_KGM2
                            }

ERA5_SINGLE_LEVEL_NC_NODATA = {"t2m": None,
                               "z": None,
                               "sp": None,
                               "d2m": None,
                               "tco3": None
                               }

# NB: Only r & t needed, can skip z/geopotential as it's a constant
ERA5_MULTI_LEVEL_NC_MIN = {
    "t": MIN_VALID_TEMPERATURE_K,
    "r": MIN_RELATIVE_HUMIDITY,
}

ERA5_MULTI_LEVEL_NC_MAX = {
    "t": MAX_VALID_TEMPERATURE_K,
    "r": MAX_RELATIVE_HUMIDITY,
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
    has_levels = False

    for input_dir_path in input_dir_paths:
        for file_path, var in netcdf_search(input_dir_path):
            ds = xr.open_dataset(file_path, decode_timedelta=False)

            if hasattr(ds, NCI_LEVEL) or hasattr(ds, ERA5_LEVEL):
                has_levels = True
                analyse_multi_level(ds, var, results, stats, file_path)
            else:
                analyse_single_level(ds, var, results, stats, file_path)

                if has_levels:
                    raise RuntimeError("Analysis mixes single & pressure level data")

    # reporting & statistics
    # structure of reports & stats changes with single/multi level
    if has_levels:
        print_report_levels(results)
    else:
        print_report(results)

    if stats and STATS_PATH:
        # NB: var shouldn't change unless search is too high in rt52 dir tree
        if has_levels:
            for level in PRESSURE_LEVELS_SUBSET:
                path = f"{var}_{level}_hPa_{STATS_PATH}"  # NB: breaks if STATS_PATH isn't a basename

                with open(path, "w") as mf:
                    dump_stats_level(mf, stats, var, level)
        else:
            with open(STATS_PATH, "w") as sf:
                dump_stats(sf, stats, var)


def analyse_single_level(ds, var, results, stats, file_path):
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


def analyse_multi_level(ds, var, results, stats, file_path):
    for time, level, geo_area in get_geo_area_levels(ds, var, PRESSURE_LEVELS_SUBSET):
        time_s = str(time.data)[:19]

        for res in check_nodata(
            geo_area,
            ERA5_MULTI_LEVEL_NC_MIN[var],
            ERA5_MULTI_LEVEL_NC_MAX[var]
        ):
            if res:
                # contains values potentially NODATA, too low or too high
                if level not in results[file_path]:
                    results[file_path][level] = {}

                results[file_path][level][time_s] = res

        summary_stats = get_summary_stats(geo_area)

        if not level in stats[file_path]:
            stats[file_path][level] = {}

        stats[file_path][level][time_s] = summary_stats


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
            print(f"File: {path_key}")  # NB: can display file paths with no warnings

            for time_key in sorted(results[path_key].keys()):
                print(f"\n{time_key}:")

                for r in results[path_key][time_key]:
                    print(r)

            print()  # split report outputs by month


def print_report_levels(results):
    if not results:
        return

    for level_key in PRESSURE_LEVELS_SUBSET:
        for path_key in sorted(results.keys()):
            print(f"File: {path_key}")

            if level_key in results[path_key]:  # not all levels will flag warnings
                for time_key in sorted(results[path_key][level_key].keys()):
                    print(f"\n{time_key} at {level_key} hPa:")

                    for r in results[path_key][level_key][time_key]:
                        print(r)

                print()  # split report outputs by month


def dump_stats(file_like, stats, var: str):
    file_like.write(f"TIMESTEP ({var}),MIN,MEAN,MAX\n")

    for path_key in sorted(stats.keys()):
        for time_key in sorted(stats[path_key].keys()):
            mmm = ",".join(str(v) for v in stats[path_key][time_key])
            file_like.write(f"{time_key},{mmm}\n")


def dump_stats_level(file_like, stats, var: str, level_key):
    """
    Write a CSV statistics file for a single level.

    :param file_like:
    :param stats:
    :param var:
    :param level_key:
    """
    file_like.write(f"TIMESTEP ({var}_{level_key}_hPa),MIN,MEAN,MAX\n")

    for path_key in sorted(stats.keys()):
        for time_key in sorted(stats[path_key][level_key].keys()):
            mmm = ",".join(str(v) for v in stats[path_key][level_key][time_key])
            file_like.write(f"{time_key},{mmm}")


def get_variable_name(file_path):
    for v, nv in zip(ERA5_VARIABLES, ERA5_NC_VARIABLES):
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


def get_geo_area_levels(ds, var: str, pressure_levels):
    """
    Yields geospatial areas for each time step in the Dataset.
    :param ds:
    :param var:
    :param pressure_levels:

    Yields time, pressure level, xarray.DataArray
    """
    # ERA5 time dimension differs between source & NCI data. Original ERA5 data
    # uses "valid_time", NCI shortens this to "time". Dynamically handle both.
    time_var = TIME if hasattr(ds, TIME) else VALID_TIME
    level_var = NCI_LEVEL if hasattr(ds, NCI_LEVEL) else ERA5_LEVEL

    # NB: ugly, uses module scope variable to dynamically adjust sel() query
    # TODO: pass in kwargs?
    for t in getattr(ds, time_var):
        for level in pressure_levels:
            _selection_args[time_var] = t
            _selection_args[level_var] = level
            geo_area = ds[var].sel(**_selection_args)
            yield t, level, geo_area


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
                f"Unique low/min values are {np.unique(raw_data[below_min_valid_mask])}"]
        res.extend(msgs)

    above_max_valid_mask = raw_data > max_valid

    if above_max_valid_mask.any():
        n_high_values = np.count_nonzero(above_max_valid_mask)
        high_percent = n_high_values / total_cells

        msgs = [f"Contains {n_high_values} values > {max_valid} ({high_percent:.2%})",
                f"Unique high/max values are {np.unique(raw_data[above_max_valid_mask])}"]
        res.extend(msgs)

    yield res


def get_summary_stats(geo_area: xr.DataArray):
    return float(geo_area.min()), float(geo_area.mean()), float(geo_area.max())


if __name__ == "__main__":
    workflow([pathlib.Path(i) for i in sys.argv[1:]])
