import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch

from app.main import app
from app.models import User
from app.routers import auth
from app import utils

client = TestClient(app)

# ------------------------------
# Mock 数据
# ------------------------------
mock_user = User(id=1, email="test@example.com", display_name="Test User", role=MagicMock(value="user"))

# ------------------------------
# 测试注册
# ------------------------------
@patch("app.routers.auth.crud.get_user_by_email")
@patch("app.routers.auth.crud.create_user")
@patch("app.routers.auth.crud.activate_license")
@patch("app.routers.auth.utils.create_access_token")
def test_register_success(mock_create_token, mock_activate_license, mock_create_user, mock_get_user_by_email):
    # 模拟数据库中没有重复用户
    mock_get_user_by_email.return_value = None
    # 模拟创建用户成功
    mock_create_user.return_value = mock_user
    # 模拟激活 license 成功
    mock_activate_license.return_value = (MagicMock(), None)
    # 模拟生成 token
    mock_create_token.return_value = "mock_token"

    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "display_name": "Test User",
        "license_key": "LICENSE123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["user_id"] == mock_user.id
    assert data["data"]["access_token"] == "mock_token"

# ------------------------------
# 测试注册重复 Email
# ------------------------------
@patch("app.routers.auth.crud.get_user_by_email")
def test_register_email_conflict(mock_get_user_by_email):
    mock_get_user_by_email.return_value = mock_user
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "display_name": "Test User",
        "license_key": "LICENSE123"
    })
    assert response.status_code == 409

# ------------------------------
# 测试登录成功
# ------------------------------
@patch("app.routers.auth.crud.authenticate")
@patch("app.routers.auth.utils.create_access_token")
def test_login_success(mock_create_token, mock_authenticate):
    mock_authenticate.return_value = mock_user
    mock_create_token.return_value = "mock_token"

    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["access_token"] == "mock_token"

# ------------------------------
# 测试登录失败
# ------------------------------
@patch("app.routers.auth.crud.authenticate")
def test_login_failure(mock_authenticate):
    mock_authenticate.return_value = None
    response = client.post("/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpass"
    })
    assert response.status_code == 401

# ------------------------------
# 测试 /me 获取当前用户信息
# ------------------------------
@patch("app.routers.auth.crud.get_user_by_id")
@patch("app.routers.auth.utils.decode_access_token")
def test_me_success(mock_decode_token, mock_get_user):
    mock_decode_token.return_value = {"sub": mock_user.id}
    mock_get_user.return_value = mock_user

    headers = {"Authorization": "Bearer valid_token"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["email"] == mock_user.email

# 测试 /me 缺少 token
def test_me_missing_token():
    response = client.get("/auth/me")
    assert response.status_code == 401

# 测试 /me token 无效
@patch("app.routers.auth.utils.decode_access_token")
def test_me_invalid_token(mock_decode_token):
    mock_decode_token.return_value = None
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401
