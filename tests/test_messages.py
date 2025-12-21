from app.models import Message, Block
from app.repositories import blocks as block_repo, forms as form_repo, messages as message_repo
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
        {"title": "FormMsg", "message": "M", "budget": "B", "expected_time": "T"},
    )
    form.status = status
    form.developer_id = developer_id
    db_session.add(form)
    db_session.commit()
    db_session.refresh(form)
    return form


def test_post_and_get_messages_allowed(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "msg-owner@example.com", "client")
    dev, dev_token = _make_user_with_token(client, db_session, "msg-dev@example.com", "developer")
    form = _make_form(owner.id, db_session, status="processing", developer_id=dev.id)

    payload = {"form_id": form.id, "text_content": "hello from client"}
    resp_client = client.post(
        f"{API_BASE}/message",
        json=payload,
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_client.status_code == 200

    payload_dev = {"form_id": form.id, "text_content": "hello from dev"}
    resp_dev = client.post(
        f"{API_BASE}/message",
        json=payload_dev,
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_dev.status_code == 200

    resp_list = client.get(
        f"{API_BASE}/messages?form_id={form.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_list.status_code == 200
    messages = resp_list.json()["data"]["messages"]
    texts = {m["text_content"] for m in messages}
    assert "hello from client" in texts
    assert "hello from dev" in texts


def test_post_message_forbidden_unassigned_developer(client, db_session):
    owner, _ = _make_user_with_token(client, db_session, "msg-owner2@example.com", "client")
    dev, dev_token = _make_user_with_token(client, db_session, "msg-dev2@example.com", "developer")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)

    resp = client.post(
        f"{API_BASE}/message",
        json={"form_id": form.id, "text_content": "should fail"},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp.status_code == 403


def test_update_message_only_sender(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "msg-owner3@example.com", "client")
    dev, dev_token = _make_user_with_token(client, db_session, "msg-dev3@example.com", "developer")
    form = _make_form(owner.id, db_session, status="processing", developer_id=dev.id)

    # Owner sends message
    resp_msg = client.post(
        f"{API_BASE}/message",
        json={"form_id": form.id, "text_content": "original"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    msg_id = resp_msg.json()["data"]["message_id"]
    # Developer tries to update -> forbidden
    resp_forbidden = client.put(
        f"{API_BASE}/message/{msg_id}",
        json={"text_content": "hacked"},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_forbidden.status_code == 403

    # Owner updates successfully
    resp_ok = client.put(
        f"{API_BASE}/message/{msg_id}",
        json={"text_content": "updated"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_ok.status_code == 200
    msg = message_repo.get_by_id(db_session, msg_id)
    assert msg.text_content == "updated"


def test_update_message_no_changes_and_not_found(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "msg-owner6@example.com", "client")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)
    resp_msg = client.post(
        f"{API_BASE}/message",
        json={"form_id": form.id, "text_content": "original"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    msg_id = resp_msg.json()["data"]["message_id"]

    resp_no_changes = client.put(
        f"{API_BASE}/message/{msg_id}",
        json={},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_no_changes.status_code == 400

    resp_not_found = client.put(
        f"{API_BASE}/message/9999",
        json={"text_content": "x"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_not_found.status_code == 404


def test_delete_message_only_sender(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "msg-owner4@example.com", "client")
    dev, dev_token = _make_user_with_token(client, db_session, "msg-dev4@example.com", "developer")
    form = _make_form(owner.id, db_session, status="processing", developer_id=dev.id)

    # Dev sends a message
    resp_msg = client.post(
        f"{API_BASE}/message",
        json={"form_id": form.id, "text_content": "to delete"},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    msg_id = resp_msg.json()["data"]["message_id"]

    # Owner cannot delete dev's message
    resp_forbidden = client.delete(
        f"{API_BASE}/message/{msg_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_forbidden.status_code == 403

    # Dev deletes successfully
    resp_ok = client.delete(
        f"{API_BASE}/message/{msg_id}",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_ok.status_code == 200
    assert message_repo.get_by_id(db_session, msg_id) is None


def test_delete_message_not_found(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "msg-owner8@example.com", "client")
    resp = client.delete(
        f"{API_BASE}/message/9999",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 404


def test_update_block_status(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "msg-owner5@example.com", "client")
    dev, dev_token = _make_user_with_token(client, db_session, "msg-dev5@example.com", "developer")
    form = _make_form(owner.id, db_session, status="processing", developer_id=dev.id)

    # Create a block by posting a message
    resp_msg = client.post(
        f"{API_BASE}/message",
        json={"form_id": form.id, "text_content": "trigger block"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    msg_id = resp_msg.json()["data"]["message_id"]
    msg = message_repo.get_by_id(db_session, msg_id)
    block = block_repo.get_by_id(db_session, msg.block_id)

    # Invalid status
    resp_invalid = client.put(
        f"{API_BASE}/block/{block.id}/status",
        json={"status": "invalid"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_invalid.status_code == 400

    # Developer updates to urgent successfully
    resp_ok = client.put(
        f"{API_BASE}/block/{block.id}/status",
        json={"status": "urgent"},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_ok.status_code == 200
    db_session.refresh(block)
    assert block.status == "urgent"


def test_get_messages_form_not_found_and_forbidden(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "msg-owner7@example.com", "client")
    other, other_token = _make_user_with_token(client, db_session, "msg-other@example.com", "client")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)

    resp_not_found = client.get(
        f"{API_BASE}/messages?form_id=9999",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_not_found.status_code == 404

    resp_forbidden = client.get(
        f"{API_BASE}/messages?form_id={form.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp_forbidden.status_code == 403
