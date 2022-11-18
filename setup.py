from os import path, makedirs
from pathlib import Path
from io import BytesIO
import zipfile
import json

import requests

import rasterio
import rasterio.features
import rasterio.warp

filename_tpl = 'hyd_{region}_{data}_{res}s.{ext}'
url_tpl = 'https://data.hydrosheds.org/file/hydrosheds-v1-{data}/{filename}'


def download_extract_hydrosheds(region, data, res, dest='./data'):
    fdir_filename = filename_tpl.format(region=region, data=data, res=res, ext='zip')
    fdir_url = url_tpl.format(data=data, filename=fdir_filename)

    tif_name = filename_tpl.format(region=region, data=data, res=res, ext='tif')
    out_path = Path(dest, tif_name)

    if not path.exists(out_path):
        print(f'Processing {fdir_url}')
        req = requests.get(fdir_url)
        zf = zipfile.ZipFile(BytesIO(req.content))
        zf.extract(tif_name, dest)

    return out_path


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
    if not path.exists(dest):
        makedirs(dest)

    # extract direction grids
    for res in [15, 30]:
        download_extract_hydrosheds(region, 'dir', res)
        download_extract_hydrosheds(region, 'acc', res)

    # extract masks
    download_extract_hydrosheds(region, 'msk', 30, dest=dest)
    tif_name = filename_tpl.format(region=region, data='msk', res=30, ext='tif')
    mask_path = Path(dest, tif_name)
    out_path = Path(dest, tif_name.replace('.tif', '.json'))

    if not path.exists(out_path):
        vector = mask_raster_to_vector(mask_path)
        with open(out_path, 'w') as f:
            f.write(json.dumps(vector))

    return


def initialize():
    print('Initializing data...')
    regions = ['eu', 'as', 'af', 'na', 'sa', 'au']
    for region in regions:
        process_region(region, './data')


if __name__ == '__main__':
    initialize()
