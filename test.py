from lib.delineation import delineate_point
import json

if __name__ == '__main__':

    lat, lon = 32.49434, -114.81376  # Colorado River at San Luis Rio Colorado
    # lat, lon = 32.52726, -114.79777  # Gila River?

    print(f'lat={lat}, lon={lon}')

    catchment = delineate_point(lat, lon)

    catchment_str = json.dumps(catchment, indent=4)
    with open('test.json', 'w') as f:
        f.write(catchment_str)

    print(catchment_str)
