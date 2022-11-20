import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import ee

from lib.delineation import delineate_point, delineate_points
from app.model import Outlets

from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title='RapidSHEDS',
              description='A catchment delineation API based on HydroSHEDS + Pysheds',
              version='0.0.1')

origins = [
    "https://rapidsheds.io",
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class EarthEngineMap(object):
    ee = None

    def __init__(self):
        # ee.Authenticate()

        service_account = os.environ.get('EE_SERVICE_ACCOUNT')
        try:
            credentials = ee.ServiceAccountCredentials(service_account, 'ee-credentials.json')
            ee.Initialize(credentials)
            self.ee = ee
        except:
            pass

    def get_earth_engine_map_tile_url(self, dataset, threshold, palette='0000FF'):
        if not self.ee:
            raise Exception('Earth Engine not initialized')
        ee_image = self.ee.Image(dataset)
        map_id = None
        if dataset in ['WWF/HydroSHEDS/15ACC', 'WWF/HydroSHEDS/30ACC']:
            # real_threshold = pow(10, (100 - threshold) / 100 * 7.5)
            max_threshold = pow(5, (100 - threshold) / 100 * 7.5)
            # max_threshold = (100 - threshold) / 100 * 7.5
            masked = ee_image.updateMask(ee_image.gte(max_threshold))

            map_id = masked.getMapId({'palette': palette, 'min': 0, 'max': max_threshold})

        # elif dataset == 'CGIAR/SRTM90_V4':
        #     range = request.args.getlist('range[]', type=int)
        #     min = range[0]
        #     max = range[1]
        #     map_id = ee_image.getMapId({'min': min, 'max': max})

        tile_url = map_id['tile_fetcher'].url_format
        return tile_url


EEMap = EarthEngineMap()


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
    geojson = delineate_point(lon, lat, res=res)
    return geojson


@app.post('/delineate_catchment')
async def delineate(lat: float = None, lon: float = None, res: int = 30):
    geojson = delineate_point(lon, lat, res=res)
    return geojson


@app.post('/delineate_catchments')
async def delineate(res: int = 30, outlets: Outlets = None):
    features = outlets.features
    geojson = delineate_points(features, res=res)
    return geojson
