import os
from copy import copy
import multiprocessing as mp
import json
import requests
from itertools import product, combinations
from functools import partial

from pysheds.grid import Grid
import shapely
from shapely import Point
import fiona
import numpy as np
import rasterio

dirmap = (64, 128, 1, 2, 4, 8, 16, 32)

data_dir = os.environ.get('DATA_DIR', './instance/data')
tif_tpl = f'{data_dir}/hyd_{{region}}_{{data}}_{{res}}s.tif'


def get_regions(lon, lat):
    if 90 < lon < 190 and lat < 8:  # prioritize Australia
        return ['au', 'as']
    elif 57 < lon < 155 and 7 < lat < 55:  # prioritize Asia
        return ['as', 'eu', 'au']
    elif -30 < lon < 55 and lat < 35:  # prioritize Africa
        return ['af', 'eu']
    elif -25 < lon < 70 and 12 < lat:  # prioritize Europe
        return ['eu', 'af', 'as']
    elif -82 < lon < -34 and lat < 15:
        return ['sa', 'na']
    elif -140 < lon < -52 and 7 < lat < 62:
        return ['na', 'sa']
    else:
        return ['na', 'sa', 'eu', 'af', 'as', 'au']


def shapes_to_geojson(shapes, stringify=False):
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

    if stringify:
        geojson = json.dumps(geojson)

    return geojson


class Delineator(object):
    filename_tpl = 'hyd_{region}_{data}_{res}s.{ext}'

    def __init__(self, regions, resolutions):
        self.grids = {}
        self.fdirs = {}
        self.faccs = {}
        self.masks = {}

        production = os.environ.get('DEPLOYMENT_MODE') == 'production'

        for region, res, data_type in product(regions, resolutions, ['dir', 'acc', 'msk']):

            if data_type == 'msk' and res == 15:
                continue

            print(f'Loading {data_type} for {region}, {res}s')

            data_dir = os.environ.get('DATA_DIR')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            ext = 'json' if data_type == 'msk' else 'tif'
            mode = 'w' if data_type == 'msk' else 'wb'
            fname = self.filename_tpl.format(region=region, data=data_type, res=res, ext=ext)
            fpath = f'{data_dir}/{fname}'

            if production:
                data_http_uri = os.environ.get('DATA_HTTP_URI')
                url = f'{data_http_uri}/{fname}'
                req = requests.get(url)
                with open(fpath, mode) as f:
                    f.write(req.content if mode == 'wb' else req.content.decode())

            key = (region, res)
            if data_type == 'dir':
                self.grids[key] = grid = Grid.from_raster(fpath)
                self.fdirs[key] = grid.read_raster(fpath)

    def get_region(self, lon, lat):
        regions = get_regions(lon, lat)
        point = Point(lon, lat)
        data_dir = os.environ.get('DATA_DIR', './instance/data')
        for region in regions:
            filename = f'{data_dir}/hyd_{region}_msk_30s.json'
            with open(filename) as f:
                gj_str = f.read()
            gj_geom = shapely.from_geojson(gj_str)

            if shapely.contains(gj_geom, point):
                return region

        raise 'No region found'

    def delineate_point(self, lon, lat, res=30, output='geojson', region=None, stringify=False):
        region = region or self.get_region(lon, lat)
        key = (region, res)
        grid = copy(self.grids[key])
        fdir = copy(self.fdirs[key])

        catchment = grid.catchment(x=lon, y=lat, fdir=fdir, dirmap=dirmap, snap='center')

        grid.clip_to(catchment)
        catch_view = grid.view(catchment, dtype=np.uint8)

        shapes = grid.polygonize(catch_view)

        if output == 'native':
            return shapes

        elif output == 'shapefile':

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
            return shapes_to_geojson(shapes)

        elif output == 'shapely':
            geojson = shapes_to_geojson(shapes, stringify=True)
            return shapely.from_geojson(geojson)

    def get_facc(self, lon, lat, region, res):
        facc_path = tif_tpl.format(region=region, data='acc', res=res)
        x = lon
        y = lat
        with rasterio.open(facc_path) as dataset:
            facc = list(dataset.sample([(x, y)]))[0][0]
        return facc

    def _delineate_point(self, feature, res=30):
        lon, lat = feature['geometry']['coordinates']
        region = self.get_region(lon, lat)
        catchment = self.delineate_point(lon, lat, res=res, region=region, output='shapely')
        delineation = {
            'coords': (lon, lat),
            'catchment': catchment,
            'facc': self.get_facc(lon, lat, region, res)
        }
        return delineation

    def delineate_points(self, features, res=30, parallel=False):
        # step 1: create basic catchments
        if parallel:
            pool = mp.Pool(processes=4)
            func = partial(self._delineate_point, res=30)
            delineations = pool.map(func, features)
        else:
            delineations = []
            for feature in features:
                delineation = self._delineate_point(feature, res=res)
                delineations.append(delineation)

        outlets = {d['coords']: d for d in delineations}
        catchment_combos = list(combinations(outlets.keys(), 2))
        for i, (p1, p2) in enumerate(catchment_combos):
            o1 = outlets.get(p1)
            o2 = outlets.get(p2)
            if not (o1 and o2):
                continue
            c1 = o1['catchment']
            c2 = o2['catchment']
            if not shapely.intersects(c1, c2):
                continue

            if o1['facc'] > o2['facc']:
                c1_new = shapely.difference(c1, c2)
                outlets[p1]['catchment'] = c1_new
            elif o1['facc'] < o2['facc']:
                c2_new = shapely.difference(c2, c1)
                outlets[p2]['catchment'] = c2_new

        features = []
        for outlet in outlets.values():
            geom = outlet['catchment']
            geom_type = geom.geom_type
            if geom_type == 'GeometryCollection':
                geometry = geom.geoms[0]  # TODO: check if this is valid
            elif geom_type == 'Polygon':
                geometry = geom
            elif geom_type == 'MultiPolygon':
                area_threshold = 1e-6  # TODO: confirm this threshold
                geometries = [g for g in geom.geoms if g.area >= area_threshold]
                if len(geometries) == 1:
                    geometry = geometries[0]
                else:
                    geometry = geometries[0]
            else:
                raise Exception(f'Unsupported geometry: {geom_type}')

            feature = {
                'type': 'Feature',
                'geometry': json.loads(shapely.to_geojson(geometry))
            }

            features.append(feature)

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

        return geojson
