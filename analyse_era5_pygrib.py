import readers as rd

import numpy as np
import pytest


# TODO: create unittests module
#       - single band file matches (subset)
#       - three band file matches  1, 500, 1000hPa
#       - grab larger file with bigger extents
#       - test multiple time stamps as it affects bands/band order
# TODO: test unit conversions (units in meta?) (should be percent)


@pytest.fixture
def aus_1_band_subset_path():
    # RH data with 1 time step & one pressure level
    # This is contrived but limits the number of variables in reader testing
    return "data/20230201_reanalysis_rh_level_1hpa_midnight_aus_subset.grib"


def test_gdal_pygrib_single_band_read_matches(aus_1_band_subset_path):
    band = 0  # using 0 for 1st band

    gdal_data = rd.read_gdal_data(aus_1_band_subset_path, band)
    pygrib_data = rd.read_data_pygrib(aus_1_band_subset_path, band)

    matches = pygrib_data == gdal_data

    assert matches.all(), "GDAL & pygrib data reads are different"
    assert ((0.0 <= gdal_data) <= 100.0).all(), "Invalid RH data found"


# nlat, nlon = gdal_data.shape
#
# for i in range(nlat):
#     print(f"Row {i}")
#     for a,b in zip(grib_data[i], gdal_data[i]):
#         print(f"{a}\t{b}\tdiff {abs(a-b)}")
#
# for i in range(nlat):
#     matching = grib_data[i] == gdal_data[i]
#     assert matching.all(), f"row {i} cmp failed  {np.count_nonzero(matching)} of {nlat} matched"
#     # assert (grib_data[-1] == gdal_data[0]).all(), "grib[-1] to gdal[0] failed"
#
#
# nz = np.count_nonzero(matches)
# total_cells = np.multiply(*matches.shape)
# match_percent = (nz / total_cells) * 100
#
# print(f"Data matches: {matches.all()}")
# print(f"Matching cells: {match_percent}%   exact matches: {nz} from {total_cells} cells")
#
# diff = np.abs(gdal_data - grib_data)
# print(f"min diff={diff.min()}  max diff={diff.max()}")
