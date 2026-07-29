"""Unit tests for skill-maker grilling prerequisite setup checker."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

SETUP_PATH = Path(__file__).resolve().parents[2] / "skills" / "skill-maker" / "scripts" / "setup.py"


def _load_setup():
    """Load skill-maker setup.py as a module without package install."""
    spec = importlib.util.spec_from_file_location("skill_maker_setup", SETUP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


setup = _load_setup()


def _place_grilling(root: Path) -> Path:
    """Create a fake grilling/SKILL.md under root/skills and return its path."""
    skill_md = root / "skills" / "grilling" / "SKILL.md"
    skill_md.parent.mkdir(parents=True, exist_ok=True)
    skill_md.write_text("---\nname: grilling\n---\n", encoding="utf-8")
    return skill_md.resolve()


class TestGrillingSearchPaths:
    def test_includes_user_and_project_locations(self, tmp_path):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        paths = setup.grilling_search_paths(home=home, cwd=cwd)
        assert home / ".claude" / "skills" / "grilling" / "SKILL.md" in paths
        assert home / ".agents" / "skills" / "grilling" / "SKILL.md" in paths
        assert home / ".cursor" / "skills" / "grilling" / "SKILL.md" in paths
        assert cwd / ".claude" / "skills" / "grilling" / "SKILL.md" in paths
        assert cwd / ".agents" / "skills" / "grilling" / "SKILL.md" in paths
        assert cwd / ".cursor" / "skills" / "grilling" / "SKILL.md" in paths


class TestFindGrilling:
    def test_missing_returns_none(self, tmp_path):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        home.mkdir()
        cwd.mkdir()
        assert setup.find_grilling(home=home, cwd=cwd) is None

    def test_found_in_claude_skills(self, tmp_path):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        cwd.mkdir()
        expected = _place_grilling(home / ".claude")
        assert setup.find_grilling(home=home, cwd=cwd) == expected

    def test_found_in_project_local_agents(self, tmp_path):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        home.mkdir()
        expected = _place_grilling(cwd / ".agents")
        assert setup.find_grilling(home=home, cwd=cwd) == expected

    def test_found_in_project_local_cursor(self, tmp_path):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        home.mkdir()
        expected = _place_grilling(cwd / ".cursor")
        assert setup.find_grilling(home=home, cwd=cwd) == expected

    def test_prefers_first_match_in_search_order(self, tmp_path):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        first = _place_grilling(home / ".claude")
        _place_grilling(home / ".cursor")
        assert setup.find_grilling(home=home, cwd=cwd) == first


class TestCheckGrilling:
    def test_pass_when_found(self, tmp_path):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        cwd.mkdir()
        path = _place_grilling(home / ".cursor")
        result = setup.check_grilling(home=home, cwd=cwd)
        assert result["grilling_found"] is True
        assert result["grilling_path"] == str(path)
        assert result["overall"] == "pass"
        assert (
            "npx skills@latest add mattpocock/skills --skill grilling" in result["minimal_install"]
        )
        assert "--all -g" in result["recommended_install"]

    def test_fail_when_missing(self, tmp_path):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        home.mkdir()
        cwd.mkdir()
        result = setup.check_grilling(home=home, cwd=cwd)
        assert result["grilling_found"] is False
        assert result["grilling_path"] is None
        assert result["overall"] == "fail"


class TestMainCli:
    def test_exit_zero_when_found(self, tmp_path, monkeypatch, capsys):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        cwd.mkdir()
        _place_grilling(home / ".claude")
        fixed = setup.check_grilling(home=home, cwd=cwd)
        monkeypatch.setattr(setup, "check_grilling", lambda *a, **k: fixed)

        code = setup.main(["--json"])
        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["overall"] == "pass"
        assert payload["grilling_found"] is True

    def test_exit_nonzero_when_missing(self, tmp_path, monkeypatch, capsys):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        home.mkdir()
        cwd.mkdir()
        fixed = setup.check_grilling(home=home, cwd=cwd)
        monkeypatch.setattr(setup, "check_grilling", lambda *a, **k: fixed)

        code = setup.main(["--json"])
        assert code == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["overall"] == "fail"
        assert payload["grilling_found"] is False

    def test_human_output_mentions_prereq_and_install_hints(self, tmp_path, monkeypatch, capsys):
        home = tmp_path / "home"
        cwd = tmp_path / "project"
        home.mkdir()
        cwd.mkdir()
        fixed = setup.check_grilling(home=home, cwd=cwd)
        monkeypatch.setattr(setup, "check_grilling", lambda *a, **k: fixed)

        code = setup.main([])
        assert code == 1
        out = capsys.readouterr().out
        assert "Hard prerequisite" in out
        assert setup.MINIMAL_INSTALL in out
        assert setup.RECOMMENDED_INSTALL in out
        assert "detects only" in out
