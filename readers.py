"""
TODO: readers for opening GRIB files with different libraries
"""

from osgeo import gdal
import pygrib

gdal.UseExceptions()


# TODO: add xarray GRIB reader

def read_data_pygrib(path, nband):
    # TODO: is band zero or one index?
    # TODO: add handling for large(r) data, such as global
    ds = pygrib.open(path)
    ds.seek(nband)
    record = ds.read(1)[0]  # extract from a list
    data = record.values
    ds.close()

    return data


def read_gdal_data(path, nband):
    ds = gdal.Open(path)
    band = ds.GetRasterBand(nband+1)
    data = band.ReadAsArray()  # TODO: warning performance for large arrays
    ds = None  # close dataset  # noqa

    return data
