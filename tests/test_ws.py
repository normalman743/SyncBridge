import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app import models, crud
from datetime import datetime
from unittest.mock import patch, AsyncMock
import json

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

# =========================
# Mock token decoding
# =========================
@pytest.fixture
def mock_decode_token(test_client_user):
    with patch("app.routers.ws.utils.decode_access_token") as mock_decode:
        mock_decode.return_value = {"sub": str(test_client_user.id)}
        yield mock_decode

# =========================
# Mock WebSocket manager
# =========================
@pytest.fixture
def mock_manager():
    with patch("app.routers.ws.manager.connect", new_callable=AsyncMock) as mock_connect, \
         patch("app.routers.ws.manager.disconnect", new_callable=AsyncMock) as mock_disconnect, \
         patch("app.routers.ws.manager.broadcast", new_callable=AsyncMock) as mock_broadcast, \
         patch("app.routers.ws.manager.send_to", new_callable=AsyncMock) as mock_send_to:
        yield {
            "connect": mock_connect,
            "disconnect": mock_disconnect,
            "broadcast": mock_broadcast,
            "send_to": mock_send_to
        }

# =========================
# Test WS connect and presence
# =========================
def test_websocket_connect(test_form, mock_decode_token, mock_manager):
    with client.websocket_connect(f"/ws?token=fake&form_id={test_form.id}") as websocket:
        # On connect, server should send presence join broadcast
        # We can simulate sending ping
        websocket.send_text("ping")
        # Receive pong
        # Since send_to is mocked, we won't actually receive a real message, just ensure no error occurs

        # Send normal message (ignored by server)
        websocket.send_text("hello")
        # Close connection
        websocket.close()
    # Ensure connect/disconnect called
    assert mock_manager["connect"].called
    assert mock_manager["disconnect"].called
    assert mock_manager["broadcast"].called

# =========================
# Test WS without token
# =========================
def test_websocket_no_token(test_form):
    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws?form_id={test_form.id}") as websocket:
            pass  # Should close immediately

# =========================
# Test WS with invalid token
# =========================
def test_websocket_invalid_token(test_form):
    with patch("app.routers.ws.utils.decode_access_token") as mock_decode:
        mock_decode.return_value = None
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws?token=invalid&form_id={test_form.id}") as websocket:
                pass
