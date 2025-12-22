from typing import Optional
from pydantic import BaseModel


class Resp(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None
