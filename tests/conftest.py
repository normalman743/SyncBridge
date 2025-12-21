import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure required env vars exist before importing app modules (override to avoid stale values)
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUDIT_ENABLED"] = "false"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from app.api.v1.deps import get_db
from app.main import app
from app.models import License, User
from app.models.base import Base
from app.utils import get_password_hash

# In-memory SQLite shared across threads for tests
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Disable background reminder loops for tests
app.router.on_startup.clear()
app.router.on_shutdown.clear()
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Recreate all tables before each test for isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def create_user(
    db,
    email="user@example.com",
    password="StrongPass123",
    role=None,
    is_active=1,
    display_name="User",
):
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        display_name=display_name,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_license(
    db,
    key="TEST-LICENSE",
    role="client",
    status="unused",
    user=None,
    expires_at=None,
    activate_user=True,
):
    lic = License(
        license_key=key,
        role=role,
        status=status,
        user_id=user.id if user else None,
        activated_at=datetime.utcnow() if status != "unused" else None,
        expires_at=expires_at,
    )
    if user and status == "active":
        user.role = role
        if activate_user:
            user.is_active = 1
        user.updated_at = datetime.utcnow()
        db.add(user)
    db.add(lic)
    db.commit()
    db.refresh(lic)
    if user:
        db.refresh(user)
    return lic
