import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.setup import initialize
from app.model import Outlets
from app.helpers import EarthEngineMap
from app.lib.delineation import delineate_point, delineate_points

import logging

from dotenv import load_dotenv

load_dotenv()

regions = ['eu', 'as', 'af', 'na', 'sa', 'au']
resolutions = [15, 30]
initialize(regions, resolutions)

app = FastAPI(title='flowdirections.io',
              description='A catchment delineation API based on HydroSHEDS + Pysheds',
              version='0.0.1')

deployment_mode = os.environ.get('DEPLOYMENT_MODE', 'development')
logging.info(f'Deployment mode: {deployment_mode}')
if deployment_mode == 'production':
    allowed_origin = os.environ.get('ALLOWED_ORIGIN')
    if not allowed_origin:
        raise Exception('Environment variable ALLOWED_ORIGIN not specified')
else:
    allowed_origin = 'http://localhost:3000'

app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.ee = EarthEngineMap()


@app.get("/")
async def root():
    return "Hello, Hydrologist!"


@app.get('/ee_tile')
async def get_ee_tile(dataset: str, threshold: int):
    try:
        tile_url = app.ee.get_earth_engine_map_tile_url(dataset, threshold)
        return tile_url
    except:
        return 'Earth Engine not initialized'


@app.get('/streamlines_raster')
async def get_streamlines_raster(resolution: int, threshold: int):
    try:
        tile_url = app.ee.get_streamlines_raster(resolution, threshold)
        return tile_url
    except:
        return 'Earth Engine not initialized'


@app.get('/catchment')
async def delineate(lat: float = None, lon: float = None, res: int = 30, remove_sinks: bool = False):
    geojson = delineate_point(lon, lat, res=res, remove_sinks=remove_sinks)
    return geojson


@app.post('/delineate_catchment')
async def delineate_catchment(lat: float = None, lon: float = None, res: int = 30):
    try:
        geojson = delineate_point(lon, lat, res=res)
        return geojson
    except:
        return 'Uh-oh!'


@app.post('/delineate_catchments')
async def delineate_catchments(res: int = 30, outlets: Outlets = None):
    features = outlets.features
    geojson = delineate_points(features, res=res, parallel=False)
    return geojson
