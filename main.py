import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import ee

from lib.delineation import delineate_point, delineate_points

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

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


class Outlets(BaseModel):
    type: str
    features: list


class EarthEngineMap(object):

    def __init__(self):
        # ee.Authenticate()
        service_account = os.environ['EE_SERVICE_ACCOUNT']
        credentials_path = os.environ['EE_CREDENTIALS_PATH']
        credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
        ee.Initialize(credentials)
        self.ee = ee

    def get_earth_engine_map_tile_url(self, dataset, threshold, palette='0000FF'):
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
    return {"message": "Hello World!"}


@app.get('/ee_tile')
async def get_ee_tile(dataset: str, threshold: int):
    tile_url = EEMap.get_earth_engine_map_tile_url(dataset, threshold)
    return tile_url


@app.get('/delineate')
async def delineate(lat: float = None, lon: float = None, res: int = 30):
    geojson = delineate_point(lon, lat, res=res)
    return geojson


@app.post('/delineate')
async def delineate(res: int = 30, outlets: Outlets = None):
    features = outlets.features
    geojson = delineate_points(features, res=res)
    return geojson
