from pydantic import BaseModel


class FileOut(BaseModel):
    id: int
    file_name: str
    file_size: int
    storage_path: str
