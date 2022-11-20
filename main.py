import uvicorn
from app.api import app
from setup import initialize

if __name__ == "__main__":
    initialize()
    uvicorn.run("app.api:app", host="127.0.0.1", port=8000, reload=True)
