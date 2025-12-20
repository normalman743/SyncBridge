from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# unified response wrapper
class Resp(BaseModel):
    status: str
    message: str
    data: Optional[dict] = None

# Auth
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str]
    license_key: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class AuthMeOut(BaseModel):
    user_id: int
    email: EmailStr
    display_name: Optional[str]
    role: Optional[str]

# Form
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

# Function / NonFunction
class FunctionIn(BaseModel):
    form_id: int
    name: str
    choice: str
    description: Optional[str]
    status: Optional[str] = "available"
    is_changed: Optional[bool] = False

class FunctionOut(BaseModel):
    id: int
    form_id: int
    name: str
    choice: str
    description: Optional[str]
    status: str
    is_changed: bool

# Message
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

# File upload response is simple id
class FileOut(BaseModel):
    id: int
    file_name: str
    file_size: int
    storage_path: str
