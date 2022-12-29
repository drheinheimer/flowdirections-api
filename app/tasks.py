import os

from celery import Celery

from app.lib.delineation import delineate_point as _delineate_point

import dotenv

dotenv.load_dotenv()

redis_url = os.environ.get('REDIS_URL', 'redis://localhost')
celery = Celery(
    __name__,
    broker=os.environ.get("CELERY_BROKER_URL", redis_url),
    backend=os.environ.get("CELERY_RESULT_BACKEND", redis_url),
    expires=60  # results expire after 1 minute
)


@celery.task(name='delineate_point')
def delineate_point(lon, lat, res=30, remove_sinks=False):
    return _delineate_point(lon, lat, res=res, remove_sinks=remove_sinks)
