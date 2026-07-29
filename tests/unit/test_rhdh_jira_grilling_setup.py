"""Tests for grilling skill detection in rhdh-jira setup.py."""

import importlib.util
import json
from pathlib import Path

import pytest

SETUP = Path(__file__).parents[2] / "skills/rhdh-jira/scripts/setup.py"


def load_setup():
    spec = importlib.util.spec_from_file_location("rhdh_jira_setup", SETUP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def setup_mod():
    return load_setup()


def _write_grilling(base: Path) -> Path:
    skill = base / "grilling" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# grilling\n", encoding="utf-8")
    return skill


def test_grilling_search_paths_order(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    paths = setup_mod.grilling_search_paths(home=home, cwd=cwd)
    assert paths == [
        home / ".claude" / "skills" / "grilling" / "SKILL.md",
        home / ".agents" / "skills" / "grilling" / "SKILL.md",
        home / ".cursor" / "skills" / "grilling" / "SKILL.md",
        cwd / ".claude" / "skills" / "grilling" / "SKILL.md",
        cwd / ".agents" / "skills" / "grilling" / "SKILL.md",
        cwd / ".cursor" / "skills" / "grilling" / "SKILL.md",
    ]


def test_find_grilling_missing(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    assert setup_mod.find_grilling(home=home, cwd=cwd) is None


def test_find_grilling_in_claude_skills(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    expected = _write_grilling(home / ".claude" / "skills")
    found = setup_mod.find_grilling(home=home, cwd=cwd)
    assert found == expected.resolve()


def test_find_grilling_prefers_first_match(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    first = _write_grilling(home / ".claude" / "skills")
    _write_grilling(home / ".agents" / "skills")
    found = setup_mod.find_grilling(home=home, cwd=cwd)
    assert found == first.resolve()


def test_find_grilling_project_local(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    expected = _write_grilling(cwd / ".agents" / "skills")
    found = setup_mod.find_grilling(home=home, cwd=cwd)
    assert found == expected.resolve()


def test_find_grilling_cursor_skills(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    expected = _write_grilling(home / ".cursor" / "skills")
    found = setup_mod.find_grilling(home=home, cwd=cwd)
    assert found == expected.resolve()


def test_find_grilling_project_local_cursor_skills(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    expected = _write_grilling(cwd / ".cursor" / "skills")
    found = setup_mod.find_grilling(home=home, cwd=cwd)
    assert found == expected.resolve()


def test_check_grilling_pass_fields(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    skill = _write_grilling(home / ".cursor" / "skills")
    results = setup_mod.check_grilling(home=home, cwd=cwd)
    assert results["grilling_found"] is True
    assert results["grilling_path"] == str(skill.resolve())
    assert results["overall"] == "pass"
    assert "grilling" in results["minimal_install"]
    assert "--all -g" in results["recommended_install"]


def test_check_grilling_fail_fields(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    results = setup_mod.check_grilling(home=home, cwd=cwd)
    assert results["grilling_found"] is False
    assert results["grilling_path"] is None
    assert results["overall"] == "fail"
    assert results["minimal_install"] == setup_mod.MINIMAL_GRILLING_INSTALL
    assert results["recommended_install"] == setup_mod.RECOMMENDED_GRILLING_INSTALL


def test_grilling_only_main_exit_nonzero_when_missing(setup_mod, monkeypatch, capsys):
    monkeypatch.setattr(
        setup_mod,
        "check_grilling",
        lambda home=None, cwd=None: {
            "grilling_found": False,
            "grilling_path": None,
            "minimal_install": setup_mod.MINIMAL_GRILLING_INSTALL,
            "recommended_install": setup_mod.RECOMMENDED_GRILLING_INSTALL,
            "overall": "fail",
        },
    )

    with pytest.raises(SystemExit) as exc:
        setup_mod.main(["--grilling-only", "--json"])
    assert exc.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["grilling_found"] is False
    assert payload["overall"] == "fail"
    assert payload["minimal_install"] == setup_mod.MINIMAL_GRILLING_INSTALL
    assert payload["recommended_install"] == setup_mod.RECOMMENDED_GRILLING_INSTALL


def test_grilling_only_main_exit_zero_when_found(setup_mod, tmp_path, monkeypatch, capsys):
    skill_path = str((tmp_path / "grilling" / "SKILL.md").resolve())
    monkeypatch.setattr(
        setup_mod,
        "check_grilling",
        lambda home=None, cwd=None: {
            "grilling_found": True,
            "grilling_path": skill_path,
            "minimal_install": setup_mod.MINIMAL_GRILLING_INSTALL,
            "recommended_install": setup_mod.RECOMMENDED_GRILLING_INSTALL,
            "overall": "pass",
        },
    )

    with pytest.raises(SystemExit) as exc:
        setup_mod.main(["--grilling-only", "--json"])
    assert exc.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["grilling_found"] is True
    assert payload["grilling_path"] == skill_path
    assert payload["overall"] == "pass"


def test_grilling_only_human_output_includes_install_hints(setup_mod, monkeypatch, capsys):
    monkeypatch.setattr(
        setup_mod,
        "check_grilling",
        lambda home=None, cwd=None: {
            "grilling_found": False,
            "grilling_path": None,
            "minimal_install": setup_mod.MINIMAL_GRILLING_INSTALL,
            "recommended_install": setup_mod.RECOMMENDED_GRILLING_INSTALL,
            "overall": "fail",
        },
    )

    with pytest.raises(SystemExit) as exc:
        setup_mod.main(["--grilling-only"])
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "grilling skill not found" in out
    assert setup_mod.MINIMAL_GRILLING_INSTALL in out
    assert setup_mod.RECOMMENDED_GRILLING_INSTALL in out
    assert "does not install" in out
