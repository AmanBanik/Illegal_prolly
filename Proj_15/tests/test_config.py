import os
import pytest
from Proj_15.src.config import PasswordResetConfig
from Proj_15.src.exceptions import ConfigurationError


def test_default_config():
    cfg = PasswordResetConfig()
    assert cfg.expiration_seconds == 30.0
    assert cfg.code_length == 6
    assert cfg.auth_base_url == "https://auth.example.com"
    assert cfg.min_password_length == 8


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("TEST_AUTH_BASE_URL", "https://identity.company.org/sso")
    monkeypatch.setenv("TEST_EXPIRATION_SECONDS", "30.0")
    monkeypatch.setenv("TEST_CODE_LENGTH", "8")
    monkeypatch.setenv("TEST_MIN_PASSWORD_LENGTH", "10")

    cfg = PasswordResetConfig.from_env(env_prefix="TEST_")
    assert cfg.auth_base_url == "https://identity.company.org/sso"
    assert cfg.expiration_seconds == 30.0
    assert cfg.code_length == 8
    assert cfg.min_password_length == 10


def test_config_invalid_env_values(monkeypatch):
    monkeypatch.setenv("ERR_EXPIRATION_SECONDS", "not_a_number")
    with pytest.raises(ConfigurationError):
        PasswordResetConfig.from_env(env_prefix="ERR_")


def test_config_immutability():
    cfg = PasswordResetConfig()
    with pytest.raises(Exception):  # FrozenInstanceError
        cfg.expiration_seconds = 60.0
