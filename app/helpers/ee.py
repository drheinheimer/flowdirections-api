import os
import json

import ee


class EarthEngineMap(object):
    ee = None

    def __init__(self):
        # ee.Authenticate()

        service_account = os.environ.get('EE_CLIENT_EMAIL')
        ee_key_data = {
            "type": "service_account",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        }
        for var in os.environ:
            if var[:3] == 'EE_':
                ee_key_data[var[3:].lower()] = os.environ[var]

        try:
            credentials = ee.ServiceAccountCredentials(service_account, key_data=json.dumps(ee_key_data))
            ee.Initialize(credentials)
            self.ee = ee
        except:
            pass

    def get_streamlines_raster(self, resolution, threshold, showsinks=True, palette='0000FF', sink_color='black'):
        facc_dataset = f'WWF/HydroSHEDS/{resolution}ACC'

        facc_image = self.ee.Image(facc_dataset)
        max_threshold = pow(5, (100 - threshold) / 100 * 7.5)
        streams = facc_image.updateMask(facc_image.gte(max_threshold))
        streams_visualized = streams.visualize(palette=palette, min=0, max=max_threshold)

        if showsinks:
            fdir_dataset = f'WWF/HydroSHEDS/{resolution}DIR'
            fdir_image = self.ee.Image(fdir_dataset)
            sinks = fdir_image.updateMask(fdir_image.eq(255))
            sinks_visualized = sinks.visualize(palette=sink_color)

            mosaic = ee.ImageCollection([streams_visualized, sinks_visualized]).mosaic()
            map_id = mosaic.getMapId()
        else:
            map_id = streams_visualized.getMapId()

        return map_id['tile_fetcher'].url_format

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
