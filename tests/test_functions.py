import pytest
import io
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
def test_function(test_form, db=TestingSessionLocal()):
    fn = models.Function(form_id=test_form.id, name="Func1", choice="yes", description="desc", status="active", is_changed=False)
    db.add(fn); db.commit(); db.refresh(fn)
    return fn

# =========================
# Test list functions
# =========================
def test_list_functions(test_form, test_client_user):
    response = client.get(f"/functions?form_id={test_form.id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "functions" in data

# =========================
# Test create function
# =========================
def test_create_function(test_form, test_client_user):
    payload = {"form_id": test_form.id, "name": "NewFunc", "choice": "no", "description": "desc"}
    response = client.post("/function", json=payload)
    assert response.status_code == 200
    assert "id" in response.json()["data"]

# =========================
# Test create function form not found
# =========================
def test_create_function_form_not_found(test_client_user):
    payload = {"form_id": 999, "name": "FuncX", "choice": "no", "description": "desc"}
    response = client.post("/function", json=payload)
    assert response.status_code == 404

# =========================
# Test update function
# =========================
def test_update_function(test_function):
    payload = {"name": "UpdatedFunc", "description": "updated"}
    response = client.put(f"/function/{test_function.id}", json=payload)
    assert response.status_code == 200
    assert response.json()["message"] == "Function updated"

# =========================
# Test update function not found
# =========================
def test_update_function_not_found():
    payload = {"name": "X"}
    response = client.put("/function/999", json=payload)
    assert response.status_code == 404

# =========================
# Test delete function
# =========================
def test_delete_function(test_function):
    response = client.delete(f"/function/{test_function.id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Function deleted"

# =========================
# Test delete function not found
# =========================
def test_delete_function_not_found():
    response = client.delete("/function/999")
    assert response.status_code == 404
