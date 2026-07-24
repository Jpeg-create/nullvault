import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def unique_name(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def get_user_token(username="projectowner", email="projectowner@example.com", password="testpassword123"):
    client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    response = client.post("/auth/login", data={
        "username": username,
        "password": password,
    })
    assert response.status_code == 200
    return response.json()["access_token"]


def create_project(token, name=None):
    name = name or unique_name("project")
    response = client.post(
        "/projects/",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return name


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register():
    response = client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    })
    assert response.status_code in [201, 400]


def test_login():
    client.post("/auth/register", json={
        "username": "loginuser",
        "email": "login@example.com",
        "password": "testpassword123"
    })
    response = client.post("/auth/login", data={
        "username": "loginuser",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_secrets_require_auth():
    response = client.get("/secrets/")
    assert response.status_code == 401


def test_audit_requires_auth():
    response = client.get("/audit/")
    assert response.status_code == 401


def test_create_project():
    token = get_user_token()
    name = unique_name("project")
    response = client.post(
        "/projects/",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == name


def test_duplicate_project_rejected():
    token = get_user_token()
    name = create_project(token)
    response = client.post(
        "/projects/",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


def test_secret_requires_project_field():
    token = get_user_token()
    response = client.post(
        "/secrets/",
        json={"name": "some-secret", "value": "some-value"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_secret_lifecycle_within_project():
    token = get_user_token()
    project = create_project(token)
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/secrets/",
        json={"project": project, "name": "api-key", "value": "super-secret-value"},
        headers=headers,
    )
    assert create.status_code == 201
    assert create.json()["project"] == project

    read = client.get(f"/secrets/{project}/api-key", headers=headers)
    assert read.status_code == 200
    assert read.json()["value"] == "super-secret-value"

    listing = client.get(f"/secrets/?project={project}", headers=headers)
    assert listing.status_code == 200
    names = [s["name"] for s in listing.json()]
    assert "api-key" in names

    audit = client.get(f"/audit/?project={project}", headers=headers)
    assert audit.status_code == 200
    actions = [entry["action"] for entry in audit.json()]
    assert "CREATE" in actions
    assert "READ" in actions
    assert all(entry["project_name"] == project for entry in audit.json())

    delete = client.delete(f"/secrets/{project}/api-key", headers=headers)
    assert delete.status_code == 204

    missing = client.get(f"/secrets/{project}/api-key", headers=headers)
    assert missing.status_code == 404


def test_get_secret_requires_matching_project():
    token = get_user_token()
    project = create_project(token)
    headers = {"Authorization": f"Bearer {token}"}
    client.post(
        "/secrets/",
        json={"project": project, "name": "db-password", "value": "hunter2"},
        headers=headers,
    )

    other_project = unique_name("other-project")
    response = client.get(f"/secrets/{other_project}/db-password", headers=headers)
    assert response.status_code == 404


def test_list_secrets_filtered_by_project():
    token = get_user_token()
    project_a = create_project(token)
    project_b = create_project(token)
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/secrets/", json={"project": project_a, "name": "shared-name", "value": "a-value"}, headers=headers)
    client.post("/secrets/", json={"project": project_b, "name": "shared-name", "value": "b-value"}, headers=headers)

    only_a = client.get(f"/secrets/?project={project_a}", headers=headers).json()
    assert len(only_a) == 1
    assert only_a[0]["project"] == project_a

    both = client.get("/secrets/", headers=headers).json()
    project_names = {s["project"] for s in both}
    assert project_a in project_names
    assert project_b in project_names


def test_project_token_can_only_access_its_own_project():
    token = get_user_token()
    project_a = create_project(token)
    project_b = create_project(token)
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/secrets/", json={"project": project_a, "name": "only-in-a", "value": "value-a"}, headers=headers)
    client.post("/secrets/", json={"project": project_b, "name": "only-in-b", "value": "value-b"}, headers=headers)

    token_response = client.post(f"/projects/{project_a}/token", headers=headers)
    assert token_response.status_code == 200
    project_token = token_response.json()["access_token"]
    project_headers = {"Authorization": f"Bearer {project_token}"}

    own_project = client.get(f"/secrets/{project_a}/only-in-a", headers=project_headers)
    assert own_project.status_code == 200
    assert own_project.json()["value"] == "value-a"

    other_project = client.get(f"/secrets/{project_b}/only-in-b", headers=project_headers)
    assert other_project.status_code == 403

    listing = client.get("/secrets/", headers=project_headers).json()
    project_names = {s["project"] for s in listing}
    assert project_names == {project_a}


def test_project_token_cannot_manage_projects():
    token = get_user_token()
    project_a = create_project(token)
    headers = {"Authorization": f"Bearer {token}"}

    token_response = client.post(f"/projects/{project_a}/token", headers=headers)
    project_token = token_response.json()["access_token"]
    project_headers = {"Authorization": f"Bearer {project_token}"}

    create_attempt = client.post("/projects/", json={"name": unique_name("blocked")}, headers=project_headers)
    assert create_attempt.status_code == 403

    list_attempt = client.get("/projects/", headers=project_headers)
    assert list_attempt.status_code == 403
