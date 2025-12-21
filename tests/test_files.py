import os
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app import models, crud

# =========================
# Setup Test DB
# =========================
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# =========================
# Fixtures
# =========================
@pytest.fixture
def test_user(db=TestingSessionLocal()):
    user = models.User(username="testuser", email="test@example.com", hashed_password="fakehash")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_message(test_user, db=TestingSessionLocal()):
    msg = models.Message(content="Hello", user_id=test_user.id)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


# =========================
# Test File Upload
# =========================
def test_upload_file(test_user, test_message):
    file_content = b"hello world"
    file = io.BytesIO(file_content)
    file.name = "hello.txt"

    response = client.post(
        f"/file?message_id={test_message.id}",
        files={"file": ("hello.txt", file, "text/plain")}
    )

    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data["data"]


# =========================
# Test File Too Large
# =========================
def test_upload_file_too_large(test_user, test_message, monkeypatch):
    monkeypatch.setenv("MAX_FILE_SIZE", "5")  # 5 bytes limit
    file_content = b"exceeding"
    file = io.BytesIO(file_content)
    file.name = "bigfile.txt"

    response = client.post(
        f"/file?message_id={test_message.id}",
        files={"file": ("bigfile.txt", file, "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


# =========================
# Test Get File Metadata
# =========================
def test_get_file_metadata(test_user, test_message, db=TestingSessionLocal()):
    # create file record manually
    path = os.path.join(os.path.dirname(__file__), "temp.txt")
    with open(path, "wb") as f:
        f.write(b"abc")
    rec = crud.create_file_record(db, test_message.id, "temp.txt", "text/plain", 3, path)

    response = client.get(f"/file/{rec.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["file_name"] == "temp.txt"


# =========================
# Test Delete File
# =========================
def test_delete_file(test_user, test_message, db=TestingSessionLocal()):
    path = os.path.join(os.path.dirname(__file__), "delete_me.txt")
    with open(path, "wb") as f:
        f.write(b"delete me")
    rec = crud.create_file_record(db, test_message.id, "delete_me.txt", "text/plain", 9, path)

    response = client.delete(f"/file/{rec.id}")
    assert response.status_code == 200
    assert response.json()["message"] == "File deleted"
    # confirm file deleted
    assert not os.path.exists(path)
