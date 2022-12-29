import os
import json

from celery import Celery

from app.lib.delineation import delineate_point as _delineate_point
from app.lib.utils import snap_to_center
from app.store import redis

import dotenv

dotenv.load_dotenv()

redis_url = os.environ.get('REDIS_URL', 'redis://localhost')
celery = Celery(
    __name__,
    broker=os.environ.get("CELERY_BROKER_URL", redis_url),
    backend=os.environ.get("CELERY_RESULT_BACKEND", redis_url),
    expires=60  # results expire after 1 minute
)


def get_stored_result(key):
    if redis:
        stored_value = redis.get(key)
        if stored_value and stored_value != b'null':
            return stored_value.decode()


@celery.task(name='delineate_point')
def delineate_point(lon, lat, res=30, remove_sinks=False, **kwargs):
    _lon = snap_to_center(lon, res)
    _lat = snap_to_center(lat, res)
    memory_key = f'{_lon}:{_lat}:{res}:{remove_sinks}'

    result = get_stored_result(memory_key)
    if result:
        return json.loads(result)

    else:
        result = _delineate_point(lon, lat, res=res, remove_sinks=remove_sinks)
        redis.set(memory_key, json.dumps(result))
        return result
