import pytest

from app.database import _get_postgres_password


def test_development_database_password_fallback_is_available(monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setenv("APP_ENV", "development")

    assert _get_postgres_password() == "dev_password_change_me"


def test_production_requires_explicit_database_password(monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(ValueError, match="POSTGRES_PASSWORD is required"):
        _get_postgres_password()


def test_staging_rejects_blank_database_password(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", " ")
    monkeypatch.setenv("APP_ENV", "staging")

    with pytest.raises(ValueError, match="POSTGRES_PASSWORD is required"):
        _get_postgres_password()


def test_explicit_password_is_used_in_any_environment(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "local-test-secret")
    monkeypatch.setenv("APP_ENV", "production")

    assert _get_postgres_password() == "local-test-secret"
