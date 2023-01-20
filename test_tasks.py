import datetime as dt
import json

from app.setup import initialize
from app.tasks import delineate_point, delineate_from_feature, delineate_from_features

from dotenv import load_dotenv

load_dotenv()


class Test(object):

    def __init__(self, regions):
        print('Setting up test environment')
        initialize(regions, [30])

    def test_delineate_point(self, lon=None, lat=None, outlet_name=None, res=30):

        if lon and lat:
            print(f'testing lat={lat}, lon={lon}')

        elif outlet_name:
            with open(f'./examples/{outlet_name}.json') as f:
                outlet = json.load(f)

        else:
            raise Exception('Coordinates or outlet name must be provided')

        start_time = dt.datetime.now()
        result = delineate_point(outlet, res=30)
        elapsed_time = dt.datetime.now() - start_time
        print(f'elapsed time: {elapsed_time}')

        assert ('type' in result and result['type'] == 'FeatureCollection')

    def test_delinate_points(self, res):
        with open('./examples/outlets.json') as f:
            outlets = json.load(f)
        features = outlets['features']
        result = delineate_from_features(features, res=res)

        assert ('type' in result and result['type'] == 'FeatureCollection')


if __name__ == '__main__':
    print('Initializing test')
    test = Test(['na'])

    res = 30

    # print('Test delineate Delaware River')
    # test.test_delineate_point(outlet_name='colorado')

    # print('Test delineate points')
    test.test_delinate_points(res=res)

    print('Test passed!')
