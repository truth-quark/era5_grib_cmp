import readers
from osgeo import gdal

import numpy as np

gdal.UseExceptions()


# TODO: create unittests module
#       - single band file matches (subset)
#       - three band file matches  1, 500, 1000hPa
#       - grab larger file with bigger extents
# TODO: test unit conversions (units in meta?) (should be percent)


path = "data/20230201_reanalysis_rh_level_1hpa_midnight_aus_subset.grib"
band = 0  # using 0 for 1st band

grib_data = readers.read_data_pygrib(path, band)
print("Got GRIB")
gdal_data = readers.read_gdal_data(path, band)
print("Got GDAL")

matches = grib_data == gdal_data

nlat, nlon = gdal_data.shape

for i in range(nlat):
    print(f"Row {i}")
    for a,b in zip(grib_data[i], gdal_data[i]):
        print(f"{a}\t{b}\tdiff {abs(a-b)}")

for i in range(nlat):
    matching = grib_data[i] == gdal_data[i]
    assert matching.all(), f"row {i} cmp failed  {np.count_nonzero(matching)} of {nlat} matched"
    # assert (grib_data[-1] == gdal_data[0]).all(), "grib[-1] to gdal[0] failed"


nz = np.count_nonzero(matches)
total_cells = np.multiply(*matches.shape)
match_percent = (nz / total_cells) * 100

print(f"Data matches: {matches.all()}")
print(f"Matching cells: {match_percent}%   exact matches: {nz} from {total_cells} cells")

diff = np.abs(gdal_data - grib_data)
print(f"min diff={diff.min()}  max diff={diff.max()}")
