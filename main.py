import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import ee

from lib.delineation import delineate_point

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
        if dataset == 'WWF/HydroSHEDS/15ACC':
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
async def delineate(lat: float = 0, lon: float = 0, res: int = 30):
    geojson = delineate_point(lat, lon, res=res)
    return geojson
