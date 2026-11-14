"""Tests for memory/config_manager.py — config read/write logic."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


# ---------------------------------------------------------------------------
# We import the module under test and patch its CONFIG_FILE / CONFIG_DIR so
# that every test operates on an in-memory fake instead of touching disk.
# ---------------------------------------------------------------------------
import memory.config_manager as cm


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path):
    """Redirect config_manager to a temp directory for every test."""
    fake_dir = tmp_path / "config"
    fake_file = fake_dir / "api_keys.json"
    with patch.object(cm, "CONFIG_DIR", fake_dir), \
         patch.object(cm, "CONFIG_FILE", fake_file):
        yield fake_file


# ── helpers ────────────────────────────────────────────────────────────────
def _write_cfg(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _read_cfg(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ── ensure_config_dir / config_exists ──────────────────────────────────────
class TestConfigDir:
    def test_ensure_config_dir_creates_directory(self, _isolated_config):
        assert not cm.CONFIG_DIR.exists()
        cm.ensure_config_dir()
        assert cm.CONFIG_DIR.is_dir()

    def test_config_exists_false_when_missing(self, _isolated_config):
        assert cm.config_exists() is False

    def test_config_exists_true_when_present(self, _isolated_config):
        _write_cfg(_isolated_config, {})
        assert cm.config_exists() is True


# ── save / load api keys ───────────────────────────────────────────────────
class TestApiKeys:
    def test_save_and_load_round_trip(self, _isolated_config):
        cm.save_api_keys("  test-key-12345  ")
        data = cm.load_api_keys()
        assert data["gemini_api_key"] == "test-key-12345"

    def test_save_preserves_existing_keys(self, _isolated_config):
        _write_cfg(_isolated_config, {"other": "value"})
        cm.save_api_keys("key123")
        data = _read_cfg(_isolated_config)
        assert data["other"] == "value"
        assert data["gemini_api_key"] == "key123"

    def test_load_returns_empty_dict_when_missing(self, _isolated_config):
        assert cm.load_api_keys() == {}

    def test_load_returns_empty_dict_on_corrupt_file(self, _isolated_config):
        _isolated_config.parent.mkdir(parents=True, exist_ok=True)
        _isolated_config.write_text("NOT JSON", encoding="utf-8")
        assert cm.load_api_keys() == {}


# ── get_gemini_key / is_configured ─────────────────────────────────────────
class TestGeminiKey:
    def test_get_gemini_key_none_when_missing(self, _isolated_config):
        assert cm.get_gemini_key() is None

    def test_get_gemini_key_returns_saved_value(self, _isolated_config):
        cm.save_api_keys("abcdefghijklmnopqrst")
        assert cm.get_gemini_key() == "abcdefghijklmnopqrst"

    def test_is_configured_false_when_no_key(self, _isolated_config):
        assert cm.is_configured() is False

    def test_is_configured_false_when_short_key(self, _isolated_config):
        cm.save_api_keys("short")
        assert cm.is_configured() is False

    def test_is_configured_true_when_long_key(self, _isolated_config):
        cm.save_api_keys("a" * 20)
        assert cm.is_configured() is True


# ── assistant name / user name ─────────────────────────────────────────────
class TestAssistantConfig:
    def test_default_assistant_name(self, _isolated_config):
        assert cm.get_assistant_name() == "JARVIS"

    def test_save_and_get_assistant_name(self, _isolated_config):
        cm.save_assistant_config("Friday", "Tony")
        assert cm.get_assistant_name() == "Friday"
        assert cm.get_user_name() == "Tony"

    def test_empty_assistant_name_falls_back(self, _isolated_config):
        cm.save_assistant_config("", "")
        assert cm.get_assistant_name() == "JARVIS"


# ── voice ──────────────────────────────────────────────────────────────────
class TestVoice:
    def test_default_voice(self, _isolated_config):
        assert cm.get_voice() == cm.DEFAULT_VOICE

    def test_save_valid_voice(self, _isolated_config):
        cm.save_voice("Puck")
        assert cm.get_voice() == "Puck"

    def test_save_invalid_voice_falls_back(self, _isolated_config):
        cm.save_voice("NonExistent")
        assert cm.get_voice() == cm.DEFAULT_VOICE


# ── boolean flag helpers ───────────────────────────────────────────────────
class TestBooleanFlags:
    def test_wake_word_default_false(self, _isolated_config):
        assert cm.get_wake_word_enabled() is False

    def test_save_wake_word(self, _isolated_config):
        cm.save_wake_word_enabled(True)
        assert cm.get_wake_word_enabled() is True

    def test_push_to_talk_default_false(self, _isolated_config):
        assert cm.get_push_to_talk_enabled() is False

    def test_thinking_default_false(self, _isolated_config):
        assert cm.get_thinking_enabled() is False


# ── hud style ──────────────────────────────────────────────────────────────
class TestHudStyle:
    def test_default_hud_style(self, _isolated_config):
        assert cm.get_hud_style() == "face"

    def test_save_valid_hud_style(self, _isolated_config):
        cm.save_hud_style("core")
        assert cm.get_hud_style() == "core"

    def test_save_invalid_hud_style_falls_back(self, _isolated_config):
        cm.save_hud_style("hologram")
        assert cm.get_hud_style() == "face"


# ── ui scale ───────────────────────────────────────────────────────────────
class TestUiScale:
    def test_default_ui_scale(self, _isolated_config):
        assert cm.get_ui_scale() == 0.0

    def test_valid_scale(self, _isolated_config):
        cm.save_ui_scale(1.5)
        assert cm.get_ui_scale() == 1.5

    def test_too_small_scale_returns_zero(self, _isolated_config):
        cm.save_ui_scale(0.3)
        assert cm.get_ui_scale() == 0.0

    def test_clamped_at_max(self, _isolated_config):
        cm.save_ui_scale(5.0)
        assert cm.get_ui_scale() == 3.0


# ── plugin enabled / plugin config ─────────────────────────────────────────
class TestPlugins:
    def test_plugin_enabled_default_true(self, _isolated_config):
        assert cm.get_plugin_enabled("my_plugin") is True

    def test_save_plugin_disabled(self, _isolated_config):
        cm.save_plugin_enabled("my_plugin", False)
        assert cm.get_plugin_enabled("my_plugin") is False

    def test_plugin_config_empty_when_none(self, _isolated_config):
        assert cm.get_plugin_config("ns") == {}

    def test_save_and_get_plugin_config(self, _isolated_config):
        cm.save_plugin_config("printer", {"ip": "192.168.1.10"})
        assert cm.get_plugin_setting("printer", "ip") == "192.168.1.10"

    def test_plugin_config_merges(self, _isolated_config):
        cm.save_plugin_config("ns", {"a": 1})
        cm.save_plugin_config("ns", {"b": 2})
        cfg = cm.get_plugin_config("ns")
        assert cfg == {"a": 1, "b": 2}
