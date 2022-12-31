from math import floor


def snap_to_center(n, res):
    r = res / 60 / 60
    N = floor(n / r) * r + r / 2
    return round(N * 10000) / 10000


def make_catchment_key(lon, lat, res, routing, remove_sinks):
    lon = snap_to_center(lon, res)
    lat = snap_to_center(lat, res)
    return f'{lon}:{lat}:{routing}:{res}:{remove_sinks}'
