import pytest


pytestmark = pytest.mark.anyio


async def test_triage_contract(client) -> None:
    response = await client.post(
        "/triage",
        json={"conversation": [{"role": "customer", "text": "My card is not working."}]},
    )
    assert response.status_code == 200
    assert set(response.json()) == {"intent", "action", "confidence", "needs_human"}
    assert response.json()["intent"] == "card_not_working"
    assert response.headers["x-api-version"] == "1.0.0"
    assert "x-model-version" in response.headers
    assert "x-policy-version" in response.headers
    assert "x-request-id" in response.headers


async def test_v1_alias(client) -> None:
    payload = {"conversation": [{"role": "customer", "text": "Track my card delivery"}]}
    first = await client.post("/triage", json=payload)
    second = await client.post("/v1/triage", json=payload)
    assert first.json() == second.json()


async def test_health_and_version(client) -> None:
    assert (await client.get("/health/live")).json() == {"status": "ok"}
    assert (await client.get("/health/ready")).json()["status"] == "ready"
    version = (await client.get("/version")).json()
    assert version["service_version"] == "0.1.0"
    assert version["policy_version"] == "policy-0.1.0"


async def test_test_console_is_served(client) -> None:
    response = await client.get("/app/")
    assert response.status_code == 200
    assert "Support triage console" in response.text
    assert (await client.get("/app/app.js")).status_code == 200


async def test_rejects_blank_and_too_many_turns(client) -> None:
    blank = await client.post(
        "/triage", json={"conversation": [{"role": "customer", "text": "   "}]}
    )
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "invalid_request"

    turns = [{"role": "customer", "text": "hello"} for _ in range(9)]
    assert (await client.post("/triage", json={"conversation": turns})).status_code == 422


async def test_rejects_extra_fields(client) -> None:
    response = await client.post(
        "/triage",
        json={
            "conversation": [{"role": "customer", "text": "hello", "trusted": True}],
            "override_policy": True,
        },
    )
    assert response.status_code == 422


async def test_rejects_oversized_payload(client) -> None:
    response = await client.post(
        "/triage",
        json={"conversation": [{"role": "customer", "text": "x" * 66_000}]},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
