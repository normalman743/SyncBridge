from datetime import datetime, timedelta

import pytest

from app.models import AuditLog, Block, Form
from app.services import audit as audit_service
from app.services import reminders
from tests.conftest import create_license, create_user


def _make_user_with_token(client, db_session, email, role):
    user = create_user(db_session, email=email, password="StrongPass123", role=role, is_active=1)
    create_license(db_session, key=f"LIC-{email}", role=role, status="active", user=user)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPass123"},
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return user, token


def test_reminder_process_sets_flag_and_sends_email(monkeypatch, db_session):
    send_calls = []

    def fake_send_email(recipients, subject, html):
        send_calls.append((tuple(recipients), subject, html))

    monkeypatch.setattr(reminders, "send_email", fake_send_email)

    client_user = create_user(db_session, email="rem-client@example.com", password="StrongPass123", role="client", is_active=1)
    dev_user = create_user(db_session, email="rem-dev@example.com", password="StrongPass123", role="developer", is_active=1)

    form = Form(
        type="mainform",
        user_id=client_user.id,
        developer_id=dev_user.id,
        created_by=client_user.id,
        title="R1",
        message="msg",
        budget="b",
        expected_time="t",
        status="processing",
    )
    db_session.add(form)
    db_session.commit()
    db_session.refresh(form)

    block = Block(
        form_id=form.id,
        status="urgent",
        type="general",
        target_id=None,
        last_message_at=datetime.utcnow() - timedelta(minutes=10),
        reminder_sent=0,
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)

    reminders._process_blocks(db_session, [block])
    db_session.refresh(block)
    assert block.reminder_sent == 1
    assert len(send_calls) == 1
    recipients, _, _ = send_calls[0]
    assert "rem-client@example.com" in recipients
    assert "rem-dev@example.com" in recipients


def test_reminder_process_no_recipients_sets_flag(monkeypatch, db_session):
    send_calls = []
    monkeypatch.setattr(reminders, "send_email", lambda recipients, subject, html: send_calls.append(recipients))

    # user without usable email (empty string to skip recipient list)
    client_user = create_user(db_session, email="", password="StrongPass123", role="client", is_active=1)
    form = Form(
        type="mainform",
        user_id=client_user.id,
        developer_id=None,
        created_by=client_user.id,
        title="R2",
        message="msg",
        budget="b",
        expected_time="t",
        status="processing",
    )
    db_session.add(form)
    db_session.commit()
    db_session.refresh(form)

    block = Block(
        form_id=form.id,
        status="normal",
        type="general",
        target_id=None,
        last_message_at=datetime.utcnow() - timedelta(hours=50),
        reminder_sent=0,
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)

    reminders._process_blocks(db_session, [block])
    db_session.refresh(block)
    assert block.reminder_sent == 1
    assert send_calls == []


def test_audit_log_written_when_enabled(client, db_session):
    # Enable audit for this test
    audit_service.AUDIT_ENABLED = True

    client_user, client_token = _make_user_with_token(client, db_session, "audit-client@example.com", "client")
    form = Form(
        type="mainform",
        user_id=client_user.id,
        developer_id=None,
        created_by=client_user.id,
        title="A1",
        message="msg",
        budget="b",
        expected_time="t",
        status="preview",
    )
    db_session.add(form)
    db_session.commit()
    db_session.refresh(form)

    # Directly call log_audit to validate audit writer
    audit_service.log_audit(db_session, "form", form.id, "update", client_user.id, {"title": "A1"}, {"title": "A1-updated"})

    rows = db_session.query(AuditLog).filter(AuditLog.entity_type == "form", AuditLog.entity_id == form.id).all()
    assert len(rows) >= 1

    # Reset audit flag
    audit_service.AUDIT_ENABLED = False
