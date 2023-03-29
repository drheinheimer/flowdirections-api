import os
import logging

from redis import Redis

import dotenv

dotenv.load_dotenv()

redis_port = os.environ.get('REDIS_PORT', 6379)
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_password = os.environ.get('REDIS_PASSWORD')
try:
    redis = Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password
    )
    logging.info(f'Starting with REDIS on server {redis_host}')

except:
    redis = None
    logging.warning('Starting without REDIS')


def get_stored_result(key):
    if redis:
        stored_value = redis.get(key)
        if stored_value and stored_value != b'null':
            return stored_value.decode()


def store_result(key, value):
    redis.set(key, value)
