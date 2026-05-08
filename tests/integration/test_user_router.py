from uuid import uuid4

from httpx import AsyncClient


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "username": "ada.lovelace",
        "email": "ada@example.com",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "role": "user",
    }
    base.update(overrides)
    return base


async def test_create_user_returns_201(client: AsyncClient) -> None:
    resp = await client.post("/users", json=_payload())

    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "ada.lovelace"
    assert body["email"] == "ada@example.com"
    assert "id" in body
    assert "created_at" in body


async def test_create_user_defaults_to_inactive(client: AsyncClient) -> None:
    resp = await client.post("/users", json=_payload())

    assert resp.status_code == 201
    assert resp.json()["active"] is False


async def test_create_user_rejects_invalid_email(client: AsyncClient) -> None:
    resp = await client.post("/users", json=_payload(email="not-an-email"))

    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")


async def test_create_user_conflict_on_duplicate_username(client: AsyncClient) -> None:
    await client.post("/users", json=_payload())
    resp = await client.post("/users", json=_payload(email="other@example.com"))

    assert resp.status_code == 409
    body = resp.json()
    assert body["type"].endswith("user-already-exists")


async def test_get_user_returns_404_when_missing(client: AsyncClient) -> None:
    resp = await client.get(f"/users/{uuid4()}")

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["type"].endswith("user-not-found")


async def test_get_user_returns_200_when_exists(client: AsyncClient) -> None:
    create_resp = await client.post("/users", json=_payload())
    user_id = create_resp.json()["id"]

    resp = await client.get(f"/users/{user_id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == user_id


async def test_list_users_paginates(client: AsyncClient) -> None:
    for i in range(3):
        await client.post(
            "/users",
            json=_payload(username=f"user{i}", email=f"u{i}@example.com"),
        )

    resp = await client.get("/users", params={"limit": 2, "offset": 0})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2


async def test_update_user_partial(client: AsyncClient) -> None:
    create_resp = await client.post("/users", json=_payload())
    user_id = create_resp.json()["id"]

    resp = await client.patch(f"/users/{user_id}", json={"first_name": "Augusta"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "Augusta"
    assert body["last_name"] == "Lovelace"


async def test_update_user_not_found(client: AsyncClient) -> None:
    resp = await client.patch(f"/users/{uuid4()}", json={"first_name": "X"})

    assert resp.status_code == 404


async def test_delete_user_returns_204(client: AsyncClient) -> None:
    create_resp = await client.post("/users", json=_payload())
    user_id = create_resp.json()["id"]

    resp = await client.delete(f"/users/{user_id}")
    assert resp.status_code == 204

    follow_up = await client.get(f"/users/{user_id}")
    assert follow_up.status_code == 404


async def test_activate_user_endpoint(client: AsyncClient) -> None:
    create_resp = await client.post("/users", json=_payload())
    user_id = create_resp.json()["id"]
    assert create_resp.json()["active"] is False

    resp = await client.post(f"/users/{user_id}/activate")

    assert resp.status_code == 200
    assert resp.json()["active"] is True


async def test_deactivate_user_endpoint(client: AsyncClient) -> None:
    create_resp = await client.post("/users", json=_payload())
    user_id = create_resp.json()["id"]
    await client.post(f"/users/{user_id}/activate")

    resp = await client.post(f"/users/{user_id}/deactivate")

    assert resp.status_code == 200
    assert resp.json()["active"] is False


async def test_activate_user_not_found(client: AsyncClient) -> None:
    resp = await client.post(f"/users/{uuid4()}/activate")

    assert resp.status_code == 404


async def test_list_users_filters_by_active(client: AsyncClient) -> None:
    for i in range(3):
        create_resp = await client.post(
            "/users",
            json=_payload(username=f"user{i}", email=f"u{i}@example.com"),
        )
        if i < 2:
            await client.post(f"/users/{create_resp.json()['id']}/activate")

    only_active = await client.get("/users", params={"active": "true"})
    only_inactive = await client.get("/users", params={"active": "false"})
    all_users = await client.get("/users")

    assert only_active.json()["total"] == 2
    assert only_inactive.json()["total"] == 1
    assert all_users.json()["total"] == 3
