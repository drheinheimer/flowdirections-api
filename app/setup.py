import os
from pathlib import Path
import json
import shutil

import requests

import rasterio
import rasterio.features
import rasterio.warp

from loguru import logger

filename_tpl = 'hyd_{region}_{data}_{res}s.{ext}'


def download_extract_hydrosheds(region, data, res, dest='./data'):
    src_data_url = os.environ['DATA_HTTP_URI']
    tif_name = filename_tpl.format(region=region, data=data, res=res, ext='tif')
    src_url = f'{src_data_url}/{tif_name}'
    dst_path = Path(dest, tif_name)

    if not os.path.exists(dst_path):
        print(f'Processing {tif_name}')

        req = requests.get(src_url)

        with open(dst_path, 'wb') as f:
            f.write(req.content)

        total, used, free = shutil.disk_usage("/")

        print("Total storage: %d GiB" % (total // (2 ** 30)))
        print("Used storage: %d GiB" % (used // (2 ** 30)))
        print("Free storage: %d GiB" % (free // (2 ** 30)))


    return dst_path


def mask_raster_to_vector(input_path):
    print(f'Extracting region mask: {input_path}')

    features = []

    with rasterio.open(input_path) as dataset:
        # Read the dataset's valid data mask as a ndarray.
        mask = dataset.dataset_mask()

        # Extract feature shapes and values from the array.
        for geom, val in rasterio.features.shapes(mask, transform=dataset.transform):
            # Transform shapes from the dataset's own coordinate
            # reference system to CRS84 (EPSG:4326).
            geom = rasterio.warp.transform_geom(dataset.crs, 'EPSG:4326', geom, precision=6)

            feature = {'type': 'Polygon', 'geometry': geom, 'properties': {'val': val}}
            features.append(feature)

    gj = {
        'type': 'FeatureCollection',
        'features': features
    }

    return gj


def process_region(region, dest):
    if not os.path.exists(dest):
        os.makedirs(dest)

    # extract direction grids
    for res in [15, 30]:
        download_extract_hydrosheds(region, 'dir', res, dest=dest)
        download_extract_hydrosheds(region, 'acc', res, dest=dest)

    # extract masks
    download_extract_hydrosheds(region, 'msk', 30, dest=dest)
    tif_name = filename_tpl.format(region=region, data='msk', res=30, ext='tif')
    mask_path = Path(dest, tif_name)

    mask_name = tif_name.replace('.tif', '.json')
    dst_path = Path(dest, mask_name)

    if not os.path.exists(dst_path):

        src_data_url = os.environ['DATA_HTTP_URI']
        src_url = f'{src_data_url}/{mask_name}'
        req = requests.get(src_url)
        if req.ok:
            vector = req.content.decode()
        else:
            vector = mask_raster_to_vector(mask_path)

        with open(dst_path, 'w') as f:
            f.write(json.dumps(vector))

    return


def initialize():
    logger.info('Initializing grid data...')
    regions = ['eu', 'as', 'af', 'na', 'sa', 'au']
    dest = os.environ.get('DATA_DIR', './instance/data')
    for region in regions:
        process_region(region, dest)


if __name__ == '__main__':
    initialize()
