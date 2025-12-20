from datetime import datetime
from pydantic import BaseModel


class FormCreate(BaseModel):
    title: str
    message: str
    budget: str
    expected_time: str


class FormOut(BaseModel):
    id: int
    type: str
    title: str | None
    message: str | None
    budget: str | None
    expected_time: str | None
    status: str | None
    user_id: int
    developer_id: int | None
    subform_id: int | None
    created_at: datetime
