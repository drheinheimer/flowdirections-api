import datetime as dt
from lib.delineation import delineate_point, delineate_points
import json


def test_delineate_point(lon, lat, res):
    print(f'testing lat={lat}, lon={lon}')

    start_time = dt.datetime.now()
    catchment = delineate_point(lon, lat, res=30)

    catchment_str = json.dumps(catchment, indent=4)
    # with open('test.json', 'w') as f:
    #     f.write(catchment_str)
    elapsed_time = dt.datetime.now() - start_time
    print(f'elapsed time: {elapsed_time}')


if __name__ == '__main__':
    # delineate a single point
    # Sacramento River at Isleton
    # lat, lon = 38.171, -121.653
    # test_delineate_point(lon, lat, 30)

    # delineate multiple points
    with open('./examples/outlets.json') as f:
        outlets = json.load(f)
    features = outlets['features']
    result = delineate_points(features)

    with open('catchments.json', 'w') as f:
        f.write(json.dumps(result, indent=2))
    print('done!')
