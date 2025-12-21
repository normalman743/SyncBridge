import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app import models, crud
from datetime import datetime
from unittest.mock import patch

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
def test_client_user(db=TestingSessionLocal()):
    user = models.User(username="client1", email="client1@example.com", role="client", hashed_password="fakehash")
    db.add(user); db.commit(); db.refresh(user)
    return user

@pytest.fixture
def test_form(test_client_user, db=TestingSessionLocal()):
    f = models.Form(type=models.FormType.mainform, title="Test Form", user_id=test_client_user.id,
                    status=models.FormStatus.preview, created_at=datetime.utcnow())
    db.add(f); db.commit(); db.refresh(f)
    return f

@pytest.fixture
def test_block(test_form, db=TestingSessionLocal()):
    block = models.Block(form_id=test_form.id, type="general", target_id=None)
    db.add(block); db.commit(); db.refresh(block)
    return block

@pytest.fixture
def test_message(test_block, test_client_user, db=TestingSessionLocal()):
    msg = models.Message(block_id=test_block.id, user_id=test_client_user.id, text_content="Hello", created_at=datetime.utcnow())
    db.add(msg); db.commit(); db.refresh(msg)
    return msg

# =========================
# Mock WebSocket broadcast
# =========================
@pytest.fixture(autouse=True)
def mock_ws_broadcast():
    with patch("app.routers.messages.manager.broadcast") as mock_broadcast:
        yield mock_broadcast

# =========================
# Test get messages
# =========================
def test_get_messages(test_form, test_block, test_message, test_client_user):
    response = client.get(f"/messages?form_id={test_form.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "messages" in data
    assert len(data["messages"]) >= 1
    assert data["messages"][0]["text_content"] == test_message.text_content

# =========================
# Test post message
# =========================
def test_post_message(test_form, test_client_user, mock_ws_broadcast):
    payload = {"form_id": test_form.id, "text_content": "New message"}
    response = client.post("/message", json=payload)
    assert response.status_code == 200
    assert "message_id" in response.json()["data"]
    # WS broadcast should be called
    assert mock_ws_broadcast.called

# =========================
# Test post message form not found
# =========================
def test_post_message_form_not_found(test_client_user):
    payload = {"form_id": 999, "text_content": "X"}
    response = client.post("/message", json=payload)
    assert response.status_code == 404

# =========================
# Test update message
# =========================
def test_update_message(test_message, mock_ws_broadcast):
    payload = {"text_content": "Updated"}
    response = client.put(f"/message/{test_message.id}", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Message updated"
    assert mock_ws_broadcast.called

# =========================
# Test update message not found
# =========================
def test_update_message_not_found():
    payload = {"text_content": "X"}
    response = client.put("/message/999", json=payload)
    assert response.status_code == 404

# =========================
# Test delete message
# =========================
def test_delete_message(test_message, mock_ws_broadcast):
    response = client.delete(f"/message/{test_message.id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Message deleted"
    assert mock_ws_broadcast.called

# =========================
# Test delete message not found
# =========================
def test_delete_message_not_found():
    response = client.delete("/message/999")
    assert response.status_code == 404
