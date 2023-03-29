import os
import json

from celery import Celery

from app.lib.delineation import delineate_point as _delineate_point, delineations_to_subcatchments

from app.lib.utils import make_catchment_key
from app.store import get_stored_result, store_result

import dotenv

dotenv.load_dotenv()

redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_password = os.environ.get('REDIS_PASSWORD')
if redis_password:
    redis_host = f':{redis_password}@{redis_host}'
redis_url = f'redis://{redis_host}'
celery = Celery(
    __name__,
    broker=os.environ.get("CELERY_BROKER_URL", redis_url),
    backend=os.environ.get("CELERY_RESULT_BACKEND", redis_url),
    expires=60  # results expire after 1 minute
)


@celery.task(name='delineate_point')
def delineate_point(lon, lat, res=30, remove_sinks=False):
    return _delineate_point(lon, lat, res=res, remove_sinks=remove_sinks)


@celery.task(name='delineate_from_feature')
def delineate_from_feature(feature, res, remove_sinks):
    lon, lat = feature['geometry']['coordinates']

    key = make_catchment_key(lat, lon, res, remove_sinks=remove_sinks)
    result = get_stored_result(key)
    if result:
        delineation = json.loads(result)
    else:
        delineation = _delineate_point(lon, lat, res=res, remove_sinks=remove_sinks)

    store_result(key, json.dumps(delineation))

    return delineation


@celery.task(name='delineate_from_features')
def delineate_from_features(features, res=30, remove_sinks=False):
    n = len(features)
    resolutions = [res] * n
    remove_sinkss = [remove_sinks] * n

    delineations = ~delineate_from_feature.starmap(zip(features, resolutions, remove_sinkss))

    catchments = delineations_to_subcatchments(delineations)

    return catchments
