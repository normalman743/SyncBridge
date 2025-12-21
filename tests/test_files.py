import os

from app.repositories import forms as form_repo, files as file_repo
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
        {"title": "FormFile", "message": "M", "budget": "B", "expected_time": "T"},
    )
    form.status = status
    form.developer_id = developer_id
    db_session.add(form)
    db_session.commit()
    db_session.refresh(form)
    return form


def _post_message(client, token, form_id, text="hello"):
    resp = client.post(
        f"{API_BASE}/message",
        json={"form_id": form_id, "text_content": text},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["message_id"]


def test_upload_and_get_file_success(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "file-owner@example.com", "client")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)
    message_id = _post_message(client, owner_token, form.id, text="with file")

    upload_resp = client.post(
        f"{API_BASE}/file",
        params={"message_id": message_id},
        files={"file": ("hello.txt", b"hello world", "text/plain")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert upload_resp.status_code == 200
    file_id = upload_resp.json()["data"]["file_id"]
    rec = file_repo.get_by_id(db_session, file_id)
    assert rec is not None and os.path.exists(rec.storage_path)

    download = client.get(
        f"{API_BASE}/file/{file_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert download.status_code == 200
    assert download.content == b"hello world"

    # cleanup and verify delete works
    del_resp = client.delete(
        f"{API_BASE}/file/{file_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert del_resp.status_code == 200
    assert file_repo.get_by_id(db_session, file_id) is None
    assert not os.path.exists(rec.storage_path)


def test_upload_forbidden_unassigned_developer(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "file-owner2@example.com", "client")
    dev, dev_token = _make_user_with_token(client, db_session, "file-dev2@example.com", "developer")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)
    message_id = _post_message(client, owner_token, form.id, text="no dev access")

    resp = client.post(
        f"{API_BASE}/file",
        params={"message_id": message_id},
        files={"file": ("forbid.txt", b"nope", "text/plain")},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp.status_code == 403


def test_get_file_forbidden_other_client(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "file-owner3@example.com", "client")
    other, other_token = _make_user_with_token(client, db_session, "file-other@example.com", "client")
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)
    message_id = _post_message(client, owner_token, form.id, text="private file")

    upload_resp = client.post(
        f"{API_BASE}/file",
        params={"message_id": message_id},
        files={"file": ("secret.txt", b"secret", "text/plain")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    file_id = upload_resp.json()["data"]["file_id"]

    resp_forbidden = client.get(
        f"{API_BASE}/file/{file_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp_forbidden.status_code == 403


def test_delete_file_only_sender(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "file-owner4@example.com", "client")
    dev, dev_token = _make_user_with_token(client, db_session, "file-dev3@example.com", "developer")
    form = _make_form(owner.id, db_session, status="processing", developer_id=dev.id)

    msg_id = _post_message(client, dev_token, form.id, text="dev message")

    upload_resp = client.post(
        f"{API_BASE}/file",
        params={"message_id": msg_id},
        files={"file": ("mine.txt", b"mine", "text/plain")},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    file_id = upload_resp.json()["data"]["file_id"]
    rec = file_repo.get_by_id(db_session, file_id)
    assert rec is not None

    # Owner (not sender) cannot delete
    resp_forbidden = client.delete(
        f"{API_BASE}/file/{file_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_forbidden.status_code == 403

    # Sender can delete
    resp_ok = client.delete(
        f"{API_BASE}/file/{file_id}",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_ok.status_code == 200
    assert file_repo.get_by_id(db_session, file_id) is None
    assert not os.path.exists(rec.storage_path)


def test_upload_file_message_not_found_and_too_large(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "file-owner5@example.com", "client")
    # Message id does not exist -> 404
    resp_not_found = client.post(
        f"{API_BASE}/file",
        params={"message_id": 9999},
        files={"file": ("missing.txt", b"noop", "text/plain")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_not_found.status_code == 404

    # Large file (>10MB default) -> 400
    form = _make_form(owner.id, db_session, status="processing", developer_id=None)
    msg_id = _post_message(client, owner_token, form.id, text="big file")
    big_content = b"x" * (11 * 1024 * 1024)  # ~11MB
    resp_too_large = client.post(
        f"{API_BASE}/file",
        params={"message_id": msg_id},
        files={"file": ("big.bin", big_content, "application/octet-stream")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_too_large.status_code == 400
