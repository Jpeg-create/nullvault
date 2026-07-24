import json
import urllib.error

import pytest

import client as nullvault_client


class FakeResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def test_get_secret_returns_value(monkeypatch):
    def fake_urlopen(request, timeout=10):
        assert request.full_url == "http://127.0.0.1:8100/secrets/acme-app/db-password"
        assert request.get_header("Authorization") == "Bearer test-token"
        return FakeResponse({"project": "acme-app", "name": "db-password", "value": "hunter2"})

    monkeypatch.setattr(nullvault_client.urllib.request, "urlopen", fake_urlopen)
    value = nullvault_client.get_secret("acme-app", "db-password", token="test-token")
    assert value == "hunter2"


def test_get_secret_uses_custom_base_url(monkeypatch):
    def fake_urlopen(request, timeout=10):
        assert request.full_url == "https://vault.example.com/secrets/acme-app/db-password"
        return FakeResponse({"value": "hunter2"})

    monkeypatch.setattr(nullvault_client.urllib.request, "urlopen", fake_urlopen)
    value = nullvault_client.get_secret(
        "acme-app", "db-password", token="test-token", base_url="https://vault.example.com/"
    )
    assert value == "hunter2"


def test_get_secret_missing_token_raises(monkeypatch):
    monkeypatch.delenv("NULLVAULT_TOKEN", raising=False)
    with pytest.raises(nullvault_client.NullVaultError):
        nullvault_client.get_secret("acme-app", "db-password")


def test_get_secret_reads_token_from_env(monkeypatch):
    monkeypatch.setenv("NULLVAULT_TOKEN", "env-token")

    def fake_urlopen(request, timeout=10):
        assert request.get_header("Authorization") == "Bearer env-token"
        return FakeResponse({"value": "from-env"})

    monkeypatch.setattr(nullvault_client.urllib.request, "urlopen", fake_urlopen)
    assert nullvault_client.get_secret("acme-app", "db-password") == "from-env"


def test_get_secret_reads_base_url_from_env(monkeypatch):
    monkeypatch.setenv("NULLVAULT_URL", "https://vault.example.com")

    def fake_urlopen(request, timeout=10):
        assert request.full_url == "https://vault.example.com/secrets/acme-app/db-password"
        return FakeResponse({"value": "hunter2"})

    monkeypatch.setattr(nullvault_client.urllib.request, "urlopen", fake_urlopen)
    nullvault_client.get_secret("acme-app", "db-password", token="test-token")


def test_get_secret_http_error_raises_nullvault_error(monkeypatch):
    def fake_urlopen(request, timeout=10):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", hdrs=None, fp=None)

    monkeypatch.setattr(nullvault_client.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(nullvault_client.NullVaultError):
        nullvault_client.get_secret("acme-app", "missing-key", token="test-token")


def test_get_secret_connection_error_raises_nullvault_error(monkeypatch):
    def fake_urlopen(request, timeout=10):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(nullvault_client.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(nullvault_client.NullVaultError):
        nullvault_client.get_secret("acme-app", "db-password", token="test-token")
