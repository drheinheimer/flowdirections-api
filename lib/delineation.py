import os

from itertools import combinations
import json

import shapely
from pysheds.grid import Grid
import shapely.geometry as geom
from shapely import union, union_all, to_geojson, Point
import fiona
import numpy as np
import rasterio

dirmap = (64, 128, 1, 2, 4, 8, 16, 32)

data_dir = os.environ.get('DATA_DIR', './instance/data')
tif_tpl = f'{data_dir}/hyd_{{region}}_{{data}}_{{res}}s.tif'


class DirGrid(object):
    def __init__(self, res, region):
        fdir_tif = tif_tpl.format(region=region, data='dir', res=res)
        self.grid = Grid.from_raster(fdir_tif)
        self.fdir = self.grid.read_raster(fdir_tif)


def get_regions(lon, lat):
    if 90 < lon < 190 and lat < 8:  # prioritize Australia
        regions = ['au', 'as']
    elif 57 < lon < 155 and 7 < lat < 55:  # prioritize Asia
        regions = ['as', 'eu', 'au']
    elif -30 < lon < 55 and lat < 35:  # prioritize Africa
        regions = ['af', 'eu']
    elif -25 < lon < 70 and 12 < lat:  # prioritize Europe
        regions = ['eu', 'af', 'as']
    elif -82 < lon < -34 and lat < 15:
        regions = ['sa', 'na']
    elif -140 < lon < -52 and 7 < lat < 62:
        regions = ['na', 'sa']
    else:
        regions = ['na', 'sa', 'eu', 'af', 'as', 'au']

    return regions


def get_region(lon, lat):
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


class Outlet(object):

    def __init__(self, lon, lat, res, include_facc=False):
        self.lon = lon
        self.lat = lat
        region = get_region(lon, lat)
        dirgrid = DirGrid(res, region)
        self.grid = dirgrid.grid
        self.fdir = dirgrid.fdir

        if include_facc:
            self.facc_path = tif_tpl.format(region=region, data='acc', res=res)

    def get_facc(self):
        x = self.lon
        y = self.lat
        with rasterio.open(self.facc_path) as dataset:
            facc = list(dataset.sample([(x, y)]))[0][0]

        return facc

    def delineate(self, output='geojson', stringify=False):

        catchment = self.grid.catchment(x=self.lon, y=self.lat, fdir=self.fdir, dirmap=dirmap, snap='center')

        self.grid.clip_to(catchment)
        catch_view = self.grid.view(catchment, dtype=np.uint8)

        shapes = self.grid.polygonize(catch_view)

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
                            crs=self.grid.crs.srs,
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


def delineate_point(lon, lat, res=30):
    outlet = Outlet(lon, lat, res)
    return outlet.delineate()


def delineate_points(features, res=30):
    # step 1: create basic catchments
    # TODO: parallelize this!!!
    outlets = {}
    for feature in features:
        lon, lat = feature['geometry']['coordinates']
        outlet = Outlet(lon, lat, res, include_facc=True)
        catchment = outlet.delineate(output='shapely')
        facc = outlet.get_facc()
        outlets[(lon, lat)] = {
            'catchment': catchment,
            'facc': facc
        }

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
        f_str = shapely.to_geojson(outlet['catchment'])
        f = json.loads(f_str)
        if f['type'] == 'GeometryCollection':
            f['type'] = 'Feature'
            f['geometry'] = f['geometries'][0]
            f.pop('geometries')
        elif f['type'] in ['Polygon', 'MultiPolygon']:
            f = {
                'type': 'Feature',
                'geometry': f
            }
        features.append(f)

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    return geojson
