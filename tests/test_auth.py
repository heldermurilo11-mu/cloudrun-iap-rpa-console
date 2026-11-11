"""
Testes de Autenticação, Proteção IAP, Headers de Segurança e Rejeição de Mutações.
"""
import time
import jwt
import json
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from orchestrator import auth
from orchestrator.config import settings

TEST_IAP_AUDIENCE = "/projects/000000000000/locations/us-central1/services/rpa-console-test"


def test_security_headers_present(client):
    """Verifica se os cabeçalhos de segurança e CSP estão ativos em todas as respostas."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")


def test_local_auth_mode_returns_authenticated_user(client, monkeypatch):
    """Verifica se no modo local o usuário de desenvolvimento é injetado corretamente."""
    monkeypatch.setattr(settings, "AUTH_MODE", "local")
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    resp = client.get("/api/datapools")
    assert resp.status_code == 200


def test_local_auth_mode_blocked_in_production(client, monkeypatch):
    """Garante que o bypass local é estritamente bloqueado com 403 em ambiente de produção."""
    monkeypatch.setattr(settings, "AUTH_MODE", "local")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    resp = client.get("/api/datapools")
    assert resp.status_code == 403
    assert "não permitido em ambiente de produção" in resp.json()["detail"]


def test_iap_auth_mode_blocks_missing_jwt_header(client, monkeypatch):
    """Verifica se no modo IAP qualquer requisição sem o token assinado é rejeitada com 401."""
    monkeypatch.setattr(settings, "AUTH_MODE", "iap")
    resp = client.get("/api/datapools")
    assert resp.status_code == 401
    assert "X-Goog-IAP-JWT-Assertion" in resp.json()["detail"]


def test_iap_auth_mode_invalid_jwt_rejected(client, monkeypatch):
    """Verifica se token IAP malformado ou com kid inexistente é rejeitado com 401."""
    monkeypatch.setattr(settings, "AUTH_MODE", "iap")
    monkeypatch.setattr(settings, "IAP_EXPECTED_AUDIENCE", TEST_IAP_AUDIENCE)
    headers = {"X-Goog-IAP-JWT-Assertion": "invalid.jwt.token"}
    resp = client.get("/api/datapools", headers=headers)
    assert resp.status_code == 401


def test_iap_auth_mode_expired_jwt_rejected(client, monkeypatch):
    """Verifica se token IAP expirado é rejeitado com 401."""
    monkeypatch.setattr(settings, "AUTH_MODE", "iap")
    monkeypatch.setattr(settings, "IAP_EXPECTED_AUDIENCE", TEST_IAP_AUDIENCE)
    monkeypatch.setattr(settings, "IAP_ALLOWED_DOMAINS", ["example.com"])
    private_key = ec.generate_private_key(ec.SECP256R1())
    key = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key()))
    key["kid"] = "mock_kid"
    monkeypatch.setattr(auth, "get_iap_public_keys", lambda **kwargs: {"keys": [key]})
    expired_token = jwt.encode(
        {"sub": "123", "email": "dev@example.com", "exp": int(time.time()) - 3600,
         "iat": int(time.time()) - 3900, "iss": "https://cloud.google.com/iap",
         "aud": TEST_IAP_AUDIENCE},
        private_key,
        algorithm="ES256",
        headers={"kid": "mock_kid"}
    )
    headers = {"X-Goog-IAP-JWT-Assertion": expired_token}
    resp = client.get("/api/datapools", headers=headers)
    assert resp.status_code == 401


@pytest.fixture
def iap_signer(monkeypatch):
    monkeypatch.setattr(settings, "IAP_EXPECTED_AUDIENCE", TEST_IAP_AUDIENCE)
    monkeypatch.setattr(settings, "IAP_ALLOWED_DOMAINS", ["example.com"])
    monkeypatch.setattr(settings, "IAP_ADMIN_EMAILS", ["admin@example.com"])

    private_key = ec.generate_private_key(ec.SECP256R1())
    key = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key()))
    key["kid"] = "local-test-key"
    monkeypatch.setattr(auth, "_IAP_KEYS_CACHE", {"keys": [key]})
    monkeypatch.setattr(auth, "_IAP_KEYS_LAST_FETCH", time.time())

    def sign(**changes):
        claims = {"sub": "test-subject", "email": "dev@example.com",
                  "iss": "https://cloud.google.com/iap", "aud": TEST_IAP_AUDIENCE,
                  "iat": int(time.time()), "exp": int(time.time()) + 300}
        claims.update(changes)
        claims = {name: value for name, value in claims.items() if value is not None}
        return jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": key["kid"]})
    return sign


def test_valid_iap_ecdsa_signature_is_accepted(client, monkeypatch, iap_signer):
    monkeypatch.setattr(settings, "AUTH_MODE", "iap")
    response = client.get("/api/datapools", headers={"X-Goog-IAP-JWT-Assertion": iap_signer()})
    assert response.status_code == 200


def test_iap_mode_missing_audience_returns_503(client, monkeypatch, iap_signer):
    token = iap_signer()
    monkeypatch.setattr(settings, "AUTH_MODE", "iap")
    monkeypatch.setattr(settings, "IAP_EXPECTED_AUDIENCE", "")
    response = client.get("/api/datapools", headers={"X-Goog-IAP-JWT-Assertion": token})
    assert response.status_code == 503


def test_iap_empty_allowed_domains_fails_closed_with_403(client, monkeypatch, iap_signer):
    monkeypatch.setattr(settings, "AUTH_MODE", "iap")
    monkeypatch.setattr(settings, "IAP_ALLOWED_DOMAINS", [])
    response = client.get("/api/datapools", headers={"X-Goog-IAP-JWT-Assertion": iap_signer()})
    assert response.status_code == 403


@pytest.mark.parametrize("bad_email", [
    "user@unauthorized.org",
    "user@evil-example.com",
    "user@sub.example.com",
    "@example.com",
    "invalid-email",
])
def test_iap_unauthorized_domain_returns_403(client, monkeypatch, iap_signer, bad_email):
    monkeypatch.setattr(settings, "AUTH_MODE", "iap")
    monkeypatch.setattr(settings, "IAP_ALLOWED_DOMAINS", ["example.com"])
    response = client.get("/api/datapools", headers={"X-Goog-IAP-JWT-Assertion": iap_signer(email=bad_email)})
    assert response.status_code == 403


def test_iap_admin_vs_operator_role_assignment(client, monkeypatch, iap_signer):
    monkeypatch.setattr(settings, "AUTH_MODE", "iap")
    monkeypatch.setattr(settings, "IAP_ALLOWED_DOMAINS", ["example.com"])
    monkeypatch.setattr(settings, "IAP_ADMIN_EMAILS", ["admin@example.com"])

    admin_resp = client.get(
        "/api/me",
        headers={"X-Goog-IAP-JWT-Assertion": iap_signer(email="Admin@Example.com")},
    )
    assert admin_resp.status_code == 200
    assert admin_resp.json()["email"] == "admin@example.com"
    assert admin_resp.json()["role"] == "admin"

    operator_resp = client.get(
        "/api/me",
        headers={"X-Goog-IAP-JWT-Assertion": iap_signer(email="operator@example.com")},
    )
    assert operator_resp.status_code == 200
    assert operator_resp.json()["email"] == "operator@example.com"
    assert operator_resp.json()["role"] == "operator"


@pytest.mark.parametrize("changes", [
    {"aud": "another-service"}, {"aud": None}, {"iss": "https://attacker.invalid"},
    {"exp": None}, {"iat": None}, {"sub": None}, {"email": None}, {"email": []},
    {"iat": int(time.time()) + 120}, {"exp": int(time.time()) + 1000},
    {"aud": [TEST_IAP_AUDIENCE]}, {"iat": True},
    {"exp": float("inf")}, {"iat": float("nan")}, {"exp": []},
])
def test_invalid_iap_claims_rejected(iap_signer, changes):
    with pytest.raises(auth.HTTPException) as error:
        auth.validate_iap_jwt(iap_signer(**changes), settings.IAP_EXPECTED_AUDIENCE)
    assert error.value.status_code == 401


def test_forged_signature_rejected(iap_signer):
    claims = jwt.decode(iap_signer(), options={"verify_signature": False})
    forged = jwt.encode(claims, ec.generate_private_key(ec.SECP256R1()), algorithm="ES256",
                        headers={"kid": "local-test-key"})
    with pytest.raises(auth.HTTPException) as error:
        auth.validate_iap_jwt(forged, settings.IAP_EXPECTED_AUDIENCE)
    assert error.value.status_code == 401


def test_unknown_key_rejected_without_repeated_refresh(monkeypatch, iap_signer):
    token = iap_signer()
    claims = jwt.decode(token, options={"verify_signature": False})
    token = jwt.encode(claims, ec.generate_private_key(ec.SECP256R1()), algorithm="ES256",
                       headers={"kid": "unknown-key"})
    def unexpected_fetch(*args, **kwargs):
        pytest.fail("Unknown keys must not repeatedly bypass the refresh cooldown")
    monkeypatch.setattr(auth.requests, "get", unexpected_fetch)
    with pytest.raises(auth.HTTPException) as error:
        auth.validate_iap_jwt(token, settings.IAP_EXPECTED_AUDIENCE)
    assert error.value.status_code == 401


def test_missing_audience_fails_closed(iap_signer):
    with pytest.raises(auth.HTTPException) as error:
        auth.validate_iap_jwt(iap_signer(), "")
    assert error.value.status_code == 503


@pytest.mark.parametrize("expired_cache", [False, True])
def test_key_outage_returns_503_without_trusting_stale_cache(monkeypatch, iap_signer, expired_cache):
    token = iap_signer()
    if not expired_cache:
        monkeypatch.setattr(auth, "_IAP_KEYS_CACHE", {})
    monkeypatch.setattr(auth, "_IAP_KEYS_LAST_FETCH", time.time() - 7200)
    def outage(*args, **kwargs):
        raise auth.requests.ConnectionError("synthetic failure")
    monkeypatch.setattr(auth.requests, "get", outage)
    with pytest.raises(auth.HTTPException) as error:
        auth.validate_iap_jwt(token, settings.IAP_EXPECTED_AUDIENCE)
    assert error.value.status_code == 503
    assert "synthetic" not in error.value.detail


def test_rotated_key_refreshes_once(monkeypatch, iap_signer):
    token = iap_signer()
    keys = auth._IAP_KEYS_CACHE
    monkeypatch.setattr(auth, "_IAP_KEYS_CACHE", {"keys": [dict(keys["keys"][0], kid="old-key")]})
    monkeypatch.setattr(auth, "_IAP_KEYS_LAST_FETCH", time.time() - 120)
    from unittest.mock import Mock
    response = Mock()
    response.json.return_value = keys
    fetch = Mock(return_value=response)
    monkeypatch.setattr(auth.requests, "get", fetch)
    assert auth.validate_iap_jwt(token, settings.IAP_EXPECTED_AUDIENCE)["sub"] == "test-subject"
    assert auth.validate_iap_jwt(token, settings.IAP_EXPECTED_AUDIENCE)["sub"] == "test-subject"
    assert fetch.call_count == 1


@pytest.mark.parametrize("keys", [{}, {"keys": []}, {"keys": [None]},
                                    {"keys": [{"kid": "bad", "kty": "RSA"}]},
                                    {"keys": [{"kid": "bad", "kty": "EC", "crv": "P-256"}]}])
def test_invalid_provider_keys_fail_closed(monkeypatch, keys):
    from unittest.mock import Mock
    monkeypatch.setattr(auth, "_IAP_KEYS_CACHE", {})
    response = Mock()
    response.json.return_value = keys
    monkeypatch.setattr(auth.requests, "get", Mock(return_value=response))
    with pytest.raises(auth.HTTPException) as error:
        auth.get_iap_public_keys()
    assert error.value.status_code == 503


def test_non_ecdsa_algorithm_rejected_before_key_fetch(monkeypatch, iap_signer):
    from unittest.mock import Mock
    fetch = Mock()
    monkeypatch.setattr(auth, "get_iap_public_keys", fetch)
    token = jwt.encode({"sub": "synthetic"}, "synthetic-test-key-not-a-secret" * 2,
                       algorithm="HS256", headers={"kid": "unknown-key"})
    with pytest.raises(auth.HTTPException) as error:
        auth.validate_iap_jwt(token, settings.IAP_EXPECTED_AUDIENCE)
    assert error.value.status_code == 401
    fetch.assert_not_called()


def test_clock_skew_within_30_seconds_is_accepted(iap_signer):
    token = iap_signer(iat=int(time.time()) - 300, exp=int(time.time()) - 15)
    assert auth.validate_iap_jwt(token, settings.IAP_EXPECTED_AUDIENCE)["sub"] == "test-subject"


def test_expiration_outside_skew_rejected(iap_signer):
    token = iap_signer(iat=int(time.time()) - 300, exp=int(time.time()) - 60)
    with pytest.raises(auth.HTTPException) as error:
        auth.validate_iap_jwt(token, settings.IAP_EXPECTED_AUDIENCE)
    assert error.value.status_code == 401


@pytest.mark.parametrize("status_code", [404, 500])
def test_key_http_failure_is_service_unavailable(monkeypatch, status_code):
    from unittest.mock import Mock
    monkeypatch.setattr(auth, "_IAP_KEYS_CACHE", {})
    response = Mock()
    response.raise_for_status.side_effect = auth.requests.HTTPError(str(status_code))
    monkeypatch.setattr(auth.requests, "get", Mock(return_value=response))
    with pytest.raises(auth.HTTPException) as error:
        auth.get_iap_public_keys()
    assert error.value.status_code == 503


def test_mutation_methods_rejected_with_405(client, monkeypatch):
    """Garante que nenhum endpoint aceita métodos de mutação (POST, PUT, DELETE, PATCH)."""
    monkeypatch.setattr(settings, "AUTH_MODE", "local")
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")

    endpoints = [
        "/api/me",
        "/api/datapools",
        "/api/datapools/summary",
        "/api/jobs",
        "/api/schedulers",
        "/api/logs",
        "/api/audit"
    ]
    for ep in endpoints:
        assert client.post(ep, json={"test": "mutate"}).status_code == 405
        assert client.put(ep, json={"test": "mutate"}).status_code == 405
        assert client.delete(ep).status_code == 405
        assert client.patch(ep, json={"test": "mutate"}).status_code == 405
