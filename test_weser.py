from pysheds.grid import Grid
import numpy as np


def delineate():
    lon = 8.495495612171311
    lat = 53.33938676253513

    fpath = './instance/data/hyd_eu_dir_30s.tif'

    grid = Grid.from_raster(fpath)
    fdir = grid.read_raster(fpath)

    catchment = grid.catchment(lon, lat, fdir, snap='center')
    grid.clip_to(catchment)
    catch_view = grid.view(catchment, dtype=np.uint8)
    shapes = list(grid.polygonize(catch_view))
    # print(shapes[0])


for i in range(10):
    print(i)
    delineate()
    print(f'{i} done')
