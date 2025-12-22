from pydantic import BaseModel


class FunctionIn(BaseModel):
    form_id: int
    name: str
    choice: str
    description: str
    status: str | None = "available"
    is_changed: bool | None = False


class FunctionOut(BaseModel):
    id: int
    form_id: int
    name: str
    choice: str
    description: str | None
    status: str
    is_changed: bool


class FunctionUpdate(BaseModel):
    name: str | None = None
    choice: str | None = None
    description: str | None = None
    status: str | None = None
    is_changed: bool | None = None

    class Config:
        extra = "forbid"
