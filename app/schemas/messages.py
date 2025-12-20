from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class MessageIn(BaseModel):
    form_id: int
    function_id: Optional[int] = None
    nonfunction_id: Optional[int] = None
    text_content: str


class MessageOut(BaseModel):
    id: int
    block_id: int
    user_id: int
    text_content: str
    created_at: datetime


class MessageUpdate(BaseModel):
    text_content: str | None = None

    class Config:
        extra = "forbid"
