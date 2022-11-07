from pysheds.grid import Grid
import fiona
import numpy as np


def delineate_point(lat, lon, res=30, output='geojson', name=None):
    tif = f'./data/hyd_na_dir_{res}s.tif'

    grid = Grid.from_raster(tif)
    fdir = grid.read_raster(tif)

    dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
    catchment = grid.catchment(x=lon, y=lat, fdir=fdir, dirmap=dirmap, snap='center')

    grid.clip_to(catchment)
    catch_view = grid.view(catchment, dtype=np.uint8)

    shapes = grid.polygonize(catch_view)

    if output == 'shapefile':

        # Specify schema
        schema = {
            'geometry': 'Polygon',
            'properties': {'LABEL': 'float:16'}
        }

        # Write shapefile
        with fiona.open('catchment.shp', 'w',
                        driver='ESRI Shapefile',
                        crs=grid.crs.srs,
                        schema=schema) as c:
            i = 0
            for shape, value in shapes:
                rec = {}
                rec['geometry'] = shape
                rec['properties'] = {'LABEL': str(value)}
                rec['id'] = str(i)
                c.write(rec)
                i += 1

    elif output == 'geojson':

        features = []

        for shape, value in shapes:
            feature = {
                "type": "Feature",
                "geometry": shape,
                "properties": {
                    "value": value
                }
            }
            features.append(feature)

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

        return geojson
