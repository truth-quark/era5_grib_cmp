# ERA5 GRIB / NCI NetCDF / XArray Data Exploration

Using `20230201_era5.data.grib` as the source GRIB file.

This is the multi level reanalysis data for the 24 one hour time steps for 1/2/2023.

## GDAL Data Analysis

GDAL reports data is 1440x721. Cell size is `0.25 x 0.25` degrees.

GDAL reports data is stored in `888` bands (672 timesteps * 37 pressure levels).

**TODO: which order are the levels stored?**

