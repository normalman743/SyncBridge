from app.models import Form
from app.repositories import forms as form_repo, functions as function_repo
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


def test_list_functions_permission(client, db_session):
    owner, owner_token = _make_user_with_token(client, db_session, "fn-owner@example.com", "client")
    other, other_token = _make_user_with_token(client, db_session, "fn-other@example.com", "client")

    form = form_repo.create_mainform(
        db_session,
        owner.id,
        {"title": "Form1", "message": "M", "budget": "B", "expected_time": "T"},
    )
    fn = function_repo.create(
        db_session,
        {"form_id": form.id, "name": "F1", "choice": "lightweight", "description": "D1", "status": "preview"},
    )

    resp_ok = client.get(
        f"{API_BASE}/functions?form_id={form.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_ok.status_code == 200
    data = resp_ok.json()["data"]["functions"]
    assert any(item["id"] == fn.id for item in data)

    resp_forbidden = client.get(
        f"{API_BASE}/functions?form_id={form.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp_forbidden.status_code == 403


def test_create_function_client_success(client, db_session):
    owner, token = _make_user_with_token(client, db_session, "fn-client@example.com", "client")
    form = form_repo.create_mainform(
        db_session,
        owner.id,
        {"title": "Form2", "message": "M", "budget": "B", "expected_time": "T"},
    )
    payload = {
        "form_id": form.id,
        "name": "NewFn",
        "choice": "lightweight",
        "description": "Desc",
        "status": "preview",
    }
    resp = client.post(
        f"{API_BASE}/function",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    fn_id = resp.json()["data"]["id"]
    fn = function_repo.get_by_id(db_session, fn_id)
    assert fn is not None and fn.name == "NewFn"


def test_create_function_developer_unassigned_processing_forbidden(client, db_session):
    client_user, _ = _make_user_with_token(client, db_session, "fn-cl2@example.com", "client")
    dev_user, dev_token = _make_user_with_token(client, db_session, "fn-dev@example.com", "developer")

    form = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "Form3", "message": "M", "budget": "B", "expected_time": "T"},
    )
    form.status = "processing"
    db_session.add(form)
    db_session.commit()

    payload = {
        "form_id": form.id,
        "name": "FnForbidden",
        "choice": "commercial",
        "description": "Desc",
        "status": "preview",
    }
    resp = client.post(
        f"{API_BASE}/function",
        json=payload,
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp.status_code == 403


def test_update_function_conflict_and_developer_success(client, db_session):
    client_user, client_token = _make_user_with_token(client, db_session, "fn-cl3@example.com", "client")
    dev_user, dev_token = _make_user_with_token(client, db_session, "fn-dev2@example.com", "developer")

    # Form in processing assigned to developer
    form = form_repo.create_mainform(
        db_session,
        client_user.id,
        {"title": "Form4", "message": "M", "budget": "B", "expected_time": "T"},
    )
    form.status = "processing"
    form.developer_id = dev_user.id
    db_session.add(form)
    db_session.commit()
    db_session.refresh(form)

    fn = function_repo.create(
        db_session,
        {"form_id": form.id, "name": "FnUpd", "choice": "enterprise", "description": "Old", "status": "preview"},
    )

    # Client cannot edit when status processing -> 409
    resp_conflict = client.put(
        f"{API_BASE}/function/{fn.id}",
        json={"description": "New"},
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp_conflict.status_code == 409

    # Assigned developer can edit
    resp_dev = client.put(
        f"{API_BASE}/function/{fn.id}",
        json={"description": "New", "status": "available"},
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp_dev.status_code == 200
    db_session.refresh(fn)
    assert fn.description == "New"
    assert fn.status == "available"


def test_update_function_no_changes_and_not_found(client, db_session):
    owner, token = _make_user_with_token(client, db_session, "fn-nc@example.com", "client")
    form = form_repo.create_mainform(
        db_session,
        owner.id,
        {"title": "FormNC", "message": "M", "budget": "B", "expected_time": "T"},
    )
    fn = function_repo.create(
        db_session,
        {"form_id": form.id, "name": "FnNC", "choice": "enterprise", "description": "Old", "status": "preview"},
    )
    resp_no_changes = client.put(
        f"{API_BASE}/function/{fn.id}",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_no_changes.status_code == 400

    resp_not_found = client.put(
        f"{API_BASE}/function/9999",
        json={"description": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_not_found.status_code == 404


def test_create_function_form_not_found(client, db_session):
    user, token = _make_user_with_token(client, db_session, "fn-nf@example.com", "client")
    payload = {
        "form_id": 9999,
        "name": "FnMissing",
        "choice": "lightweight",
        "description": "Desc",
        "status": "preview",
    }
    resp = client.post(
        f"{API_BASE}/function",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_delete_function_subform_only_creator(client, db_session):
    creator, creator_token = _make_user_with_token(client, db_session, "fn-subcreator@example.com", "developer")
    other, other_token = _make_user_with_token(client, db_session, "fn-subother@example.com", "developer")

    # Build a subform directly
    subform = Form(
        type="subform",
        user_id=creator.id,
        developer_id=creator.id,
        created_by=creator.id,
        title="SubForm",
        message="m",
        budget="b",
        expected_time="t",
        status="rewrite",
    )
    db_session.add(subform)
    db_session.commit()
    db_session.refresh(subform)

    fn = function_repo.create(
        db_session,
        {"form_id": subform.id, "name": "FnSub", "choice": "lightweight", "description": "d", "status": "preview"},
    )

    resp_forbidden = client.delete(
        f"{API_BASE}/function/{fn.id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert resp_forbidden.status_code == 403

    resp_ok = client.delete(
        f"{API_BASE}/function/{fn.id}",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert resp_ok.status_code == 200
    assert function_repo.get_by_id(db_session, fn.id) is None
