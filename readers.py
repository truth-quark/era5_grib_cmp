"""
TODO: readers for opening GRIB files with different libraries
"""

from osgeo import gdal
import pygrib
import xarray as xr

gdal.UseExceptions()


def read_data_pygrib(path, nband):
    # Treat band as zero indexed
    # TODO: add handling for large(r) data, such as global
    ds = pygrib.open(path)
    ds.seek(nband)
    record = ds.read(1)[0]  # extract from a list
    data = record.values
    ds.close()

    return data


def read_data_gdal(path, nband):
    ds = gdal.Open(path)
    band = ds.GetRasterBand(nband+1)
    data = band.ReadAsArray()  # TODO: warning performance for large arrays
    ds = None  # close dataset  # noqa

    return data


def read_data_xarray(path, nband):
    # TODO: does xarray use GDAL???
    # checked in virtual env, raw xarray from pip does NOT have a GDAL dependency

    ds = xr.open_dataset(path, engine="cfgrib", decode_timedelta=False)

    assert ds.r is not None
    if ds.r.dims == ('latitude', 'longitude'):
        # there are no time or pressure dimensions, ignore nband & return data
        return ds.r.data

    raise NotImplementedError("Handle time/pressure bands")
