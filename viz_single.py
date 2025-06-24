"""
ERA5 Single Level, Single Variable Data Visualisation

TODO: code to work with `sp` first, then generify
"""

import sys
import datetime
import pathlib

import numpy as np
import xarray as xr
from PIL import Image


MIN_VALID_PRESSURE_PA = 90000.0  # https://en.wikipedia.org/wiki/List_of_atmospheric_pressure_records_in_Europe#Land-based_observations_in_Europe
MAX_VALID_PRESSURE_PA = 107000.0
DIFF = MAX_VALID_PRESSURE_PA - MIN_VALID_PRESSURE_PA

MIN_SP_BOUND = 47500
MIN_SP_BOUND_DIFF = abs(MIN_VALID_PRESSURE_PA - MIN_SP_BOUND)

# colours for viewing RH & outside 0-100 range
RED = (200, 0, 0)
DARK_RED = (100, 0, 0)
BLUE = (0, 0, 200)

VARIABLE = "sp"


def workflow(ds: xr.Dataset,
             dest_dir: pathlib.Path,
             underflow,
             overflow):

    height, width = ds[VARIABLE].shape[-2:]
    total_cells = height * width

    if not dest_dir.exists():
        dest_dir.mkdir(parents=True)

    for t in ds.time.data:
        dt = datetime.datetime.fromisoformat(str(t))

        timestamp = f"{dt.year}-{dt.month:02d}-{dt.day:02d}_T{dt.hour:02d}{dt.minute:02d}"
        png_path = dest_dir / f"{timestamp}_sp_plot.png"

        raw_global_data = ds[VARIABLE].sel(time=t, method="nearest").data
        scaled_global_data = ((raw_global_data - MIN_VALID_PRESSURE_PA) / DIFF) * 255
        underflow_mask = raw_global_data < underflow
        underflow_scaled = ((MIN_VALID_PRESSURE_PA - raw_global_data) / MIN_SP_BOUND_DIFF) * 255
        overflow_mask = raw_global_data > overflow

        if overflow_mask.any():
            msg = "Overflow detected but no handling is implemented"
            raise  NotImplementedError(msg)

        image = Image.new(mode="RGB", size=(width, height))
        idata = image.load()

        # TODO: pixel by pixel access to is slow, check API for passing arrays to PIL
        for x in range(image.size[0]):
            for y in range(image.size[1]):
                if underflow_mask[y, x]:
                    red_scaled =  int(underflow_scaled[y, x])
                    idata[x, y] = (red_scaled, 0, 0)  # modify red intensity
                # elif overflow_mask[y, x]:
                #     idata[x, y] = BLUE
                else:
                    pixel = int(scaled_global_data[y, x])
                    idata[x, y] = (pixel, pixel, pixel)  # should be greyscale

        image.save(png_path)

        if underflow_count := np.count_nonzero(underflow_mask):
            under_percent = round((underflow_count / total_cells) * 100, 2)
            print(f"Underflow values detected {under_percent}% of cells: {png_path}")

        # if overflow_count := np.count_nonzero(overflow_mask):
        #     overflow_percent = round((overflow_count / total_cells) * 100, 2)
        #     print(f"Overflow values detected {overflow_percent}% of cells: {png_path}")


def main():
    # TODO: add parser
    # parser = argparse.ArgumentParser(description="Visualise single level ERA5 datasets")
    # parser.add_argument("-d", "--dest-dir", help="Directory to save to")

    input_path = sys.argv[1]
    ds = xr.open_dataset(input_path, decode_timedelta=False)
    dest_dir = pathlib.Path("tmp-output")
    workflow(ds, dest_dir, MIN_VALID_PRESSURE_PA, MAX_VALID_PRESSURE_PA)


if __name__ == "__main__":
    main()
