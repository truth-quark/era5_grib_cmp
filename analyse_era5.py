"""
Data analysis/debugging work for analysing ERA5 GRIB & NCI NetCDF data.
"""

import datetime
from osgeo import gdal

gdal.UseExceptions()

# constants
GRIB_REF_TIME = "GRIB_REF_TIME"
TZ_UTC = datetime.timezone.utc

def main():
    grib_path = "data/20230201_era5_rh_global.data.grib"
    analyse_grib_gdal(grib_path)


def analyse_grib_gdal(path):
    ds = gdal.Open(path)
    assert isinstance(ds, gdal.Dataset)

    band1 = ds.GetRasterBand(1)
    assert isinstance(band1, gdal.Band)
    metadata = band1.GetMetadata()

    # GRIB_REF_TIME appears to be timestamp of *1st* hour in UTC
    # NB: datetime.datetime.fromtimestamp() without a tz arg results in the time
    #  being interpreted in the system timezone for that timestamp. 20230201 is
    #  assumed to be AEDT & the timestamp is +11 hours!
    ref_time = int(metadata[GRIB_REF_TIME])
    dt = datetime.datetime.fromtimestamp(ref_time, tz=TZ_UTC)

    assert dt.year == 2023
    assert dt.month == 2
    assert dt.day == 1
    debug(dt.hour, 0)
    assert dt.minute == 0
    assert dt.second == 0

    # read 1st band of 1[hPa] ISBL (Isobaric surface) / near top of atmos
    data = band1.ReadAsArray()
    _min, _max = data.min(), data.max()

    msg = f"rh value error 0.0 <= rh <= 100.0 is FALSE, (min {_min}, max {_max})"
    assert ((0.0 <= data) <= 100.0).all(), msg

    ds = None  # close dataset


def debug(actual, exp):
    assert exp == actual, f"Exp: {exp} != {actual}"


if __name__ == "__main__":
    main()
