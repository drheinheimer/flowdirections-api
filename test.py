import datetime as dt
from app.lib.delineation import Delineator
import json

from dotenv import load_dotenv

load_dotenv()


class Test(object):

    def __init__(self, regions):
        print('Setting up test environment')
        self.delineator = Delineator(regions, [30])

    def delineate_point(self, lon=None, lat=None, outlet_name=None, res=30):

        if lon and lat:
            print(f'testing lat={lat}, lon={lon}')

        elif outlet_name:
            with open(f'./examples/{outlet_name}.json') as f:
                outlet = json.load(f)
                lon, lat = outlet['geometry']['coordinates']
        else:
            raise Exception('Coordinates or outlet name must be provided')

        start_time = dt.datetime.now()
        result = self.delineator.delineate_point(lon, lat, res=30)
        elapsed_time = dt.datetime.now() - start_time
        print(f'elapsed time: {elapsed_time}')

        assert ('type' in result and result['type'] == 'FeatureCollection')

    def delinate_points(self):
        with open('./examples/outlets.json') as f:
            outlets = json.load(f)
        features = outlets['features']
        result = self.delineator.delineate_points(features, parallel=False)

        assert ('type' in result and result['type'] == 'FeatureCollection')


if __name__ == '__main__':
    print('Initializing test')
    test = Test(['eu'])

    print('Test delineate Weser River, Europe')
    test.delineate_point(outlet_name='weser')

    # print('Test delineate points')
    # test.delinate_points()

    print('Test passed!')
