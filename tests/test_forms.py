import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app import models, crud
from datetime import datetime

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
def test_developer_user(db=TestingSessionLocal()):
    user = models.User(username="dev1", email="dev1@example.com", role="developer", hashed_password="fakehash")
    db.add(user); db.commit(); db.refresh(user)
    return user

@pytest.fixture
def test_form(test_client_user, db=TestingSessionLocal()):
    f = models.Form(type=models.FormType.mainform, title="Test Form", user_id=test_client_user.id,
                    status=models.FormStatus.preview, created_at=datetime.utcnow())
    db.add(f); db.commit(); db.refresh(f)
    return f

# =========================
# Test list forms
# =========================
def test_list_forms(test_client_user):
    response = client.get("/forms")
    assert response.status_code == 200
    assert "forms" in response.json()["data"]

# =========================
# Test get form
# =========================
def test_get_form(test_form):
    response = client.get(f"/form/{test_form.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == test_form.id
    assert data["title"] == test_form.title

# =========================
# Test create form
# =========================
def test_create_form(test_client_user):
    payload = {"title": "New Form", "message": "Hello", "budget": 100, "expected_time": "3d"}
    response = client.post("/form", json=payload)
    assert response.status_code == 200
    assert "form_id" in response.json()["data"]

# =========================
# Test update form
# =========================
def test_update_form(test_form):
    payload = {"title": "Updated Form"}
    response = client.put(f"/form/{test_form.id}", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Form updated"

# =========================
# Test delete form
# =========================
def test_delete_form(test_form):
    response = client.delete(f"/form/{test_form.id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Form deleted"

# =========================
# Test create subform
# =========================
def test_create_subform(test_form, test_client_user):
    payload = {"title": "Subform", "message": "Sub", "budget": 50, "expected_time": "1d"}
    response = client.post(f"/form/{test_form.id}/subform", json=payload)
    assert response.status_code == 200
    assert "subform_id" in response.json()["data"]

# =========================
# Test update status
# =========================
def test_update_status(test_form, test_client_user):
    payload = {"status": "available"}  # assuming allowed transition
    response = client.put(f"/form/{test_form.id}/status", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Status updated"

# =========================
# Test invalid status
# =========================
def test_update_status_invalid(test_form):
    payload = {"status": "invalid_status"}
    response = client.put(f"/form/{test_form.id}/status", json=payload)
    assert response.status_code in (400, 403, 422)
