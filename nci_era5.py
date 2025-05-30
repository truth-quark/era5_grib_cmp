# import sys
# import xarray as xr
#
# nc_path = sys.argv[1]
#
# ds = xr.open_dataset(nc_path, decode_timedelta=False)
#
# for t in ds.time.data:
#     for level in ds.level.data:
#         data = ds.r.sel(time=t, level=level, method="nearest").data
#         if (data < 0).any():
#             print(f"Negative RH for {t}, {level} hPa")


import sys
import xarray as xr
import numpy as np

nc_path = sys.argv[1]

ds = xr.open_dataset(nc_path, decode_timedelta=False)
total_cells = np.multiply(*ds.r.shape[-2:])
spacing = len(str(total_cells))


for t in ds.time.data:
    print(f"time={t}")

    for level in ds.level.data:
        data = ds.r.sel(time=t, level=level, method="nearest").data

        negative_data = data < 0
        if negative_data.any():
            negative_count = np.count_nonzero(negative_data)
            n_percent = (negative_count / total_cells) * 100
            msg = f"{int(level):4d} hPa  Negative RH, {negative_count:>8} / {total_cells} cells ({n_percent:.2f}%)"
            print(msg)

        overflow_data = data > 100
        if overflow_data.any():
            overflow_count = np.count_nonzero(overflow_data)
            o_percent = (overflow_count / total_cells) * 100
            msg = f"{int(level):4d} hPa  Overflow RH, {overflow_count:>8} / {total_cells} cells ({o_percent:.2f}%)"
            print(msg)

    print()
