import os
import json
from itertools import combinations

import logging

from pysheds.grid import Grid
import shapely
import numpy as np
import rasterio

import dotenv

dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)

data_dir = os.environ.get('DATA_DIR', './instance/data')


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


def shapes_to_geojson(lon, lat, shapes, region=None, remove_sinks=False, stringify=False):
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
                "value": value,
                "outlet_coords": [lon, lat]
            }
        }
        features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'properties': {
            'region': region,
            'outlet_coords': [lon, lat]
        }
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


def delineate_point(lon, lat, res=30, region=None, remove_sinks=False):
    region = region or get_region(lon, lat)
    fname = filename_tpl.format(region=region, data='dir', res=res, ext='tif')
    fpath = f'{data_dir}/{fname}'
    grid = Grid.from_raster(fpath)
    fdir = grid.read_raster(fpath)
    catchment = grid.catchment(lon, lat, fdir, snap='center')
    grid.clip_to(catchment)
    catch_view = grid.view(catchment, dtype=np.uint8)
    shapes = grid.polygonize(catch_view)

    result = shapes_to_geojson(lon, lat, shapes, region=region, remove_sinks=remove_sinks)

    return result


def delineations_to_subcatchments(delineations):
    catchments = {}
    for d in delineations:
        coords = tuple(d['properties']['outlet_coords'])
        geom = shapely.from_geojson(json.dumps(d))
        catchments[coords] = geom

    catchment_combos = list(combinations(catchments.keys(), 2))
    for i, (p1, p2) in enumerate(catchment_combos):
        c1 = catchments[p1]
        c2 = catchments[p2]

        # the core algorithm
        if shapely.contains_xy(c1, *p2):
            catchments[p1] = shapely.difference(c1, c2)
        elif shapely.contains_xy(c2, *p1):
            catchments[p2] = shapely.difference(c2, c1)

    features = []
    for point, geom in catchments.items():
        geom_type = geom.geom_type
        if geom_type == 'Polygon':
            geometry = geom
        elif geom_type in ['MultiPolygon', 'GeometryCollection']:
            area_threshold = 1e-6  # TODO: confirm this threshold
            geometries = [g for g in geom.geoms if g.area >= area_threshold]
            geometry = geometries[0]  # TODO: confirm
        else:
            raise Exception(f'Unsupported geometry: {geom_type}')

        feature = {
            'type': 'Feature',
            'properties': {
                'outlet_coords': list(point)
            },
            'geometry': json.loads(shapely.to_geojson(geometry)),
        }

        features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features,
    }

    return geojson


def delineate_points(features, res=30):
    delineations = []
    for feature in features:
        # delineation = _delineate_point(feature, res=res)
        lon, lat = feature['geometry']['coordinates']
        region = get_region(lon, lat)
        catchment = delineate_point(lon, lat, res=res, region=region)
        delineations.append(catchment)

    # step 2: convert to subcatchments
    catchments = delineations_to_subcatchments(delineations)

    return catchments
