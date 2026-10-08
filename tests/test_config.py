import pytest

from app.config import Settings, DEFAULT_SETTINGS


def make_env(tmp_path, content):
    env_file = tmp_path / ".env"
    env_file.write_text(content, encoding="utf-8")
    return Settings(env_path=env_file, config_path=tmp_path / "missing.yaml")


class TestSettings:
    def test_defaults_when_no_env(self, tmp_path):
        settings = Settings(env_path=tmp_path / "missing.env", config_path=tmp_path / "missing.yaml")
        assert settings.headless is False
        assert settings.default_limit == 100
        assert settings.retry_attempts == 3

    def test_env_values_are_coerced(self, tmp_path):
        settings = make_env(
            tmp_path,
            "\n".join(
                [
                    "HEADLESS=true",
                    "DEFAULT_LIMIT=250",
                    "RETRY_ATTEMPTS=5",
                    "EXPORT_PATH=data/exports",
                ]
            ),
        )
        assert settings.headless is True
        assert settings.default_limit == 250
        assert settings.retry_attempts == 5
        assert settings.export_path == "data/exports"

    def test_falsey_headless_string_is_false(self, tmp_path):
        settings = make_env(tmp_path, "HEADLESS=false\n")
        assert settings.headless is False

    def test_invalid_int_falls_back_to_default(self, tmp_path):
        settings = make_env(tmp_path, "DEFAULT_LIMIT=abc\n")
        assert settings.default_limit == DEFAULT_SETTINGS["default_limit"]

    def test_missing_attribute_raises_without_recursion(self):
        settings = Settings(env_path=None, config_path=None)
        with pytest.raises(AttributeError):
            settings.definitely_not_a_setting  # noqa: B018

    def test_get_returns_default_for_missing_key(self):
        settings = Settings(env_path=None, config_path=None)
        assert settings.get("definitely_not_a_setting", 42) == 42
