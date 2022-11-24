import uvicorn
from app.api import app
# from app.setup import initialize

if __name__ == "__main__":
    # initialize()
    uvicorn.run("app.api:app", host="0.0.0.0", port=8080, reload=True)
