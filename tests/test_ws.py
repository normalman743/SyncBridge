import json
import pytest

from starlette.websockets import WebSocketDisconnect

from app.repositories import forms as form_repo
from tests.conftest import create_user, create_license

AUTH_BASE = "/api/v1/auth"
API_BASE = "/api/v1"


def _make_user_with_token(client, db_session, email, role):
    user = create_user(db_session, email=email, password="StrongPass123", role=role, is_active=1)
    create_license(db_session, key=f"LIC-{email}", role=role, status="active", user=user)
    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return user, token


def _make_form(client_user_id, db_session, status="processing", developer_id=None):
    form = form_repo.create_mainform(
        db_session,
        client_user_id,
        {"title": "FormWS", "message": "M", "budget": "B", "expected_time": "T"},
    )
    form.status = status
    form.developer_id = developer_id
    db_session.add(form)
    db_session.commit()
    db_session.refresh(form)
    return form


def test_websocket_connect_and_ping(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "ws-owner@example.com", "client")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)

    with client.websocket_connect(f"{API_BASE}/ws?token={owner_token}&form_id={form.id}") as ws:
        # First broadcast is presence join
        msg = json.loads(ws.receive_text())
        assert msg["type"] == "presence" and msg["action"] == "join"
        # ping/pong
        ws.send_text("ping")
        pong = json.loads(ws.receive_text())
        assert pong == {"type": "pong"}


def test_websocket_forbidden_for_unassigned_developer(client, db_session):
    owner, _ = _make_user_with_token(client, db_session, "ws-owner2@example.com", "client")
    dev, dev_token = _make_user_with_token(client, db_session, "ws-dev@example.com", "developer")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)
    db_session.refresh(form)
    assert form.status == "processing"
    assert form.developer_id is None

    # Developer not bound and form not available -> server closes during handshake or immediately after
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"{API_BASE}/ws?token={dev_token}&form_id={form.id}") as ws:
            ws.receive_text()
