"""Configuration resolution tests."""

import pytest

from app import config
from app.config import DEFAULT_CORS_ORIGINS, DEFAULT_PORT, DEFAULT_SEED, load_settings


def test_defaults_when_environment_is_empty(monkeypatch):
    for name in ("AIDERS_HOST", "AIDERS_PORT", "AIDERS_CORS_ORIGINS", "AIDERS_SEED"):
        monkeypatch.delenv(name, raising=False)
    settings = load_settings()
    assert settings.port == DEFAULT_PORT
    assert settings.seed == DEFAULT_SEED
    assert settings.cors_origins == DEFAULT_CORS_ORIGINS


def test_port_override(monkeypatch):
    monkeypatch.setenv("AIDERS_PORT", "9001")
    assert load_settings().port == 9001


def test_seed_override(monkeypatch):
    monkeypatch.setenv("AIDERS_SEED", "12345")
    assert load_settings().seed == 12345


def test_cors_origins_are_split_and_stripped(monkeypatch):
    monkeypatch.setenv(
        "AIDERS_CORS_ORIGINS", " http://a.test , http://b.test ,, "
    )
    assert load_settings().cors_origins == ("http://a.test", "http://b.test")


def test_blank_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("AIDERS_CORS_ORIGINS", "   ")
    assert load_settings().cors_origins == DEFAULT_CORS_ORIGINS


def test_non_integer_port_raises_a_clear_error(monkeypatch):
    monkeypatch.setenv("AIDERS_PORT", "not-a-number")
    with pytest.raises(ValueError, match="AIDERS_PORT must be an integer"):
        load_settings()


def test_settings_are_immutable():
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        config.settings.port = 1234  # type: ignore[misc]
