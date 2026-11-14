"""Tests for core/action_loader.py — action discovery, validation and dispatch."""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from core.action_loader import (
    ActionRecord, ActionRegistry, _validate, discover_actions,
    strip_meta, _NAME_RE,
)


# ── strip_meta ─────────────────────────────────────────────────────────────
class TestStripMeta:
    def test_removes_tier_and_brief(self):
        decls = [{"name": "a", "tier": "core", "brief": "short"}]
        result = strip_meta(decls)
        assert "tier" not in result[0]
        assert "brief" not in result[0]
        assert result[0]["name"] == "a"

    def test_leaves_clean_decls_unchanged(self):
        decls = [{"name": "b", "description": "do stuff"}]
        result = strip_meta(decls)
        assert result[0] is decls[0]  # same object, not a copy

    def test_non_dict_entries_pass_through(self):
        decls = ["not a dict", 42]
        result = strip_meta(decls)
        assert result == decls


# ── _NAME_RE ───────────────────────────────────────────────────────────────
class TestNameRegex:
    def test_valid_names(self):
        for name in ("open_app", "_private", "A1", "a" * 64):
            assert _NAME_RE.match(name), f"{name} should match"

    def test_invalid_names(self):
        for name in ("1abc", "", "a" * 65, "has space", "has-dash"):
            assert not _NAME_RE.match(name), f"{name} should NOT match"


# ── _validate ──────────────────────────────────────────────────────────────
class TestValidate:
    def _make_module(self, tool_dict):
        """Create a fake module with a TOOL attribute."""
        m = MagicMock()
        m.TOOL = tool_dict
        return m

    def test_valid_tool(self):
        handler = lambda parameters: "ok"
        tool = {
            "name": "test_action",
            "description": "A test action",
            "parameters": {"type": "OBJECT", "properties": {}},
            "handler": handler,
        }
        rec = _validate(self._make_module(tool), "test_action.py")
        assert rec.valid is True
        assert rec.name == "test_action"
        assert rec.handler is handler

    def test_missing_tool_dict(self):
        m = MagicMock()
        m.TOOL = None
        rec = _validate(m, "noaction.py")
        assert rec.valid is False
        assert "No module-level TOOL dict" in rec.error

    def test_invalid_name(self):
        tool = {
            "name": "1invalid",
            "description": "desc",
            "parameters": {"type": "OBJECT", "properties": {}},
            "handler": lambda p: None,
        }
        rec = _validate(self._make_module(tool), "bad.py")
        assert rec.valid is False
        assert "not a valid identifier" in rec.error

    def test_missing_description(self):
        tool = {
            "name": "nodesc",
            "description": "",
            "parameters": {"type": "OBJECT", "properties": {}},
            "handler": lambda p: None,
        }
        rec = _validate(self._make_module(tool), "nodesc.py")
        assert rec.valid is False
        assert "description" in rec.error.lower()

    def test_bad_parameters_type(self):
        tool = {
            "name": "badparams",
            "description": "desc",
            "parameters": {"type": "STRING"},
            "handler": lambda p: None,
        }
        rec = _validate(self._make_module(tool), "badparams.py")
        assert rec.valid is False
        assert "OBJECT" in rec.error

    def test_non_callable_handler(self):
        tool = {
            "name": "nohandler",
            "description": "desc",
            "parameters": {"type": "OBJECT", "properties": {}},
            "handler": "not callable",
        }
        rec = _validate(self._make_module(tool), "nohandler.py")
        assert rec.valid is False
        assert "not callable" in rec.error

    def test_behavior_and_scheduling(self):
        tool = {
            "name": "nb_action",
            "description": "non blocking",
            "parameters": {"type": "OBJECT", "properties": {}},
            "handler": lambda p: None,
            "behavior": "NON_BLOCKING",
            "scheduling": "WHEN_IDLE",
        }
        rec = _validate(self._make_module(tool), "nb.py")
        assert rec.valid is True
        assert rec.behavior == "NON_BLOCKING"
        assert rec.scheduling == "WHEN_IDLE"

    def test_tier_and_brief(self):
        tool = {
            "name": "tiered",
            "description": "has tier",
            "parameters": {"type": "OBJECT", "properties": {}},
            "handler": lambda p: None,
            "tier": "core",
            "brief": "short desc",
        }
        rec = _validate(self._make_module(tool), "tiered.py")
        assert rec.valid is True
        assert rec.tier == "core"
        assert rec.brief == "short desc"


# ── ActionRegistry ─────────────────────────────────────────────────────────
class TestActionRegistry:
    def _make_registry(self, records: dict[str, ActionRecord]) -> ActionRegistry:
        return ActionRegistry(records, logger=lambda s: None)

    def test_has(self):
        rec = ActionRecord(name="test", valid=True, handler=lambda p: "ok")
        reg = self._make_registry({"test": rec})
        assert reg.has("test") is True
        assert reg.has("nope") is False

    def test_names(self):
        r1 = ActionRecord(name="a", valid=True, handler=lambda p: "ok")
        r2 = ActionRecord(name="b", valid=True, handler=lambda p: "ok")
        reg = self._make_registry({"a": r1, "b": r2})
        assert reg.names() == {"a", "b"}

    def test_run_missing_action(self):
        reg = self._make_registry({})
        result = reg.run("missing", {})
        assert "not available" in result

    def test_run_valid_action(self):
        def handler(parameters):
            return f"got {parameters['x']}"
        rec = ActionRecord(name="act", valid=True, handler=handler)
        reg = self._make_registry({"act": rec})
        result = reg.run("act", {"x": 42})
        assert result == "got 42"

    def test_run_handler_crash_returns_error(self):
        def crasher(parameters):
            raise ValueError("boom")
        rec = ActionRecord(name="crash", valid=True, handler=crasher)
        reg = self._make_registry({"crash": rec})
        result = reg.run("crash", {})
        assert "failed" in result.lower()
        assert "boom" in result

    def test_get_tool_declarations(self):
        rec = ActionRecord(
            name="decl_test", description="desc", valid=True,
            handler=lambda p: None,
            parameters={"type": "OBJECT", "properties": {}},
            behavior="NON_BLOCKING", tier="core", brief="short",
        )
        reg = self._make_registry({"decl_test": rec})
        decls = reg.get_tool_declarations()
        assert len(decls) == 1
        d = decls[0]
        assert d["name"] == "decl_test"
        assert d["behavior"] == "NON_BLOCKING"
        assert d["tier"] == "core"
        assert d["brief"] == "short"

    def test_scheduling_returns_value(self):
        rec = ActionRecord(name="s", valid=True, handler=lambda p: None,
                           scheduling="SILENT")
        reg = self._make_registry({"s": rec})
        assert reg.scheduling("s") == "SILENT"
        assert reg.scheduling("missing") is None


# ── discover_actions (integration with tmp filesystem) ─────────────────────
class TestDiscoverActions:
    def test_discovers_valid_action_file(self, tmp_path):
        action_file = tmp_path / "greet.py"
        action_file.write_text(
            'def greet(parameters): return "hello"\n'
            'TOOL = {\n'
            '    "name": "greet",\n'
            '    "description": "Say hello",\n'
            '    "parameters": {"type": "OBJECT", "properties": {}},\n'
            '    "handler": greet,\n'
            '}\n',
            encoding="utf-8",
        )
        logs = []
        registry = discover_actions(tmp_path, logger=logs.append)
        assert registry.has("greet")
        assert "1 active" in logs[-1]

    def test_skips_underscore_files(self, tmp_path):
        (tmp_path / "_helper.py").write_text("TOOL = {}", encoding="utf-8")
        registry = discover_actions(tmp_path, logger=lambda s: None)
        assert registry.names() == set()

    def test_rejects_reserved_names(self, tmp_path):
        action_file = tmp_path / "reserved.py"
        action_file.write_text(
            'def fn(parameters): return "x"\n'
            'TOOL = {\n'
            '    "name": "search",\n'
            '    "description": "do search",\n'
            '    "parameters": {"type": "OBJECT", "properties": {}},\n'
            '    "handler": fn,\n'
            '}\n',
            encoding="utf-8",
        )
        registry = discover_actions(tmp_path, reserved_names={"search"},
                                     logger=lambda s: None)
        assert not registry.has("search")

    def test_skips_files_without_tool(self, tmp_path):
        (tmp_path / "helper.py").write_text(
            "# just a helper\ndef util(): pass\n", encoding="utf-8"
        )
        logs = []
        registry = discover_actions(tmp_path, logger=logs.append)
        assert registry.names() == set()

    def test_handles_import_error_gracefully(self, tmp_path):
        (tmp_path / "broken.py").write_text(
            "import this_module_does_not_exist_xyz\n"
            'TOOL = {"name": "broken"}\n',
            encoding="utf-8",
        )
        logs = []
        registry = discover_actions(tmp_path, logger=logs.append)
        assert not registry.has("broken")
        assert any("rejected" in l.lower() or "failed" in l.lower() for l in logs)
