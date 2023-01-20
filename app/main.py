import os
import json
import logging

from fastapi import FastAPI, Security, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader, APIKeyQuery

from app.setup import initialize
from app.model import Outlets
from app.store import redis
from app.helpers import EarthEngineMap
from app.tasks import celery, delineate_point, delineate_points
from app.lib.utils import make_catchment_key

from celery.result import AsyncResult

from dotenv import load_dotenv

load_dotenv()

regions = ['eu', 'as', 'af', 'na', 'sa', 'au']
resolutions = [15, 30]
initialize(regions, resolutions)

API_KEYS = [os.environ['API_KEY']]

api_key_header = APIKeyHeader(name='x-api-key')
api_key_query = APIKeyQuery(name="api-key", auto_error=False)


def get_api_key(
        api_key_query: str = Security(api_key_query),
        api_key_header: str = Security(api_key_header),
):
    """Retrieve & validate an API key from the query parameters or HTTP header"""
    # If the API Key is present as a query param & is valid, return it
    if api_key_query in API_KEYS:
        return api_key_query

    # If the API Key is present in the header of the request & is valid, return it
    if api_key_header in API_KEYS:
        return api_key_header

    # Otherwise, we can raise a 401
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )


app = FastAPI(title='flowdirections.io',
              description='A catchment delineation API using pysheds + HydroSHEDS',
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


def get_celery_worker_status():
    i = celery.control.inspect()
    return i.ping()


def get_stored_result(key):
    if redis:
        stored_value = redis.get(key)
        if stored_value and stored_value != b'null':
            return stored_value.decode()


def get_result(key, fn, *args, **kwargs):
    result = get_stored_result(key)
    if result:
        return json.loads(result)
    else:
        if get_celery_worker_status():
            result = fn.delay(*args, **kwargs).get()
        else:
            result = fn(*args, **kwargs)
        redis.set(key, json.dumps(result))
        return result


@app.get("/")
async def root():
    return "Hello, Hydrologist!"


@app.get('/ee_tile')
async def get_ee_tile(dataset: str, threshold: int, api_key: str = Security(get_api_key)):
    try:
        tile_url = app.ee.get_earth_engine_map_tile_url(dataset, threshold)
        return tile_url
    except:
        return 'Earth Engine not initialized'


@app.get('/tiles/streamlines')
async def get_streamlines_raster(resolution: int, threshold: int, api_key: str = Security(get_api_key)):
    try:
        tile_url = app.ee.get_streamlines_raster(resolution, threshold)
        return tile_url
    except:
        return 'Earth Engine not initialized'


@app.get('/catchment')
async def delineate(lat: float = None, lon: float = None, res: int = 30, remove_sinks: bool = False,
                    api_key: str = Security(get_api_key)):
    try:
        key = make_catchment_key(lat, lon, res, 'd8', remove_sinks)
        result = get_result(key, delineate_point, lon, lat, res=res, remove_sinks=remove_sinks)
        return result
    except:
        return 'Uh-oh!'


@app.post('/delineate_catchment')
async def delineate_catchment(lat: float = None, lon: float = None, res: int = 30, remove_sinks: bool = False,
                              api_key: str = Security(get_api_key)):
    try:
        geojson = delineate_point(lon, lat, res=res, remove_sinks=remove_sinks)
        return geojson
    except:
        return 'Uh-oh!'


@app.post('/delineate_catchments')
async def delineate_catchments(res: int = 30, outlets: Outlets = None, api_key: str = Security(get_api_key)):
    try:
        features = outlets.features
        geojson = delineate_points(features, res=res, parallel=False)
        return geojson
    except:
        return 'Uh-oh!'
