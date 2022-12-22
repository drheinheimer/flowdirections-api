import os
import multiprocessing as mp
import json
from itertools import combinations
from functools import partial
from math import floor

import logging

from pysheds.grid import Grid
import shapely
import fiona
import numpy as np
import rasterio
from redis import Redis

import dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

data_dir = os.environ.get('DATA_DIR', './instance/data')

try:
    redis_host = os.environ['REDIS_HOST']
    redis = Redis(
        host=redis_host,
        port=os.environ.get('REDIS_PORT', 6379),
        password=os.environ.get('REDIS_PASSWORD')
    )
    logging.info(f'Starting with REDIS on server {redis_host}')
except:
    redis = None
    logging.warning('Starting without REDIS')


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


def shapes_to_geojson(shapes, remove_sinks=False, stringify=False):
    features = []

    for geometry, value in shapes:
        if remove_sinks:
            geometry.update(
                coordinates=[geometry['coordinates'][0]]
            )
        feature = {
            "type": "Feature",
            "geometry": geometry,
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


filename_tpl = 'hyd_{region}_{data}_{res}s.{ext}'


def get_region(lon, lat):
    regions = get_regions(lon, lat)
    point = shapely.Point(lon, lat)
    for region in regions:
        filename = f'{data_dir}/hyd_{region}_msk_30s.json'
        with open(filename) as f:
            gj_str = f.read()
        gj_geom = shapely.from_geojson(gj_str)

        if shapely.contains(gj_geom, point):
            return region

    raise 'No region found'


def snap_to_center(n, res):
    r = res / 60 / 60
    N = floor(n / r) * r + r / 2
    return round(N * 10000) / 10000


def delineate_point(lon, lat, res=30, output='geojson', region=None, remove_sinks=False, memcache=True):
    _lon = snap_to_center(lon, res)
    _lat = snap_to_center(lat, res)
    memory_key = f'{_lon}:{_lat}:{res}:{remove_sinks}'
    if memcache and output == 'geojson' and redis:
        stored_catchment = redis.get(memory_key)
        if stored_catchment:
            return json.loads(stored_catchment.decode())

    region = region or get_region(lon, lat)
    fname = filename_tpl.format(region=region, data='dir', res=res, ext='tif')
    fpath = f'{data_dir}/{fname}'
    grid = Grid.from_raster(fpath)
    fdir = grid.read_raster(fpath)
    catchment = grid.catchment(lon, lat, fdir, snap='center')
    grid.clip_to(catchment)
    catch_view = grid.view(catchment, dtype=np.uint8)
    shapes = grid.polygonize(catch_view)

    result = None

    if output == 'native':
        result = shapes

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
        result = shapes_to_geojson(shapes, remove_sinks=remove_sinks)
        if redis:
            redis.set(memory_key, json.dumps(result))

    elif output == 'shapely':
        geojson = shapes_to_geojson(shapes, stringify=True)
        result = shapely.from_geojson(geojson)

    return result


def get_facc(lon, lat, region, res):
    facc_fname = filename_tpl.format(region=region, data='acc', res=res, ext='tif')
    facc_path = f'{data_dir}/{facc_fname}'
    with rasterio.open(facc_path) as dataset:
        facc = list(dataset.sample([(lon, lat)]))[0][0]
    return facc


def _delineate_point(feature, res=30):
    lon, lat = feature['geometry']['coordinates']
    region = get_region(lon, lat)
    catchment = delineate_point(lon, lat, res=res, region=region, output='shapely')
    delineation = {
        'coords': (lon, lat),
        'catchment': catchment,
        'facc': get_facc(lon, lat, region, res)
    }
    return delineation


def delineate_points(features, res=30, parallel=False):
    # step 1: create basic catchments
    if parallel:
        pool = mp.Pool(processes=4)
        func = partial(_delineate_point, res=30)
        delineations = pool.map(func, features)
    else:
        delineations = []
        for feature in features:
            delineation = _delineate_point(feature, res=res)
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
