from pydantic import BaseModel


class Outlets(BaseModel):
    type: str
    features: list
