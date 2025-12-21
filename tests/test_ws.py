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


def test_websocket_forbidden_other_client(client, db_session):
    owner, _ = _make_user_with_token(client, db_session, "ws-owner2@example.com", "client")
    other_client, other_token = _make_user_with_token(client, db_session, "ws-other@example.com", "client")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)
    db_session.refresh(form)
    assert form.status == "processing"
    assert form.developer_id is None

    # Other client without ownership should be rejected with policy violation (1008)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"{API_BASE}/ws?token={other_token}&form_id={form.id}") as ws:
            ws.receive_text()


def test_websocket_missing_token(client, db_session):
    owner, _ = _make_user_with_token(client, db_session, "ws-owner3@example.com", "client")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"{API_BASE}/ws?form_id={form.id}") as ws:
            ws.receive_text()


def test_websocket_invalid_token_and_form_not_found(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "ws-owner4@example.com", "client")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)

    # Invalid token
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"{API_BASE}/ws?token=badtoken&form_id={form.id}") as ws:
            ws.receive_text()

    # Valid token but missing form
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"{API_BASE}/ws?token={owner_token}&form_id=9999") as ws:
            ws.receive_text()


def test_websocket_developer_allowed_when_available_and_denied_when_processing(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "ws-owner5@example.com", "client")
    dev, dev_token = _make_user_with_token(client, db_session, "ws-dev5@example.com", "developer")

    # available -> unassigned developer can join
    form_available = _make_form(owner.id, db_session, status="available", developer_id=None)
    with client.websocket_connect(f"{API_BASE}/ws?token={dev_token}&form_id={form_available.id}") as ws:
        msg = json.loads(ws.receive_text())
        assert msg["type"] == "presence" and msg["action"] == "join"
        ws.close()

    # processing and unassigned -> should be denied
    form_processing = _make_form(owner.id, db_session, status="processing", developer_id=None)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"{API_BASE}/ws?token={dev_token}&form_id={form_processing.id}") as ws:
            ws.receive_text()
