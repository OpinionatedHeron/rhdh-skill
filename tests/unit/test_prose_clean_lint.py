"""The prose-clean linter scores technical prose through its public CLI and lint().

Expected scores are worked examples, not recomputed from the implementation.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "skills" / "meta" / "prose-clean" / "scripts" / "lint.py"

SLOPPY = (
    "This seamless solution will leverage cutting-edge tooling to supercharge "
    "your workflow — it is important to note that the parser serves as a "
    "gateway. I hope this helps! It's not just a parser, it's a platform."
)
PLAIN = "The parser reads the file. Then it writes the result."


def load_lint():
    spec = importlib.util.spec_from_file_location("prose_clean_lint", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_lint(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def test_a_puffed_sentence_scores_above_the_flavored_bar():
    """Worked example: marketing words, an em dash, chatbot residue, and 'serves as'."""
    report = load_lint().lint(SLOPPY)

    assert report["mode"] == "flavored"
    assert report["bar"] == 2.5
    assert report["over_bar"] is True
    assert report["violations"]["marketing_adjective"] >= 3
    assert report["violations"]["em_dash"] == 1
    assert report["violations"]["chatbot_residue"] >= 1
    assert report["violations"]["copula_avoidance"] >= 1
    assert report["violations"]["not_just_parallelism"] >= 1
    assert report["total_per100w"] > 2.5


def test_plain_technical_prose_stays_under_the_flavored_bar():
    report = load_lint().lint(PLAIN)

    assert report["over_bar"] is False
    assert report["total_per100w"] <= 2.5
    assert report["violations"]["marketing_adjective"] == 0
    assert report["violations"]["em_dash"] == 0
    assert report["violations"]["chatbot_residue"] == 0


def test_strict_mode_counts_should_and_using_flavored_does_not():
    text = "You should follow the runbook using the listed steps."
    module = load_lint()

    flavored = module.lint(text, strict=False)
    strict = module.lint(text, strict=True)

    assert "strict_banned_word" not in flavored["violations"]
    assert strict["violations"]["strict_banned_word"] >= 3
    assert strict["bar"] == 1.5
    assert strict["mode"] == "strict"
    assert strict["total"] > flavored["total"]


def test_fenced_code_and_inline_code_are_not_scored():
    text = (
        "The parser reads the file.\n\n"
        "```\nThis seamless solution will leverage cutting-edge tooling — supercharge.\n```\n"
        "Call `supercharge` to continue.\n"
    )
    report = load_lint().lint(text)

    assert report["violations"]["marketing_adjective"] == 0
    assert report["violations"]["banned_word"] == 0
    assert report["violations"]["em_dash"] == 0


def test_json_cli_reports_the_score_and_fail_over_exits_one(tmp_path):
    sloppy = tmp_path / "draft.md"
    sloppy.write_text(SLOPPY, encoding="utf-8")
    plain = tmp_path / "plain.md"
    plain.write_text(PLAIN, encoding="utf-8")

    scored = run_lint("--json", str(sloppy))
    report = json.loads(scored.stdout)
    assert scored.returncode == 0
    assert report["file"] == str(sloppy)
    assert report["over_bar"] is True

    failed = run_lint("--json", "--fail-over", "2.5", str(sloppy))
    assert failed.returncode == 1

    clean = run_lint("--json", "--fail-over", "2.5", str(plain))
    assert clean.returncode == 0


def test_help_lists_strict_json_and_fail_over():
    result = run_lint("--help")
    assert result.returncode == 0
    help_text = result.stdout
    assert "--strict" in help_text
    assert "--json" in help_text
    assert "--fail-over" in help_text


def test_stdin_json_when_piped():
    result = run_lint("--json", stdin=PLAIN)
    report = json.loads(result.stdout)
    assert result.returncode == 0
    assert report["over_bar"] is False
    assert "file" not in report
