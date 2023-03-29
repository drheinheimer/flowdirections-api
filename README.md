# Deployment

For deployment with SSL, see: https://lcalcagni.medium.com/deploy-your-fastapi-to-aws-ec2-using-nginx-aa8aa0d85ec7
The above should apply to servers generally, not just EC2 machines.

# Hardware requirements

The minimum hardware requirements have not yet been determined. However, during testing 2GB of memory on a DigitalOcean droplet with Ubuntu 22.04 LTS resulted in the application silently failing when copying a large numpy array. Increasing the memory to 4GB resolved the problem.

Additional analysis is needed to determine exact hardware requirements.

# Environment variables

* `DEPLOYMENT_MODE`: `development` or `production` (default: `development`).
* `DATA_HTTP_URI`: s3-compatible data store.
* `DATA_DIR`: local data storage directory (e.g., `./instance/data`).
* `REDIS_HOST`: Redis IP address for memcache and task queue.
* `REDIS_PASSWORD`: Redis password.
* `ALLOWED_ORIGIN`: Origin from which requests are allowed.
* `API_KEY`: Key for accessing the API. This should be passed in via the client in an `x-api-key` header.

The following environment variables are for using Google Earth Engine to display the HydroSHEDS flow accumulation grid.
They are found in the EE credentials json file associated with the EE account. Adding these as variables obviates the
need to store/manage the json credentials.
* `EE_PROJECT_ID`
* `EE_PRIVATE_KEY_ID`
* `EE_PRIVATE_KEY`
* `EE_CLIENT_EMAIL`
* `EE_CLIENT_ID`
* `EE_CLIENT_X509_CERT_URL`

# Task queue

Celery is used to manage tasks. `tasks.py` contains all the relevant Celery tasks, and can be run as follows:
* Windows: `celery -A app.tasks worker -l info -P eventlet`
* Linux: `celery -A app.tasks worker -l info -P eventlet --concurrency=10`