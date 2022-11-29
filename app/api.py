import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lib.delineation import Delineator
from app.model import Outlets
from app.helpers import EarthEngineMap

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title='RapidSHEDS',
              description='A catchment delineation API based on HydroSHEDS + Pysheds',
              version='0.0.1')

if os.environ.get('DEPLOYMENT_MODE') == 'production':
    # TODO: update to allow get requests from anywhere
    origins = [os.environ.get('ALLOWED_ORIGIN')]
else:
    origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EEMap = EarthEngineMap()

# _regions = ['eu', 'as', 'af', 'na', 'sa', 'au']
_regions = ['na']
_resolutions = [15, 30]

delineator = Delineator(_regions, _resolutions)


@app.get("/")
async def root():
    return "<p>Hello, Hydrologist!</p>"


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
