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
def test_form(test_client_user, db=TestingSessionLocal()):
    f = models.Form(type=models.FormType.mainform, title="Test Form", user_id=test_client_user.id,
                    status=models.FormStatus.preview, created_at=datetime.utcnow())
    db.add(f); db.commit(); db.refresh(f)
    return f

@pytest.fixture
def test_nonfunction(test_form, db=TestingSessionLocal()):
    nf = models.NonFunction(form_id=test_form.id, name="NonFunc1", level="low", description="desc", status="active", is_changed=False)
    db.add(nf); db.commit(); db.refresh(nf)
    return nf

# =========================
# Test list nonfunctions
# =========================
def test_list_nonfunctions(test_form, test_nonfunction, test_client_user):
    response = client.get(f"/nonfunctions?form_id={test_form.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "nonfunctions" in data
    assert len(data["nonfunctions"]) >= 1
    assert data["nonfunctions"][0]["name"] == test_nonfunction.name

# =========================
# Test create nonfunction
# =========================
def test_create_nonfunction(test_form, test_client_user):
    payload = {"form_id": test_form.id, "name": "NewNonFunc", "choice": "no", "description": "desc"}
    response = client.post("/nonfunction", json=payload)
    assert response.status_code == 200
    assert "id" in response.json()["data"]

# =========================
# Test create nonfunction form not found
# =========================
def test_create_nonfunction_form_not_found(test_client_user):
    payload = {"form_id": 999, "name": "X", "choice": "no", "description": "desc"}
    response = client.post("/nonfunction", json=payload)
    assert response.status_code == 404

# =========================
# Test update nonfunction
# =========================
def test_update_nonfunction(test_nonfunction):
    payload = {"name": "UpdatedNonFunc", "description": "updated"}
    response = client.put(f"/nonfunction/{test_nonfunction.id}", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "NonFunction updated"

# =========================
# Test update nonfunction not found
# =========================
def test_update_nonfunction_not_found():
    payload = {"name": "X"}
    response = client.put("/nonfunction/999", json=payload)
    assert response.status_code == 404

# =========================
# Test delete nonfunction
# =========================
def test_delete_nonfunction(test_nonfunction):
    response = client.delete(f"/nonfunction/{test_nonfunction.id}")
    assert response.status_code == 200
    assert response.json()["message"] == "NonFunction deleted"

# =========================
# Test delete nonfunction not found
# =========================
def test_delete_nonfunction_not_found():
    response = client.delete("/nonfunction/999")
    assert response.status_code == 404
