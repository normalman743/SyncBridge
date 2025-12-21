from app.repositories import forms as form_repo
from tests.conftest import create_user, create_license

AUTH_BASE = "/api/v1/auth"
FORMS_BASE = "/api/v1"


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


def test_create_form_client_success_and_developer_forbidden(client, db_session):
    client_user, client_token = _make_user_with_token(client, db_session, "client1@example.com", "client")
    dev_user, dev_token = _make_user_with_token(client, db_session, "dev1@example.com", "developer")

    payload = {"title": "T1", "message": "M1", "budget": "$1000", "expected_time": "1w"}
    resp_ok = client.post(
        f"{FORMS_BASE}/form",
        json=payload,
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp_ok.status_code == 200
    form_id = resp_ok.json()["data"]["form_id"]
    created = form_repo.get(db_session, form_id)
    assert created is not None
    assert created.user_id == client_user.id
    assert created.status == "preview"

    resp_forbidden = client.post(
        f"{FORMS_BASE}/form",
        json=payload,
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_forbidden.status_code == 403


def test_get_form_permissions_for_developer_available_and_denied_unassigned(client, db_session):
    client_user, _ = _make_user_with_token(client, db_session, "owner@example.com", "client")
    dev_user, dev_token = _make_user_with_token(client, db_session, "dev2@example.com", "developer")
    other_dev, _ = _make_user_with_token(client, db_session, "dev3@example.com", "developer")

    # Available form (developer can view even if not assigned)
    f_available = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "A", "message": "A", "budget": "1", "expected_time": "1d"},
    )
    f_available.status = "available"
    db_session.add(f_available)
    db_session.commit()
    db_session.refresh(f_available)

    resp_ok = client.get(
        f"{FORMS_BASE}/form/{f_available.id}",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_ok.status_code == 200

    # Processing form assigned to someone else → forbidden
    f_processing = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "P", "message": "P", "budget": "2", "expected_time": "2d"},
    )
    f_processing.status = "processing"
    f_processing.developer_id = other_dev.id
    db_session.add(f_processing)
    db_session.commit()
    db_session.refresh(f_processing)

    resp_forbidden = client.get(
        f"{FORMS_BASE}/form/{f_processing.id}",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_forbidden.status_code == 403


def test_list_forms_filters(client, db_session):
    client_user, client_token = _make_user_with_token(client, db_session, "listclient@example.com", "client")
    dev_user, dev_token = _make_user_with_token(client, db_session, "listdev@example.com", "developer")

    # Client owns two forms; another client's form should not appear
    f1 = form_repo.create_mainform(db_session, client_user.id, {"title": "C1", "message": "m", "budget": "b", "expected_time": "t"})
    f2 = form_repo.create_mainform(db_session, client_user.id, {"title": "C2", "message": "m", "budget": "b", "expected_time": "t"})
    other_client, _ = _make_user_with_token(client, db_session, "otherclient@example.com", "client")
    f_other = form_repo.create_mainform(db_session, other_client.id, {"title": "OC", "message": "m", "budget": "b", "expected_time": "t"})
    db_session.commit()

    resp_client = client.get(
        f"{FORMS_BASE}/forms",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp_client.status_code == 200
    forms = resp_client.json()["data"]["forms"]
    ids = {item["id"] for item in forms}
    assert f1.id in ids and f2.id in ids
    assert f_other.id not in ids

    # Developer default view: only assigned active/closed forms
    assigned = form_repo.create_mainform(db_session, client_user.id, {"title": "Assigned", "message": "m", "budget": "b", "expected_time": "t"})
    assigned.status = "processing"
    assigned.developer_id = dev_user.id
    available = form_repo.create_mainform(db_session, client_user.id, {"title": "Avail", "message": "m", "budget": "b", "expected_time": "t"})
    available.status = "available"
    db_session.add_all([assigned, available])
    db_session.commit()

    resp_dev_default = client.get(
        f"{FORMS_BASE}/forms",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_dev_default.status_code == 200
    dev_forms = resp_dev_default.json()["data"]["forms"]
    dev_ids = {item["id"] for item in dev_forms}
    assert assigned.id in dev_ids
    assert available.id not in dev_ids  # not assigned, default view excludes

    resp_dev_available = client.get(
        f"{FORMS_BASE}/forms?available_only=true",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_dev_available.status_code == 200
    dev_avail_ids = {item["id"] for item in resp_dev_available.json()["data"]["forms"]}
    assert available.id in dev_avail_ids


def test_update_status_flow_and_invalid_transition(client, db_session):
    client_user, client_token = _make_user_with_token(client, db_session, "statusclient@example.com", "client")
    dev_user, dev_token = _make_user_with_token(client, db_session, "statusdev@example.com", "developer")

    form = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "S", "message": "m", "budget": "b", "expected_time": "t"},
    )
    db_session.commit()
    db_session.refresh(form)

    # Client: preview -> available
    resp_preview_available = client.put(
        f"{FORMS_BASE}/form/{form.id}/status",
        json={"status": "available"},
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp_preview_available.status_code == 200
    db_session.refresh(form)
    assert form.status == "available"

    # Developer: available -> processing (binds developer)
    resp_dev_processing = client.put(
        f"{FORMS_BASE}/form/{form.id}/status",
        json={"status": "processing"},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_dev_processing.status_code == 200
    db_session.refresh(form)
    assert form.status == "processing"
    assert form.developer_id == dev_user.id

    # Invalid transition: preview -> rewrite should be 409
    new_form = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "Invalid", "message": "m", "budget": "b", "expected_time": "t"},
    )
    db_session.commit()
    resp_invalid = client.put(
        f"{FORMS_BASE}/form/{new_form.id}/status",
        json={"status": "rewrite"},
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp_invalid.status_code == 409


def test_delete_form_preview_only(client, db_session):
    client_user, client_token = _make_user_with_token(client, db_session, "deleteclient@example.com", "client")

    preview_form = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "Del", "message": "m", "budget": "b", "expected_time": "t"},
    )
    processing_form = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "Del2", "message": "m", "budget": "b", "expected_time": "t"},
    )
    processing_form.status = "processing"
    db_session.add(processing_form)
    db_session.commit()

    resp_delete_ok = client.delete(
        f"{FORMS_BASE}/form/{preview_form.id}",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp_delete_ok.status_code == 200
    assert form_repo.get(db_session, preview_form.id) is None

    resp_delete_conflict = client.delete(
        f"{FORMS_BASE}/form/{processing_form.id}",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp_delete_conflict.status_code == 409


def test_create_subform_and_merge(client, db_session):
    client_user, client_token = _make_user_with_token(client, db_session, "subclient@example.com", "client")
    dev_user, dev_token = _make_user_with_token(client, db_session, "subdev@example.com", "developer")

    mainform = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "Main", "message": "m", "budget": "b", "expected_time": "t"},
    )
    mainform.status = "processing"
    mainform.developer_id = dev_user.id
    db_session.add(mainform)
    db_session.commit()
    db_session.refresh(mainform)

    sub_payload = {"title": "Sub", "message": "m2", "budget": "b2", "expected_time": "t2"}
    resp_create_sub = client.post(
        f"{FORMS_BASE}/form/{mainform.id}/subform",
        json=sub_payload,
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_create_sub.status_code == 200
    subform_id = resp_create_sub.json()["data"]["subform_id"]

    # After creation, mainform should point to subform
    db_session.refresh(mainform)
    assert mainform.subform_id == subform_id
    assert mainform.status == "rewrite"

    # Client merges the subform
    resp_merge = client.post(
        f"{FORMS_BASE}/form/{mainform.id}/subform/merge",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp_merge.status_code == 200
    db_session.refresh(mainform)
    assert mainform.subform_id is None
    assert mainform.status == "processing"
