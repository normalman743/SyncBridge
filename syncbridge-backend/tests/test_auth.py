from datetime import datetime, timedelta

import pytest

from tests.conftest import create_license, create_user


AUTH_BASE = "/api/v1/auth"


# ---------- Register ----------

def test_register_success(client, db_session):
    create_license(db_session, key="LIC-NEW-CLIENT", role="client", status="unused")
    payload = {
        "email": "newuser@example.com",
        "password": "StrongPass123",
        "display_name": "New User",
        "license_key": "LIC-NEW-CLIENT",
    }
    resp = client.post(f"{AUTH_BASE}/register", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["role"] == "client"
    assert data["license_status"] == "active"
    assert data["user_id"] > 0
    assert "access_token" in data


def test_register_duplicate_email(client, db_session):
    existing = create_user(db_session, email="dup@example.com", password="StrongPass123", role="client")
    # License available for attempted registration
    create_license(db_session, key="LIC-DUP", role="client", status="unused")
    payload = {
        "email": existing.email,
        "password": "StrongPass123",
        "display_name": "Dup User",
        "license_key": "LIC-DUP",
    }
    resp = client.post(f"{AUTH_BASE}/register", json=payload)
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["code"] == "CONFLICT"


def test_register_weak_password(client, db_session):
    create_license(db_session, key="LIC-WEAK", role="client", status="unused")
    payload = {
        "email": "weakpass@example.com",
        "password": "weak",  # no digits/too short
        "display_name": "Weak",
        "license_key": "LIC-WEAK",
    }
    resp = client.post(f"{AUTH_BASE}/register", json=payload)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"


def test_register_invalid_license(client):
    payload = {
        "email": "nolicense@example.com",
        "password": "StrongPass123",
        "display_name": "No License",
        "license_key": "NON-EXIST",
    }
    resp = client.post(f"{AUTH_BASE}/register", json=payload)
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "FORBIDDEN"


def test_register_license_not_unused(client, db_session):
    # License already active/used
    used_user = create_user(db_session, email="used@example.com", password="StrongPass123", role="client")
    create_license(db_session, key="LIC-USED", role="client", status="active", user=used_user)
    payload = {
        "email": "new@example.com",
        "password": "StrongPass123",
        "display_name": "New",
        "license_key": "LIC-USED",
    }
    resp = client.post(f"{AUTH_BASE}/register", json=payload)
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "FORBIDDEN"


# ---------- Login ----------

def test_login_success(client, db_session):
    user = create_user(db_session, email="login@example.com", password="StrongPass123", role="client", is_active=1)
    create_license(db_session, key="LIC-ACTIVE", role="client", status="active", user=user)
    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"email": "login@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["license_status"] == "active"
    assert body["data"]["role"] == "client"
    assert "access_token" in body["data"]


def test_login_invalid_credentials(client, db_session):
    create_user(db_session, email="wrongpass@example.com", password="StrongPass123", role="client", is_active=1)
    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"email": "wrongpass@example.com", "password": "BadPass999"},
    )
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"


def test_login_inactive_user(client, db_session):
    user = create_user(db_session, email="inactive@example.com", password="StrongPass123", role="client", is_active=0)
    create_license(db_session, key="LIC-INACTIVE", role="client", status="active", user=user, activate_user=False)
    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"email": "inactive@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["message"] == "User is inactive"
    assert detail["code"] == "FORBIDDEN"


def test_login_license_expired(client, db_session):
    user = create_user(db_session, email="expired@example.com", password="StrongPass123", role="client", is_active=1)
    expired_at = datetime.utcnow() - timedelta(days=1)
    create_license(
        db_session,
        key="LIC-EXPIRED",
        role="client",
        status="active",
        user=user,
        expires_at=expired_at,
    )
    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"email": "expired@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["message"] == "License expired"
    assert detail["code"] == "FORBIDDEN"
    db_session.refresh(user)
    assert user.is_active == 0  # user should be deactivated on expired license


def test_login_license_revoked(client, db_session):
    user = create_user(db_session, email="revoked@example.com", password="StrongPass123", role="client", is_active=1)
    create_license(db_session, key="LIC-REVOKED", role="client", status="revoked", user=user)
    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"email": "revoked@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["message"] == "License not active"
    assert detail["code"] == "FORBIDDEN"
    db_session.refresh(user)
    assert user.is_active == 0


def test_login_email_not_found(client):
    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"email": "missing@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"


def test_login_license_not_found(client, db_session):
    user = create_user(db_session, email="nolicense@example.com", password="StrongPass123", role="client", is_active=1)
    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"email": user.email, "password": "StrongPass123"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["message"] == "License not found"
    assert detail["code"] == "FORBIDDEN"
    db_session.refresh(user)
    assert user.is_active == 0


# ---------- Me ----------

def test_me_success(client, db_session):
    user = create_user(db_session, email="me@example.com", password="StrongPass123", role="client", is_active=1)
    create_license(db_session, key="LIC-ME", role="client", status="active", user=user)
    login_resp = client.post(
        f"{AUTH_BASE}/login",
        json={"email": user.email, "password": "StrongPass123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]

    resp = client.get(f"{AUTH_BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["user_id"] == user.id
    assert body["data"]["email"] == user.email
    assert body["data"]["role"] == "client"


def test_me_unauthorized(client):
    resp = client.get(f"{AUTH_BASE}/me")
    assert resp.status_code == 401


# ---------- Reactivate ----------

def test_reactivate_success(client, db_session):
    user = create_user(db_session, email="reuser@example.com", password="StrongPass123", role="client", is_active=1)
    old_lic = create_license(db_session, key="LIC-OLD", role="client", status="active", user=user)
    new_lic = create_license(db_session, key="LIC-NEW", role="developer", status="unused")
    resp = client.post(
        f"{AUTH_BASE}/reactivate",
        json={
            "email": user.email,
            "password": "StrongPass123",
            "license_key": new_lic.license_key,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["user_id"] == user.id
    assert body["data"]["role"] == "developer"  # updated to new license role
    db_session.refresh(old_lic)
    db_session.refresh(new_lic)
    db_session.refresh(user)
    assert old_lic.status == "revoked"
    assert new_lic.status == "active"
    assert new_lic.user_id == user.id
    assert user.role == "developer"
    assert user.is_active == 1


def test_reactivate_invalid_license(client, db_session):
    create_user(db_session, email="badlic@example.com", password="StrongPass123", role="client", is_active=1)
    resp = client.post(
        f"{AUTH_BASE}/reactivate",
        json={
            "email": "badlic@example.com",
            "password": "StrongPass123",
            "license_key": "NO-LIC",
        },
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "FORBIDDEN"


def test_reactivate_wrong_password(client, db_session):
    user = create_user(db_session, email="badpass@example.com", password="StrongPass123", role="client", is_active=1)
    create_license(db_session, key="LIC-R1", role="client", status="unused")
    resp = client.post(
        f"{AUTH_BASE}/reactivate",
        json={
            "email": user.email,
            "password": "WrongPass123",
            "license_key": "LIC-R1",
        },
    )
    assert resp.status_code == 401
    detail = resp.json()["detail"]
    assert detail["code"] == "UNAUTHORIZED"


def test_reactivate_license_not_unused(client, db_session):
    user = create_user(db_session, email="react2@example.com", password="StrongPass123", role="client", is_active=1)
    active_lic = create_license(db_session, key="LIC-ACTIVE2", role="client", status="active", user=user)
    resp = client.post(
        f"{AUTH_BASE}/reactivate",
        json={
            "email": user.email,
            "password": "StrongPass123",
            "license_key": active_lic.license_key,
        },
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["code"] == "FORBIDDEN"
