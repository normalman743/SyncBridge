from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class FormCreate(BaseModel):
    title: str
    message: Optional[str]
    budget: Optional[str]
    expected_time: Optional[str]


class FormOut(BaseModel):
    id: int
    type: str
    title: Optional[str]
    message: Optional[str]
    budget: Optional[str]
    expected_time: Optional[str]
    status: Optional[str]
    user_id: int
    developer_id: Optional[int]
    subform_id: Optional[int]
    created_at: datetime
