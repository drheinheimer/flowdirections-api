import datetime as dt
from app.lib.delineation import Delineator
import json

from dotenv import load_dotenv

load_dotenv()


class Test(object):

    def __init__(self):
        print('Setting up test environment')
        self.delineator = Delineator(['na'], [30])

    def delineate_point(self, lon, lat, res=30):
        print(f'testing lat={lat}, lon={lon}')

        start_time = dt.datetime.now()
        catchment = self.delineator.delineate_point(lon, lat, res=30)

        # catchment_str = json.dumps(catchment, indent=4)
        # with open('test.json', 'w') as f:
        #     f.write(catchment_str)
        elapsed_time = dt.datetime.now() - start_time
        print(f'elapsed time: {elapsed_time}')

    def delinate_points(self):
        with open('./examples/outlets.json') as f:
            outlets = json.load(f)
        features = outlets['features']
        result = self.delineator.delineate_points(features, parallel=False)

        assert('type' in result and result['type'] == 'FeatureCollection')


if __name__ == '__main__':

    print('Initializing test')
    test = Test()

    print('Test delineate points')
    test.delinate_points()

    print('Test passed!')
