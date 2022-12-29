from math import floor


def snap_to_center(n, res):
    r = res / 60 / 60
    N = floor(n / r) * r + r / 2
    return round(N * 10000) / 10000
