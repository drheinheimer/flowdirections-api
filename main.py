from fastapi import FastAPI
from lib.delineation import delineate_point

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


@app.get('/delineate')
async def delineate(lat: float = 32.52726, lon: float = -114.79777):
    geojson = delineate_point(lat, lon)
    return geojson
