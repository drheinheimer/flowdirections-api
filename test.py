from lib import delineation as d

if __name__ == '__main__':
    lat = 32.52726
    lon = -114.79777

    catchment = d.delineate_point(x=lon, y=lat)

    print(catchment)
