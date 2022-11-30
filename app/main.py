import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.lib.delineation import Delineator
from app.model import Outlets
from app.helpers import EarthEngineMap

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title='flowdirections',
              description='A catchment delineation API based on HydroSHEDS + Pysheds',
              version='0.0.1')

deployment_mode = os.environ.get('DEPLOYMENT_MODE', 'development')
print(deployment_mode)
if deployment_mode == 'production':
    allowed_origins = ['https://flowdirections.io', 'https://www.flowdirections.io', 'https://api.flowdirections.io']
    if not allowed_origins:
        raise Exception('Environment variable ALLOWED_ORIGIN not specified')
else:
    allowed_origins = ['http://localhost:3000']

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=['POST', 'GET'],
    allow_headers=["*"],
)

EEMap = EarthEngineMap()

# _regions = ['eu', 'as', 'af', 'na', 'sa', 'au']
_regions = ['na']
_resolutions = [15, 30]

delineator = Delineator(_regions, _resolutions)


@app.get("/")
async def root():
    return "Hello, Hydrologist!"


@app.get('/ee_tile')
async def get_ee_tile(dataset: str, threshold: int):
    try:
        tile_url = EEMap.get_earth_engine_map_tile_url(dataset, threshold)
        return tile_url
    except:
        return 'Earth Engine not initialized'


@app.get('/catchment')
async def delineate(lat: float = None, lon: float = None, res: int = 30):
    geojson = delineator.delineate_point(lon, lat, res=res)
    return geojson


@app.post('/delineate_catchment')
async def delineate(lat: float = None, lon: float = None, res: int = 30):
    geojson = delineator.delineate_point(lon, lat, res=res)
    return geojson


@app.post('/delineate_catchments')
async def delineate(res: int = 30, outlets: Outlets = None):
    features = outlets.features
    geojson = delineator.delineate_points(features, res=res, parallel=True)
    return geojson
