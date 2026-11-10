import pytest

from analytics_cloud_lab.config import SnowflakeSettings


def test_from_env_requires_account(monkeypatch):
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
    monkeypatch.delenv("SNOWFLAKE_USER", raising=False)
    with pytest.raises(RuntimeError):
        SnowflakeSettings.from_env()


def test_key_pair_takes_priority(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "abc-123")
    monkeypatch.setenv("SNOWFLAKE_USER", "dens")
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "secret")
    monkeypatch.setenv("SNOWFLAKE_PRIVATE_KEY_FILE", "/keys/rsa_key.p8")
    kwargs = SnowflakeSettings.from_env().as_connector_kwargs()
    assert kwargs["private_key_file"] == "/keys/rsa_key.p8"
    assert "password" not in kwargs


def test_password_not_in_repr(monkeypatch):
    s = SnowflakeSettings(account="a", user="u", password="secret")
    assert "secret" not in repr(s)
