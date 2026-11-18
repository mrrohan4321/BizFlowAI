import uuid

from tests.conftest import make_token


def test_unauthenticated_requests_rejected(client):
    for method, url in (("get", "/api/payments"), ("get", "/api/expenses"), ("get", "/api/opening-cash"),
                        ("post", "/api/payments")):
        r = getattr(client, method)(url)
        assert r.status_code == 401 and r.json()["error"]["code"] == "unauthenticated"


def test_bad_expired_and_wrong_secret_tokens_rejected(client, world):
    for tok in ("garbage", make_token(world.user_a, expired=True), make_token(world.user_a, secret="x" * 40),
                make_token(world.user_a, aud="other")):
        assert client.get("/api/payments", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_valid_user_without_business_is_forbidden(client, world):
    h = {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}
    r = client.get("/api/payments", headers=h)
    assert r.status_code == 403 and r.json()["error"]["code"] == "no_business_access"


def test_business_header_cannot_grant_access_to_other_business(client, world):
    r = client.get("/api/payments", headers={**world.h_a, "X-Business-Id": world.biz_b})
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden_business"


def test_malformed_business_header(client, world):
    assert client.get("/api/payments", headers={**world.h_a, "X-Business-Id": "nope"}).status_code == 400


def test_own_business_header_allowed(client, world):
    assert client.get("/api/payments", headers={**world.h_a, "X-Business-Id": world.biz_a}).status_code == 200


def test_health_is_public(client):
    assert client.get("/api/health").status_code == 200
