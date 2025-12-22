from app.models import Form
from app.repositories import forms as form_repo, nonfunctions as nonfunction_repo
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


def test_list_nonfunctions_permission(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "nf-owner@example.com", "client")
    other, other_token = _make_user_with_token(client, db_session, "nf-other@example.com", "client")

    form = form_repo.create_mainform(
        db_session,
        owner.id,
        {"title": "FormNF", "message": "M", "budget": "B", "expected_time": "T"},
    )
    nf = nonfunction_repo.create(
        db_session,
        {"form_id": form.id, "name": "NF1", "level": "lightweight", "description": "D1", "status": "preview"},
    )

    resp_ok = client.get(
        f"{API_BASE}/nonfunctions?form_id={form.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_ok.status_code == 200
    items = resp_ok.json()["data"]["nonfunctions"]
    assert any(i["id"] == nf.id for i in items)

    resp_forbidden = client.get(
        f"{API_BASE}/nonfunctions?form_id={form.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp_forbidden.status_code == 403


def test_create_nonfunction_client_success(client, db_session):
    owner, token = _make_user_with_token(client, db_session, "nf-client@example.com", "client")
    form = form_repo.create_mainform(
        db_session,
        owner.id,
        {"title": "FormNF2", "message": "M", "budget": "B", "expected_time": "T"},
    )
    payload = {
        "form_id": form.id,
        "name": "NF-New",
        "level": "lightweight",
        "description": "Desc",
        "status": "preview",
    }
    resp = client.post(
        f"{API_BASE}/nonfunction",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    nf_id = resp.json()["data"]["id"]
    nf = nonfunction_repo.get_by_id(db_session, nf_id)
    assert nf is not None and nf.name == "NF-New"


def test_create_nonfunction_developer_unassigned_forbidden(client, db_session):
    client_user, _ = _make_user_with_token(client, db_session, "nf-cl2@example.com", "client")
    dev_user, dev_token = _make_user_with_token(client, db_session, "nf-dev@example.com", "developer")

    form = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "FormNF3", "message": "M", "budget": "B", "expected_time": "T"},
    )
    form.status = "processing"
    db_session.add(form)
    db_session.commit()

    payload = {
        "form_id": form.id,
        "name": "NF-Forbidden",
        "level": "commercial",
        "description": "Desc",
        "status": "preview",
    }
    resp = client.post(
        f"{API_BASE}/nonfunction",
        json=payload,
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp.status_code == 403


def test_update_nonfunction_conflict_and_developer_success(client, db_session):
    client_user, client_token = _make_user_with_token(client, db_session, "nf-cl3@example.com", "client")
    dev_user, dev_token = _make_user_with_token(client, db_session, "nf-dev2@example.com", "developer")

    form = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "FormNF4", "message": "M", "budget": "B", "expected_time": "T"},
    )
    form.status = "processing"
    form.developer_id = dev_user.id
    db_session.add(form)
    db_session.commit()
    db_session.refresh(form)

    nf = nonfunction_repo.create(
        db_session,
        {"form_id": form.id, "name": "NFUpd", "level": "enterprise", "description": "Old", "status": "preview"},
    )

    # Client cannot edit when status processing
    resp_conflict = client.put(
        f"{API_BASE}/nonfunction/{nf.id}",
        json={"description": "New"},
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp_conflict.status_code == 409

    # Assigned developer can edit
    resp_dev = client.put(
        f"{API_BASE}/nonfunction/{nf.id}",
        json={"description": "New", "status": "available"},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_dev.status_code == 200
    db_session.refresh(nf)
    assert nf.description == "New"
    assert nf.status == "available"


def test_update_nonfunction_no_changes_and_not_found(client, db_session):
    owner, token = _make_user_with_token(client, db_session, "nf-nc@example.com", "client")
    form = form_repo.create_mainform(
        db_session,
        owner.id,
        {"title": "FormNFNC", "message": "M", "budget": "B", "expected_time": "T"},
    )
    nf = nonfunction_repo.create(
        db_session,
        {"form_id": form.id, "name": "NFNC", "level": "enterprise", "description": "Old", "status": "preview"},
    )
    resp_no_changes = client.put(
        f"{API_BASE}/nonfunction/{nf.id}",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_no_changes.status_code == 400

    resp_not_found = client.put(
        f"{API_BASE}/nonfunction/9999",
        json={"description": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_not_found.status_code == 404


def test_create_nonfunction_form_not_found(client, db_session):
    user, token = _make_user_with_token(client, db_session, "nf-nf@example.com", "client")
    payload = {
        "form_id": 9999,
        "name": "NFMissing",
        "level": "lightweight",
        "description": "Desc",
        "status": "preview",
    }
    resp = client.post(
        f"{API_BASE}/nonfunction",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_delete_nonfunction_subform_only_creator(client, db_session):
    creator, creator_token = _make_user_with_token(client, db_session, "nf-subcreator@example.com", "developer")
    other, other_token = _make_user_with_token(client, db_session, "nf-subother@example.com", "developer")

    subform = Form(
        type="subform",
        user_id=creator.id,
        developer_id=creator.id,
        created_by=creator.id,
        title="SubFormNF",
        message="m",
        budget="b",
        expected_time="t",
        status="rewrite",
    )
    db_session.add(subform)
    db_session.commit()
    db_session.refresh(subform)

    nf = nonfunction_repo.create(
        db_session,
        {"form_id": subform.id, "name": "NFSub", "level": "lightweight", "description": "d", "status": "preview"},
    )

    resp_forbidden = client.delete(
        f"{API_BASE}/nonfunction/{nf.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp_forbidden.status_code == 403

    resp_ok = client.delete(
        f"{API_BASE}/nonfunction/{nf.id}",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp_ok.status_code == 200
    assert nonfunction_repo.get_by_id(db_session, nf.id) is None
