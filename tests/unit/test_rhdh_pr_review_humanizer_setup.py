"""Tests for humanizer skill detection in rhdh-pr-review setup.py."""

import importlib.util
import json
from pathlib import Path

import pytest

SETUP = Path(__file__).parents[2] / "skills/rhdh-pr-review/scripts/setup.py"


def load_setup():
    spec = importlib.util.spec_from_file_location("rhdh_pr_review_setup", SETUP)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def setup_mod():
    return load_setup()


def _write_humanizer(base: Path) -> Path:
    skill = base / "humanizer" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# humanizer\n", encoding="utf-8")
    return skill


def test_humanizer_search_paths_order(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    paths = setup_mod.humanizer_search_paths(home=home, cwd=cwd)
    assert paths == [
        home / ".claude" / "skills" / "humanizer" / "SKILL.md",
        home / ".agents" / "skills" / "humanizer" / "SKILL.md",
        home / ".cursor" / "skills" / "humanizer" / "SKILL.md",
        cwd / ".claude" / "skills" / "humanizer" / "SKILL.md",
        cwd / ".agents" / "skills" / "humanizer" / "SKILL.md",
        cwd / ".cursor" / "skills" / "humanizer" / "SKILL.md",
    ]


def test_find_humanizer_missing(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    assert setup_mod.find_humanizer(home=home, cwd=cwd) is None


def test_find_humanizer_in_claude_skills(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    expected = _write_humanizer(home / ".claude" / "skills")
    found = setup_mod.find_humanizer(home=home, cwd=cwd)
    assert found == expected.resolve()


def test_find_humanizer_prefers_first_match(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    first = _write_humanizer(home / ".claude" / "skills")
    _write_humanizer(home / ".agents" / "skills")
    found = setup_mod.find_humanizer(home=home, cwd=cwd)
    assert found == first.resolve()


def test_find_humanizer_project_local(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    expected = _write_humanizer(cwd / ".agents" / "skills")
    found = setup_mod.find_humanizer(home=home, cwd=cwd)
    assert found == expected.resolve()


def test_find_humanizer_cursor_skills(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    expected = _write_humanizer(home / ".cursor" / "skills")
    found = setup_mod.find_humanizer(home=home, cwd=cwd)
    assert found == expected.resolve()


def test_find_humanizer_project_local_cursor_skills(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    expected = _write_humanizer(cwd / ".cursor" / "skills")
    found = setup_mod.find_humanizer(home=home, cwd=cwd)
    assert found == expected.resolve()


def test_check_humanizer_pass_fields(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    skill = _write_humanizer(home / ".cursor" / "skills")
    results = setup_mod.check_humanizer(home=home, cwd=cwd)
    assert results["humanizer_found"] is True
    assert results["humanizer_path"] == str(skill.resolve())
    assert results["overall"] == "pass"
    assert "humanizer" in results["minimal_install"]
    assert "blader/humanizer" in results["recommended_install"]


def test_check_humanizer_fail_fields(setup_mod, tmp_path):
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    home.mkdir()
    cwd.mkdir()
    results = setup_mod.check_humanizer(home=home, cwd=cwd)
    assert results["humanizer_found"] is False
    assert results["humanizer_path"] is None
    assert results["overall"] == "fail"
    assert results["minimal_install"] == setup_mod.MINIMAL_HUMANIZER_INSTALL
    assert results["recommended_install"] == setup_mod.RECOMMENDED_HUMANIZER_INSTALL


def test_humanizer_only_main_exit_nonzero_when_missing(setup_mod, monkeypatch, capsys):
    monkeypatch.setattr(
        setup_mod,
        "check_humanizer",
        lambda home=None, cwd=None: {
            "humanizer_found": False,
            "humanizer_path": None,
            "minimal_install": setup_mod.MINIMAL_HUMANIZER_INSTALL,
            "recommended_install": setup_mod.RECOMMENDED_HUMANIZER_INSTALL,
            "overall": "fail",
        },
    )

    with pytest.raises(SystemExit) as exc:
        setup_mod.main(["--humanizer-only", "--json"])
    assert exc.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["humanizer_found"] is False
    assert payload["overall"] == "fail"
    assert payload["minimal_install"] == setup_mod.MINIMAL_HUMANIZER_INSTALL
    assert payload["recommended_install"] == setup_mod.RECOMMENDED_HUMANIZER_INSTALL


def test_humanizer_only_main_exit_zero_when_found(setup_mod, tmp_path, monkeypatch, capsys):
    skill_path = str((tmp_path / "humanizer" / "SKILL.md").resolve())
    monkeypatch.setattr(
        setup_mod,
        "check_humanizer",
        lambda home=None, cwd=None: {
            "humanizer_found": True,
            "humanizer_path": skill_path,
            "minimal_install": setup_mod.MINIMAL_HUMANIZER_INSTALL,
            "recommended_install": setup_mod.RECOMMENDED_HUMANIZER_INSTALL,
            "overall": "pass",
        },
    )

    with pytest.raises(SystemExit) as exc:
        setup_mod.main(["--humanizer-only", "--json"])
    assert exc.value.code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["humanizer_found"] is True
    assert payload["humanizer_path"] == skill_path
    assert payload["overall"] == "pass"


def test_humanizer_only_human_output_includes_install_hints(setup_mod, monkeypatch, capsys):
    monkeypatch.setattr(
        setup_mod,
        "check_humanizer",
        lambda home=None, cwd=None: {
            "humanizer_found": False,
            "humanizer_path": None,
            "minimal_install": setup_mod.MINIMAL_HUMANIZER_INSTALL,
            "recommended_install": setup_mod.RECOMMENDED_HUMANIZER_INSTALL,
            "overall": "fail",
        },
    )

    with pytest.raises(SystemExit) as exc:
        setup_mod.main(["--humanizer-only"])
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "humanizer skill not found" in out
    assert setup_mod.MINIMAL_HUMANIZER_INSTALL in out
    assert setup_mod.RECOMMENDED_HUMANIZER_INSTALL in out
    assert "does not install" in out
