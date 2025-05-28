import readers as rd

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


@pytest.fixture
def aus_2_band_subset_path():
    return "data/20230201_reanalysis_rh_level_1hpa_2hpa_midnight_aus_subset.grib"


@pytest.fixture
def aus_6_band_subset_path():
    return "data/20230201_reanalysis_rh_3_pressure_levels_2_timestamps_aus_subset.grib"


def test_gdal_pygrib_single_band_read_matches(aus_1_band_subset_path):
    band = 0  # using 0 for 1st band

    gdal_data = rd.read_data_gdal(aus_1_band_subset_path, band)
    pygrib_data = rd.read_data_pygrib(aus_1_band_subset_path, band)
    xarray_data = rd.read_data_xarray(aus_1_band_subset_path, nband=None)

    matches = gdal_data == pygrib_data

    assert matches.all(), "GDAL & pygrib data reads are different"
    assert ((0.0 <= gdal_data) <= 100.0).all(), "Invalid GDAL RH data found"

    # second stage match
    matches2 = gdal_data == xarray_data
    assert matches2.all(), "GDAL & xarray data reads are different"
    assert ((0.0 <= xarray_data) <= 100.0).all(), "Invalid xarray RH data found"


# FIXME test a subset file with 1 timestamp & 2 pressure levels
def test_multi_band_read_matches(aus_2_band_subset_path):
    for band in (0, 1):

        # TODO: inefficient due to multiple file reads
        gdal_data = rd.read_data_gdal(aus_2_band_subset_path, band)
        pygrib_data = rd.read_data_pygrib(aus_2_band_subset_path, band)

        xband = -(band + 1)  # NB xarray bands appear to be reverse order!
        xarray_data = rd.read_data_xarray(aus_2_band_subset_path, xband)

        matches = gdal_data == pygrib_data
        assert matches.all(), f"GDAL & pygrib data reads are different for band {band}"
        assert ((0.0 <= gdal_data) <= 100.0).all(), f"Invalid GDAL RH data found for band {band}"

        # second stage match
        matches2 = gdal_data == xarray_data
        assert matches2.all(), f"GDAL & xarray data reads are different for band {band}"
        assert ((0.0 <= xarray_data) <= 100.0).all(), f"Invalid xarray RH data found for band {band}"


# FIXME test a subset file with 2 timestamps & 1 pressure level
# FIXME test a subset file with 2 timestamps & 3 pressure levels
def test_6_band_data_read(aus_6_band_subset_path):
    # gdal order from gdalinfo is:
    # timestep 0, pressure 1
    # timestep 0, pressure 2
    # timestep 0, pressure 3
    # timestep 1, pressure 1
    # timestep 1, pressure 2
    # timestep 1, pressure 3

    n_timestamps = 2
    n_pressure_levels = 3

    x_bands = {0: (0,0),
               1: (0,1),
               2: (0,2),
               3: (1,0),
               4: (1,1),
               5: (1,2),
               }

    # FIXME: find neater way for xarray "band" number
    for band in range(n_timestamps * n_pressure_levels):

        # TODO: inefficient due to multiple file reads
        gdal_data = rd.read_data_gdal(aus_6_band_subset_path, band)
        pygrib_data = rd.read_data_pygrib(aus_6_band_subset_path, band)
        xarray_data = rd.read_data_xarray(aus_6_band_subset_path, x_bands[band])

        matches = gdal_data == pygrib_data
        assert matches.all(), f"GDAL & pygrib data reads are different for band {band}"
        assert ((0.0 <= gdal_data) <= 100.0).all(), f"Invalid GDAL RH data found for band {band}"

        # second stage match
        matches2 = gdal_data == xarray_data
        assert matches2.all(), f"GDAL & xarray data reads are different for band {band}"
        assert ((0.0 <= xarray_data) <= 100.0).all(), f"Invalid xarray RH data found for band {band}"



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
