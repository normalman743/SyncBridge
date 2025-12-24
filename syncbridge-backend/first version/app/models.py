from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.types import LargeBinary
from .database import Base
import enum

class RoleEnum(str, enum.Enum):
    client = "client"
    developer = "developer"
    admin = "admin"

class LicenseStatus(str, enum.Enum):
    unused = "unused"
    active = "active"
    expired = "expired"
    revoked = "revoked"

class FormType(str, enum.Enum):
    mainform = "mainform"
    subform = "subform"

class FormStatus(str, enum.Enum):
    preview = "preview"
    available = "available"
    processing = "processing"
    rewrite = "rewrite"
    end = "end"
    error = "error"

class ChoiceEnum(str, enum.Enum):
    lightweight = "lightweight"
    commercial = "commercial"
    enterprise = "enterprise"

class BlockStatus(str, enum.Enum):
    urgent = "urgent"
    normal = "normal"

class BlockType(str, enum.Enum):
    general = "general"
    function = "function"
    nonfunction = "nonfunction"

# users
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(128), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    display_name = Column(String(32))
    role = Column(Enum(RoleEnum), nullable=True)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# licenses
class License(Base):
    __tablename__ = "licenses"
    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String(128), unique=True, nullable=False)
    role = Column(Enum(RoleEnum))
    status = Column(Enum(LicenseStatus), default=LicenseStatus.unused)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

# forms (main / sub)
class Form(Base):
    __tablename__ = "forms"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(FormType), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)   # client owner
    developer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(128))
    message = Column(Text)
    budget = Column(String(64))
    expected_time = Column(String(64))
    status = Column(Enum(FormStatus), default=FormStatus.preview)
    subform_id = Column(Integer, ForeignKey("forms.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# functions
class Function(Base):
    __tablename__ = "functions"
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    name = Column(String(128))
    choice = Column(Enum(ChoiceEnum))
    description = Column(Text)
    status = Column(Enum(FormStatus), default=FormStatus.preview)
    is_changed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# nonfunctions
class NonFunction(Base):
    __tablename__ = "nonfunctions"
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    name = Column(String(128))
    level = Column(Enum(ChoiceEnum))
    description = Column(Text)
    status = Column(Enum(FormStatus), default=FormStatus.preview)
    is_changed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# blocks (internal)
class Block(Base):
    __tablename__ = "blocks"
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    status = Column(Enum(BlockStatus), default=BlockStatus.normal)
    type = Column(Enum(BlockType), default=BlockType.general)
    target_id = Column(Integer, nullable=True)  # function_id or nonfunction_id
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# messages
class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    block_id = Column(Integer, ForeignKey("blocks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text_content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# files
class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    file_name = Column(String(128))
    file_type = Column(String(32))
    file_size = Column(Integer)
    storage_path = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
