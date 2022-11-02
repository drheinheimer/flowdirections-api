from pysheds.grid import Grid


def delineate_point(x, y):

    grid = Grid.from_raster('./data/hyd_na_dir_30s.tif', data_name='dir')
    fdir = grid.read_raster('./data/hyd_na_dir_30s.tif', data_name='dir')

    dirmap = (64, 128, 1, 2, 4, 8, 16, 32)

    catchment = grid.catchment(x, y, fdir, dirmap=dirmap, xytype='coordinate', snap='center')

    shapes = catchment.polygonize()

    return {
        'catchment': str(shapes)
    }
