"""The prose-editing linter, exercised through lint() and through the CLI.

Every expected score below is a worked example: the counts are written out by
hand from the fixture text, never recomputed from the implementation.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL = PROJECT_ROOT / "skills" / "reference" / "prose-editing"
SCRIPT = SKILL / "scripts" / "lint.py"
REFERENCES = (SKILL / "references" / "mechanical.md", SKILL / "references" / "voice.md")

# seamless + leverage (ai_vocabulary), cutting-edge (promotional), one em dash,
# "it is important to note" (modal_hedge, and nowhere else), "serves as"
# (copula_avoidance), "I hope this helps" (chatbot_residue), the not-just
# parallelism, and two contractions. Ten violations over 31 words.
SLOPPY = (
    "This seamless platform will leverage cutting-edge tooling — it is "
    "important to note that the parser serves as a gateway. I hope this helps! "
    "It's not just a parser, it's a platform."
)
SLOPPY_WORDS = 31
SLOPPY_TOTAL = 10
SLOPPY_PER100W = 32.26

PLAIN = "The parser reads the file. Then it writes the result."
PLAIN_WORDS = 10

# A glossary names the words it forbids. Under --quote-safe the word lists go
# quiet and only the structural checks stay on.
GLOSSARY = (
    "# Words this skill removes\n\n"
    "Every word below is banned in a rewrite.\n\n"
    "leverage, utilize, delve, seamless, robust\n\n"
    "Do not write spin up. The phrase in order to becomes to.\n"
)
GLOSSARY_WORDS = 29
GLOSSARY_TOTAL = 8
GLOSSARY_SAFE_TOTAL = 1

VOICED = (
    "Then the release landed. It had no roadmap. No plan. No owner.\n\n"
    "The **team** shipped the **fix** and the **docs** in one day.\n\n"
    "## Conclusion\n\n"
    "The future looks bright. The release plays a vital role for us.\n"
)
VOICED_WORDS = 36
VOICED_TOTAL = 6
VOICED_PER100W = 16.67
# staccato_drama once and boldface_overuse twice are the voice layer. The
# `## Conclusion` heading, "the future looks bright" and "plays a vital role"
# are mechanical, because a README closes that way too.
VOICED_VOICE_LAYER = 3

# Every term the modern marketing register runs on. Each one has to score
# somewhere; which list owns it is an implementation detail.
MARKETING_TERMS = (
    "streamline",
    "elevate",
    "harness the",
    "foster",
    "bolster",
    "navigate the complexities",
    "ever-evolving",
    "at a crossroads",
    "find themselves",
    "in summary",
    "in conclusion",
    "unlock the power",
    "take it to the next level",
    "game changer",
    "deep dive",
    "best-in-class",
    "robust and scalable",
)

CONTRACT_KEYS = {
    "score_version",
    "register",
    "quote_safe",
    "words",
    "sentences",
    "violations",
    "by_layer",
    "total",
    "total_per100w",
    "bar",
    "over_bar",
    "longest_sentence_words",
    "markers",
    "samples",
    "delta",
}


def load_lint():
    spec = importlib.util.spec_from_file_location("prose_editing_lint", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_lint(
    *args: str, stdin: str | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        encoding="utf-8",
        check=False,
        env={**os.environ, **env} if env else None,
    )


def documented_examples() -> list[tuple[str, str, Path]]:
    """Every `### \\`category\\`` section in the reference files, with its first example.

    The reference files put the tell in the first blockquote of the section and
    the rewrite, when there is one, in the blockquotes after it.
    """
    found: list[tuple[str, str, Path]] = []
    heading = re.compile(r"^#{2,4}\s+`([a-z_]+)`\s*$")
    for path in REFERENCES:
        category = None
        quote: list[str] = []
        for line in path.read_text(encoding="utf-8").split("\n"):
            if line.startswith(">"):
                quote.append(line.lstrip(">").strip())
                continue
            if quote and category:
                found.append((category, " ".join(quote), path))
                category = None
            quote = []
            match = heading.match(line.strip())
            if match:
                category = match.group(1)
            elif line.startswith("#"):
                category = None
        if quote and category:
            found.append((category, " ".join(quote), path))
    return found


def run_lint_bytes(*args: str, stdin: bytes) -> subprocess.CompletedProcess[bytes]:
    """Feed raw bytes so the child has to decode the pipe itself."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=stdin,
        capture_output=True,
        check=False,
    )


# --------------------------------------------------------------------------
# Worked examples
# --------------------------------------------------------------------------


def test_a_puffed_paragraph_scores_ten_over_thirty_one_words():
    report = load_lint().lint(SLOPPY)
    violations = report["violations"]

    assert report["register"] == "flavored"
    assert report["bar"] == 2.5
    assert report["words"] == SLOPPY_WORDS
    assert violations["em_dash"] == 1
    assert violations["ai_vocabulary"] == 2
    assert violations["promotional"] == 1
    assert violations["modal_hedge"] == 1
    assert violations["copula_avoidance"] == 1
    assert violations["chatbot_residue"] == 1
    assert violations["negative_parallelism"] == 1
    assert violations["contraction"] == 2
    assert report["total"] == SLOPPY_TOTAL
    assert report["total_per100w"] == SLOPPY_PER100W
    assert report["over_bar"] is True
    assert report["by_layer"]["mechanical"] == 8
    assert report["by_layer"]["compression"] == 2
    assert report["by_layer"]["voice"] == 0


def test_plain_technical_prose_scores_nothing():
    report = load_lint().lint(PLAIN)

    assert report["words"] == PLAIN_WORDS
    assert report["total"] == 0
    assert report["total_per100w"] == 0.0
    assert report["over_bar"] is False
    assert report["samples"] == {}


def test_the_report_carries_every_contract_key():
    report = load_lint().lint(PLAIN)

    assert set(report) == CONTRACT_KEYS
    assert report["score_version"] == 5
    assert report["quote_safe"] is False
    assert report["delta"] is None
    assert report["markers"] == {"noun_train": 0, "rule_of_three": 0}
    assert report["longest_sentence_words"] == 5


# --------------------------------------------------------------------------
# Regressions
# --------------------------------------------------------------------------


def test_it_is_important_to_note_scores_once_not_twice():
    """It sat in the banned list and the hedge list, so one hit scored two."""
    report = load_lint().lint("It is important to note that the parser reads the file.")

    assert report["violations"]["modal_hedge"] == 1
    assert report["violations"]["verbose_word"] == 0
    assert report["total"] == 1


def test_no_two_phrase_lists_hold_the_same_phrase():
    """Containment is resolved by the longest match. An exact tie has no owner."""
    module = load_lint()
    lists = list(module.PHRASE_LISTS.items())
    for name, phrases in lists:
        assert len(set(phrases)) == len(phrases), f"{name} repeats a phrase"
    for index, (left_name, left) in enumerate(lists):
        for right_name, right in lists[index + 1 :]:
            shared = set(left) & set(right)
            assert not shared, f"{left_name} and {right_name} both claim {sorted(shared)}"


def test_every_phrase_scores_its_own_category_exactly_once():
    """The companion to the list check: two categories may not claim one span.

    `marks a pivotal moment` holds `pivotal`, `underscores our ongoing
    commitment` holds `commitment to`, and `it should be noted` holds the STE
    ban on `should`. Each of those is one tell, and the longest match owns it.
    """
    module = load_lint()
    owned = set(module.PHRASE_LISTS)
    wrong = []
    for name, phrases in module.PHRASE_LISTS.items():
        for phrase in phrases:
            report = module.lint(f"The tool {phrase} the file.", register="review")
            scored = {
                category: count
                for category, count in report["violations"].items()
                if count and category in owned
            }
            if scored != {name: 1}:
                wrong.append((name, phrase, scored))

    assert wrong == []


def test_an_em_dash_scores_and_a_range_and_a_posix_separator_do_not():
    module = load_lint()

    report = module.lint("Pass the --json flag. The build failed -- the cache was stale.")
    assert report["violations"]["em_dash"] == 1
    assert report["total"] == 1

    assert module.lint("The build failed — the cache was stale.")["violations"]["em_dash"] == 1
    # An en dash is the correct character for a range, and the spaced double
    # hyphen after a command is POSIX end-of-options, not punctuation.
    assert module.lint("The window is 10–20 seconds.")["violations"]["em_dash"] == 0
    assert (
        module.lint("Supported on OCP 5.1–5.6 and in layers L1–L4b.")["violations"]["em_dash"] == 0
    )
    assert (
        module.lint("Run npm test -- --watch and git log -- src/ now.")["violations"]["em_dash"]
        == 0
    )
    # A free-standing en dash is still a dash doing a period's work.
    assert module.lint("The build failed – the cache was stale.")["violations"]["em_dash"] == 1


def test_the_not_just_parallelism_stops_at_a_paragraph_break():
    module = load_lint()

    joined = module.lint("It's not just a parser, it's a platform.")
    split = module.lint("It's not just a parser.\n\nThe operator restarts the pod. It's ready.")

    assert joined["violations"]["negative_parallelism"] == 1
    assert split["violations"]["negative_parallelism"] == 0


def test_stdin_decodes_utf8_no_matter_the_platform_default(tmp_path):
    """A piped em dash and the same em dash in a file must score the same."""
    text = "The build failed — the cache was stale. Restart the pod — twice."
    draft = tmp_path / "draft.md"
    draft.write_text(text, encoding="utf-8")

    from_file = json.loads(run_lint("--json", str(draft)).stdout)
    piped = run_lint_bytes("--json", stdin=text.encode("utf-8"))
    from_stdin = json.loads(piped.stdout.decode("utf-8"))

    assert from_file["violations"]["em_dash"] == 2
    assert from_stdin["violations"]["em_dash"] == 2
    assert from_stdin["words"] == from_file["words"]
    assert "file" not in from_stdin


# --------------------------------------------------------------------------
# Quote safety
# --------------------------------------------------------------------------


def test_yaml_frontmatter_is_not_prose():
    module = load_lint()
    body = "The linter reads the file.\n"
    with_frontmatter = (
        "---\n"
        "name: prose-editing\n"
        "description: A seamless and robust linter that will leverage\n"
        "  cutting-edge tooling to supercharge your docs.\n"
        "---\n\n" + body
    )

    framed = module.lint(with_frontmatter)
    bare = module.lint(body)

    assert framed["words"] == bare["words"] == 5
    assert framed["total"] == 0
    assert framed["violations"]["ai_vocabulary"] == 0


def test_table_rows_are_not_prose_and_produce_no_noun_train():
    report = load_lint().lint(
        "The glossary lists replacements.\n\n"
        "| Avoid | Use |\n"
        "|---|---|\n"
        "| spin up / spun up | start |\n"
        "| leverage | use |\n"
    )

    assert report["words"] == 4
    assert report["total"] == 0
    assert report["violations"]["phrasal_verb"] == 0
    assert report["markers"]["noun_train"] == 0


def test_link_targets_are_dropped_and_link_text_is_kept():
    report = load_lint().lint(
        "Read the flavored rules first.\n\n"
        "See [references/flavored.md](references/flavored.md) and "
        "[the strict list](references/strict.md).\n"
    )

    assert report["words"] == 12
    assert report["total"] == 0
    assert report["markers"]["noun_train"] == 0


def test_blockquotes_and_code_are_not_scored():
    module = load_lint()

    quoted = module.lint(
        "The rule is simple.\n\n"
        "> This seamless platform will leverage cutting-edge tooling.\n"
        "> I hope this helps!\n"
    )
    fenced = module.lint(
        "The parser reads the file.\n\n"
        "```\nThis seamless platform will leverage cutting-edge tooling — supercharge.\n```\n\n"
        "Call `supercharge` to continue.\n"
    )

    assert quoted["words"] == 4
    assert quoted["total"] == 0
    assert fenced["words"] == 8
    assert fenced["total"] == 0


def test_quote_safe_lets_a_glossary_name_the_words_it_forbids():
    module = load_lint()

    scored = module.lint(GLOSSARY)
    safe = module.lint(GLOSSARY, quote_safe=True)

    assert scored["words"] == safe["words"] == GLOSSARY_WORDS
    assert scored["violations"]["ai_vocabulary"] == 5
    assert scored["violations"]["phrasal_verb"] == 1
    assert scored["violations"]["verbose_word"] == 1
    assert scored["total"] == GLOSSARY_TOTAL

    assert safe["quote_safe"] is True
    assert safe["violations"]["ai_vocabulary"] == 0
    assert safe["violations"]["phrasal_verb"] == 0
    assert safe["violations"]["verbose_word"] == 0
    assert "ai_vocabulary" not in safe["samples"]
    # Structural checks stay on: the sentence about the words is still prose.
    assert safe["violations"]["passive_voice"] == 1
    assert safe["total"] == GLOSSARY_SAFE_TOTAL


# --------------------------------------------------------------------------
# Registers and layers
# --------------------------------------------------------------------------


def test_strict_adds_the_ste_word_set_and_the_lower_bar():
    module = load_lint()
    text = "You should follow the runbook using the listed steps."

    flavored = module.lint(text)
    strict = module.lint(text, register="strict")

    assert "strict_banned_word" not in flavored["violations"]
    assert flavored["total"] == 0
    assert strict["violations"]["strict_banned_word"] == 3
    assert strict["bar"] == 1.5
    assert strict["total"] == 3


def test_strict_matches_may_case_sensitively_so_the_month_stays_clean():
    report = load_lint().lint("May is a month. The pod may restart.", register="strict")

    assert report["violations"]["strict_banned_word"] == 1
    assert report["samples"]["strict_banned_word"] == ["may"]


def test_each_register_scores_its_own_layers():
    module = load_lint()

    flavored = module.lint(PLAIN)
    voiced = module.lint(PLAIN, register="voiced")
    review = module.lint(PLAIN, register="review")

    assert set(module.MECHANICAL) <= set(flavored["violations"])
    assert set(module.COMPRESSION) - {"strict_banned_word"} <= set(flavored["violations"])
    assert set(module.VOICE).isdisjoint(flavored["violations"])

    assert set(module.VOICE) <= set(voiced["violations"])
    assert set(module.COMPRESSION).isdisjoint(voiced["violations"])
    assert voiced["bar"] == 2.0

    assert set(review["violations"]) == (
        set(module.MECHANICAL) | set(module.COMPRESSION) | set(module.VOICE)
    )
    assert review["bar"] is None
    assert review["over_bar"] is False


def test_review_reports_the_strict_word_set_because_it_cannot_know_the_document_type():
    """A read-only pass over a runbook must still surface the procedure word set."""
    module = load_lint()
    runbook = "You should follow the runbook using the listed steps."

    review = module.lint(runbook, register="review")
    flavored = module.lint(runbook, register="flavored")

    assert review["violations"]["strict_banned_word"] >= 3
    assert "strict_banned_word" not in flavored["violations"]
    assert review["bar"] is None, "review reports; it never gates"


def test_the_voice_layer_scores_drama_boldface_conclusions_and_inflation():
    report = load_lint().lint(VOICED, register="voiced")
    violations = report["violations"]

    assert report["words"] == VOICED_WORDS
    assert violations["staccato_drama"] == 1
    assert violations["boldface_overuse"] == 2
    assert violations["generic_conclusion"] == 2
    assert violations["significance_inflation"] == 1
    assert report["total"] == VOICED_TOTAL
    assert report["total_per100w"] == VOICED_PER100W
    assert report["by_layer"]["voice"] == VOICED_VOICE_LAYER
    assert report["by_layer"]["mechanical"] == VOICED_TOTAL - VOICED_VOICE_LAYER
    assert report["over_bar"] is True


def test_a_send_off_and_an_inflated_claim_score_in_every_register():
    """Both moved out of the voice layer: a README ends that way too."""
    module = load_lint()
    text = "In conclusion, the release marks a turning point for the platform.\n"

    for register in ("strict", "flavored", "voiced", "review"):
        report = module.lint(text, register=register)
        assert report["violations"]["generic_conclusion"] == 1, register
        assert report["violations"]["significance_inflation"] == 1, register
        assert report["by_layer"]["mechanical"] >= 2, register

    # The two that stayed behind: short steps are right in a runbook and a bold
    # defined term is right in a README.
    assert set(module.VOICE) == {"staccato_drama", "boldface_overuse"}
    assert {"generic_conclusion", "significance_inflation"} <= set(module.MECHANICAL)


def test_markers_are_reported_and_never_added_to_the_total():
    report = load_lint().lint(
        "The team shipped the parser, the linter, and the docs.\n\n"
        "The release adds caching, ensuring the pod restarts cleanly.\n"
    )

    assert report["markers"]["rule_of_three"] == 1
    assert report["markers"]["noun_train"] == 1
    assert "noun_train" not in report["violations"]
    assert "rule_of_three" not in report["violations"]
    assert report["violations"]["ing_analysis"] == 1
    assert report["total"] == 1


# --------------------------------------------------------------------------
# Precision
# --------------------------------------------------------------------------


def test_title_case_headings_need_a_capitalized_function_word():
    report = load_lint().lint(
        "# Install the Red Hat Developer Hub operator\n\n"
        "## Strategic Negotiations And Global Partnerships\n\n"
        "### Red Hat Developer Hub\n\n"
        "#### Quote safety and link targets\n"
    )

    assert report["violations"]["title_case_heading"] == 1
    assert report["samples"]["title_case_heading"] == [
        "Strategic Negotiations And Global Partnerships"
    ]


def test_a_product_name_in_a_heading_is_not_title_case():
    """No list of proper nouns can hold a product namespace, so none is kept.

    Title Case capitalizes the function words a name never does, and that is
    the only evidence this check now accepts.
    """
    module = load_lint()
    products = module.lint(
        "## Amazon Elastic Kubernetes Service\n\n"
        "## Red Hat Advanced Cluster Security\n\n"
        "## Configure Keycloak Identity Brokering\n\n"
        "## Azure Front Door Standard\n"
    )
    titled = module.lint("## Installing Dynamic Plugins On OpenShift\n")

    assert products["violations"]["title_case_heading"] == 0
    assert titled["violations"]["title_case_heading"] == 1
    assert not hasattr(module, "PROPER_NOUNS")


def test_false_ranges_ignore_real_numbers_and_real_conversions():
    report = load_lint().lint(
        "The book takes us from the singularity of the Big Bang to the grand "
        "cosmic web.\n\n"
        "Upgrade from 1.9 to 1.10 first.\n\n"
        "Convert the file from the old schema to the new schema.\n\n"
        "The job copies artifacts from the build directory to the release bucket.\n"
    )

    assert report["violations"]["false_range"] == 1
    assert report["samples"]["false_range"] == [
        "from the singularity of the Big Bang to the grand cosmic web"
    ]


def test_emoji_covers_pictographs_and_leaves_punctuation_alone():
    module = load_lint()

    decorated = module.lint("🚀 The build shipped. ✅ Tests pass. “done”\n")
    punctuation = module.lint("The arrow → and the ellipsis … are not emoji.")

    assert decorated["violations"]["emoji"] == 2
    assert decorated["violations"]["curly_quote"] == 2
    assert punctuation["violations"]["emoji"] == 0
    assert punctuation["violations"]["curly_quote"] == 0


def test_inline_header_list_needs_the_value_to_restate_the_label():
    """The tell is padding, so the value decides. A label carrying a fact is good structure."""
    module = load_lint()

    padded = module.lint(
        "- **User Experience:** The user experience has been significantly improved.\n"
        "- **Performance:** Performance has been enhanced through optimization.\n"
    )
    definition_list = module.lint("- **Milestone:** 2026-03-01\n- **Owner:** the release team\n")
    label_with_news = module.lint("- **RBAC:** Operators can now scope plugins per team.\n")

    assert padded["violations"]["inline_header_list"] == 2
    assert definition_list["violations"]["inline_header_list"] == 0
    assert label_with_news["violations"]["inline_header_list"] == 0


def test_rhetorical_openers_need_the_theatrical_pause():
    module = load_lint()

    opener = module.lint("Is it worth it? Honestly? It depends on the cache.")
    plain_look = module.lint("Look at the logs before you restart the pod.")

    assert opener["violations"]["rhetorical_opener"] == 1
    assert plain_look["violations"]["rhetorical_opener"] == 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_json_cli_reports_the_file_and_fail_over_exits_one(tmp_path):
    sloppy = tmp_path / "draft.md"
    sloppy.write_text(SLOPPY, encoding="utf-8")
    plain = tmp_path / "plain.md"
    plain.write_text(PLAIN, encoding="utf-8")

    scored = run_lint("--json", str(sloppy))
    report = json.loads(scored.stdout)
    assert scored.returncode == 0
    assert report["file"] == str(sloppy)
    assert report["total_per100w"] == SLOPPY_PER100W
    assert report["over_bar"] is True

    assert run_lint("--json", "--fail-over", "2.5", str(sloppy)).returncode == 1
    assert run_lint("--json", "--fail-over", "2.5", str(plain)).returncode == 0

    both = json.loads(run_lint("--json", str(sloppy), str(plain)).stdout)
    assert [Path(entry["file"]).name for entry in both] == ["draft.md", "plain.md"]


def test_the_plain_text_line_reports_the_score_and_still_fails_over(tmp_path):
    sloppy = tmp_path / "draft.md"
    sloppy.write_text(SLOPPY, encoding="utf-8")
    plain = tmp_path / "plain.md"
    plain.write_text(PLAIN, encoding="utf-8")

    failed = run_lint("--fail-over", "2.5", str(sloppy))
    assert failed.returncode == 1
    assert failed.stdout.startswith("draft.md")
    assert "register=flavored" in failed.stdout
    assert f"per100w={SLOPPY_PER100W:7.2f}" in failed.stdout
    assert failed.stdout.rstrip().endswith("over")
    assert not failed.stdout.lstrip().startswith("{")

    passed = run_lint("--fail-over", "2.5", str(plain))
    assert passed.returncode == 0
    assert passed.stdout.rstrip().endswith("ok")


def test_the_deprecated_strict_flag_still_selects_the_strict_register(tmp_path):
    runbook = tmp_path / "runbook.md"
    runbook.write_text("You should follow the runbook using the listed steps.", encoding="utf-8")

    legacy = json.loads(run_lint("--json", "--strict", str(runbook)).stdout)
    named = json.loads(run_lint("--json", "--register", "strict", str(runbook)).stdout)

    assert legacy["register"] == "strict"
    assert legacy["violations"] == named["violations"]


def test_a_baseline_adds_a_delta(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(SLOPPY, encoding="utf-8")
    baseline = tmp_path / "before.json"
    baseline.write_text(json.dumps({"file": str(draft), "total_per100w": 40.0}), encoding="utf-8")

    improved = json.loads(run_lint("--json", "--baseline", str(baseline), str(draft)).stdout)
    assert improved["delta"] == {
        "before": 40.0,
        "after": SLOPPY_PER100W,
        "improved": True,
    }

    baseline.write_text(json.dumps({"file": str(draft), "total_per100w": 1.0}), encoding="utf-8")
    worse = json.loads(run_lint("--json", "--baseline", str(baseline), str(draft)).stdout)
    assert worse["delta"] == {"before": 1.0, "after": SLOPPY_PER100W, "improved": False}

    baseline.write_text(
        json.dumps({"file": str(draft), "total_per100w": SLOPPY_PER100W}), encoding="utf-8"
    )
    equal = json.loads(run_lint("--json", "--baseline", str(baseline), str(draft)).stdout)
    assert equal["delta"] == {
        "before": SLOPPY_PER100W,
        "after": SLOPPY_PER100W,
        "improved": False,
    }


def test_a_baseline_for_another_file_reports_no_delta(tmp_path):
    """The delta paired on position, so an unrelated baseline invented one.

    Linting an unedited file against somebody else's baseline reported
    `before 42.86, after 0.0, improved true` for an edit that never happened.
    """
    draft = tmp_path / "draft.md"
    draft.write_text(PLAIN, encoding="utf-8")
    baseline = tmp_path / "before.json"
    baseline.write_text(
        json.dumps({"file": str(tmp_path / "other.md"), "total_per100w": 42.86}), encoding="utf-8"
    )

    report = json.loads(run_lint("--json", "--baseline", str(baseline), str(draft)).stdout)
    assert report["delta"] is None

    # A named current file never pairs with an unnamed baseline report either.
    baseline.write_text(json.dumps({"total_per100w": 42.86}), encoding="utf-8")
    unnamed = json.loads(run_lint("--json", "--baseline", str(baseline), str(draft)).stdout)
    assert unnamed["delta"] is None


def test_a_single_unnamed_baseline_pairs_with_a_single_unnamed_run(tmp_path):
    baseline = tmp_path / "before.json"
    baseline.write_text(json.dumps({"total_per100w": 40.0}), encoding="utf-8")

    piped = run_lint("--json", "--baseline", str(baseline), stdin=SLOPPY)
    assert json.loads(piped.stdout)["delta"] == {
        "before": 40.0,
        "after": SLOPPY_PER100W,
        "improved": True,
    }

    baseline.write_text(
        json.dumps([{"total_per100w": 40.0}, {"total_per100w": 3.0}]), encoding="utf-8"
    )
    ambiguous = run_lint("--json", "--baseline", str(baseline), stdin=SLOPPY)
    assert json.loads(ambiguous.stdout)["delta"] is None


def test_an_unreadable_path_is_reported_and_the_run_continues(tmp_path):
    plain = tmp_path / "plain.md"
    plain.write_text(PLAIN, encoding="utf-8")
    binary = tmp_path / "logo.png"
    binary.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00")
    missing = tmp_path / "gone.md"
    directory = tmp_path / "docs"
    directory.mkdir()

    result = run_lint("--json", str(missing), str(binary), str(directory), str(plain))
    reports = json.loads(result.stdout)

    assert result.returncode == 2
    assert [Path(entry["file"]).name for entry in reports] == [
        "gone.md",
        "logo.png",
        "docs",
        "plain.md",
    ]
    assert all("error" in entry for entry in reports[:3])
    # The good file still carries its whole report.
    assert reports[3]["total_per100w"] == 0.0
    assert "error" not in reports[3]

    lines = run_lint(str(missing), str(plain))
    assert lines.returncode == 2
    assert "error=" in lines.stdout
    assert lines.stdout.rstrip().endswith("ok")


def test_a_file_that_is_not_utf8_is_scored_with_replacement(tmp_path):
    draft = tmp_path / "latin1.md"
    draft.write_bytes("The café build failed.".encode("latin-1"))

    result = run_lint("--json", str(draft))
    report = json.loads(result.stdout)

    assert result.returncode == 0
    assert report["words"] == 4
    assert report["total"] == 0


def test_a_broken_baseline_is_reported_without_losing_the_reports(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(SLOPPY, encoding="utf-8")
    broken = tmp_path / "before.json"
    broken.write_text("{not json", encoding="utf-8")

    malformed = run_lint("--json", "--baseline", str(broken), str(draft))
    report = json.loads(malformed.stdout)
    assert malformed.returncode == 2
    assert "baseline unreadable" in malformed.stderr
    assert report["total_per100w"] == SLOPPY_PER100W
    assert report["delta"] is None

    missing = run_lint("--json", "--baseline", str(tmp_path / "gone.json"), str(draft))
    assert missing.returncode == 2
    assert "baseline unreadable" in missing.stderr
    assert json.loads(missing.stdout)["total_per100w"] == SLOPPY_PER100W


def test_output_survives_a_console_that_is_not_utf8(tmp_path):
    """A report line carries whatever the file name carries, so stdout is UTF-8.

    `json.dump` escapes its own non-ASCII, but the plain report line prints the
    file name as it is, and an accented name on an ASCII console kills the run
    on the write rather than on anything about the prose.
    """
    draft = tmp_path / "café.md"
    draft.write_text("The build failed — the cache was stale.\n", encoding="utf-8")
    ascii_console = {**os.environ, "PYTHONIOENCODING": "ascii"}

    lines = subprocess.run(
        [sys.executable, str(SCRIPT), str(draft)],
        capture_output=True,
        check=False,
        env=ascii_console,
    )
    scored = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", str(draft)],
        capture_output=True,
        check=False,
        env=ascii_console,
    )

    assert lines.returncode == 0, lines.stderr.decode("utf-8", "replace")
    assert lines.stdout.decode("utf-8").startswith("café.md")
    assert json.loads(scored.stdout.decode("utf-8"))["samples"]["em_dash"] == ["—"]


def test_quote_safe_reaches_the_cli(tmp_path):
    glossary = tmp_path / "glossary.md"
    glossary.write_text(GLOSSARY, encoding="utf-8")

    scored = json.loads(run_lint("--json", str(glossary)).stdout)
    safe = json.loads(run_lint("--json", "--quote-safe", str(glossary)).stdout)

    assert scored["total"] == GLOSSARY_TOTAL
    assert safe["total"] == GLOSSARY_SAFE_TOTAL
    assert safe["quote_safe"] is True


def test_help_lists_every_flag():
    result = run_lint("--help")
    help_text = result.stdout

    assert result.returncode == 0
    for flag in ("--register", "--strict", "--quote-safe", "--json", "--fail-over", "--baseline"):
        assert flag in help_text
    assert "python3" in help_text


# --------------------------------------------------------------------------
# Hard wrapping
# --------------------------------------------------------------------------

# One sentence of 27 words and one of 17, wrapped at eighty columns the way
# every markdown file in this repository is.
WRAPPED = (
    "The operator reconciles the Deployment whenever the ConfigMap changes,\n"
    "and it restarts the backend container so that the dynamic plugins load in\n"
    "the order the catalog lists them, which the marketplace plugin then shows.\n"
    "The marketplace plugin reads that catalog and shows which version of each\n"
    "plugin the cluster currently runs today.\n"
)


def test_a_hard_wrapped_paragraph_reads_as_whole_sentences():
    """Splitting on newlines hid the long sentences and invented short ones."""
    module = load_lint()

    wrapped = module.lint(WRAPPED, register="review")
    joined = module.lint(" ".join(WRAPPED.split()), register="review")

    assert wrapped["sentences"] == joined["sentences"] == 2
    assert wrapped["longest_sentence_words"] == joined["longest_sentence_words"] == 34
    assert wrapped["violations"]["long_sentence"] == joined["violations"]["long_sentence"] == 1


def test_a_wrapped_paragraph_is_not_a_long_paragraph():
    """Seven wrapped lines are two sentences, not seven, so the cap of six holds."""
    module = load_lint()
    seven_lines = (
        "The overlay reads the plugin version from the package manifest and\n"
        "writes it into the export overlay so that the release pipeline can\n"
        "build the dynamic plugin without any manual edit to the repository at\n"
        "all. The catalog then records the version it built together with the\n"
        "digest of the image that carries it, which is what the marketplace\n"
        "plugin shows to an administrator who is deciding whether an upgrade is\n"
        "worth taking today.\n"
    )

    report = module.lint(seven_lines, register="review")

    assert report["sentences"] == 2
    assert report["violations"]["long_paragraph"] == 0


def test_a_list_item_is_its_own_unit():
    module = load_lint()
    items = (
        "- The operator reconciles the Deployment whenever the ConfigMap\n"
        "  changes and restarts the backend.\n"
        "- The marketplace plugin reads the catalog.\n"
    )

    assert module.logical_lines(items) == [
        "- The operator reconciles the Deployment whenever the ConfigMap changes"
        " and restarts the backend.",
        "- The marketplace plugin reads the catalog.",
    ]
    assert module.lint(items)["sentences"] == 2


def test_a_seven_sentence_paragraph_still_scores_long_paragraph():
    module = load_lint()
    block = " ".join(f"The pod restarts {index} times." for index in range(7))

    assert module.lint(block)["violations"]["long_paragraph"] == 1
    assert module.lint(" ".join(block.split(". ")[:6]))["violations"]["long_paragraph"] == 0


# --------------------------------------------------------------------------
# Precision
# --------------------------------------------------------------------------


def test_a_possessive_is_not_a_contraction():
    """`s` sat in the general branch, so every possessive scored a contraction."""
    module = load_lint()

    possessive = module.lint(
        "The skill's reference, the plugin's version, and the user's token stay."
    )
    genuine = module.lint("It's ready. Don't stop. We've shipped. He's late. I'm done.")

    assert possessive["violations"]["contraction"] == 0
    assert genuine["violations"]["contraction"] == 5


def test_negative_parallelism_needs_the_antithesis_shape():
    module = load_lint()
    tell = module.lint("The overlay reads the version from the plugin manifest, no manual bumps.")
    conditional = module.lint("If validation fails, no installation operation runs.")
    one_word = module.lint("The script uses the standard library, no lockfile.")
    enumeration = module.lint("Skills compose by stable name, no imports, no layout probing.")
    list_item = module.lint("- Draft in a triple-backtick block, no placeholders left unfilled\n")

    assert tell["violations"]["negative_parallelism"] == 1
    assert conditional["violations"]["negative_parallelism"] == 0
    assert one_word["violations"]["negative_parallelism"] == 0
    assert enumeration["violations"]["negative_parallelism"] == 0
    assert list_item["violations"]["negative_parallelism"] == 0


def test_nominalization_needs_a_noun_that_names_an_action():
    module = load_lint()
    action = module.lint("The installation of the plugin precedes the migration of the data.")
    things = module.lint(
        "An instance of the class, the distance of the run, and the sentence of the paragraph.",
        register="review",
    )

    assert action["violations"]["nominalization"] == 2
    assert things["violations"]["nominalization"] == 0


def test_passive_voice_leaves_predicate_adjectives_alone():
    module = load_lint()
    report = module.lint(
        "The field is indeed correct. The value is missing. The token is required.",
        register="review",
    )
    real = module.lint("The chart was installed by the operator. The pod is restarted.")

    assert report["violations"]["passive_voice"] == 0
    assert report["violations"]["ing_main_verb"] == 0
    assert real["violations"]["passive_voice"] == 2


def test_one_verb_phrase_and_one_apostrophe_score_once():
    module = load_lint()
    perfect = module.lint("The chart has been deployed to the cluster.", register="review")
    curly = module.lint("It doesn’t restart. The operator’s log is short.", register="review")
    utilization = module.lint("The utilization of the cache is high.", register="review")

    assert perfect["violations"]["complex_tense"] == 1
    assert perfect["violations"]["passive_voice"] == 0

    # The contraction owns its apostrophe; the possessive one is still a curly
    # quote, because no other category scored it.
    assert curly["violations"]["contraction"] == 1
    assert curly["violations"]["curly_quote"] == 1

    assert utilization["violations"]["ai_vocabulary"] == 1
    assert utilization["violations"]["nominalization"] == 0


def test_matrix_marks_and_arrows_are_not_emoji():
    module = load_lint()
    matrix = module.lint("Supported ✓ and unsupported ✗ and the pointer ⬅ stay.")
    pictographs = module.lint("🚀 The build shipped. ✅ Tests pass.")

    assert matrix["violations"]["emoji"] == 0
    assert pictographs["violations"]["emoji"] == 2


def test_a_hyphenated_word_does_not_trip_a_banned_word():
    module = load_lint()

    followup = module.lint("Follow-up items stay open.", register="strict")
    verb = module.lint("Follow the runbook.", register="strict")

    assert followup["violations"]["strict_banned_word"] == 0
    assert verb["violations"]["strict_banned_word"] == 1


def test_provided_as_a_conjunction_is_not_a_verbose_verb():
    module = load_lint()

    conjunction = module.lint("Provided the token is valid, the request succeeds.")
    also_conjunction = module.lint("The call succeeds provided that the token is valid.")
    verb = module.lint("The operator provided the token.")

    assert conjunction["violations"]["verbose_word"] == 0
    assert also_conjunction["violations"]["verbose_word"] == 0
    assert verb["violations"]["verbose_word"] == 1


def test_false_ranges_stay_linear_on_a_large_document():
    """The check re-split the whole prefix per candidate, so 870KB took 17s."""
    module = load_lint()
    document = "The catalog covers everything from user onboarding to cost reporting. " * 16000

    started = time.monotonic()
    count, _ = module.false_ranges(document)
    elapsed = time.monotonic() - started

    assert count == 16000
    assert elapsed < 3.0, f"false_ranges took {elapsed:.1f}s on {len(document)} characters"


# --------------------------------------------------------------------------
# Structure that must not swallow the document
# --------------------------------------------------------------------------


def test_a_leading_thematic_break_is_not_frontmatter():
    """A document may open on a horizontal rule and close a section with another.

    Reading the first one as frontmatter blanked everything down to the second
    and turned an over-bar draft into a clean one.
    """
    module = load_lint()
    text = (
        "---\n\n"
        "This seamless platform will leverage cutting-edge tooling to supercharge docs.\n\n"
        "---\n\n"
        "The parser reads the file.\n"
    )

    report = module.lint(text)

    assert report["words"] == 15
    assert report["violations"]["ai_vocabulary"] == 2
    assert report["violations"]["promotional"] == 2
    assert report["over_bar"] is True

    frontmatter = module.lint("---\nname: prose-editing\n---\n\nThe parser reads the file.\n")
    assert frontmatter["words"] == 5


def test_an_unclosed_code_fence_does_not_delete_the_rest_of_the_document():
    module = load_lint()
    unclosed = "```\nThis seamless platform will leverage cutting-edge tooling.\n"
    closed = "```\nThis seamless platform will leverage cutting-edge tooling.\n```\n"

    assert module.lint(unclosed)["words"] == 7
    assert module.lint(unclosed)["total"] == 3
    assert module.lint(closed)["total"] == 0


def test_a_bare_url_is_not_prose():
    module = load_lint()

    report = module.lint("See https://example.com/leverage for the robust story.")

    assert report["words"] == 5
    assert report["violations"]["ai_vocabulary"] == 1


def test_a_link_reference_definition_is_not_prose():
    module = load_lint()

    report = module.lint("The parser reads the file.\n\n[robust]: https://example.com/x\n")

    assert report["words"] == 5
    assert report["total"] == 0


def test_samples_stop_at_six_hits():
    module = load_lint()
    text = (
        "It will leverage a seamless and robust landscape of intricate, nuanced,"
        " multifaceted realms and myriad tapestry."
    )

    report = module.lint(text)

    # "realms" is not "realm", so nine of the ten words score.
    assert report["violations"]["ai_vocabulary"] == 9
    assert len(report["samples"]["ai_vocabulary"]) == 6
    assert module.SAMPLE_LIMIT == 6


# --------------------------------------------------------------------------
# The tells the reference files teach
# --------------------------------------------------------------------------


def test_staccato_counts_the_run_and_not_the_sentence_length():
    module = load_lint()
    documented = (
        "Then the marketplace shipped. No more editing ConfigMaps by hand. No"
        " more waiting on a rebuild. No more guessing which version you had."
        " The old workflow was gone."
    )
    seven = "Alpha beta gamma delta epsilon zeta eta. " * 3
    eight = "Alpha beta gamma delta epsilon zeta eta theta. " * 3
    two_in_a_row = "The pod restarts. The build fails."

    assert module.lint(documented, register="voiced")["violations"]["staccato_drama"] == 1
    assert module.lint(seven, register="voiced")["violations"]["staccato_drama"] == 1
    assert module.lint(eight, register="voiced")["violations"]["staccato_drama"] == 0
    assert module.lint(two_in_a_row, register="voiced")["violations"]["staccato_drama"] == 0
    assert module.STACCATO_MAX_WORDS == 7
    assert module.STACCATO_RUN == 3


def test_generic_conclusion_matches_the_shape_not_one_wording():
    module = load_lint()

    for text in (
        "The future of the platform is bright.",
        "The future looks bright.",
        "In conclusion, the work continues.",
        "In summary, the work continues.",
        "The possibilities are endless.",
        "Exciting times ahead.",
        "The road ahead is long.",
        "## Conclusion\n\nThe release shipped.\n",
    ):
        assert module.lint(text)["violations"]["generic_conclusion"] >= 1, text


def test_significance_inflation_covers_the_inflected_forms():
    module = load_lint()

    for text in (
        "The release sets the stage for 1.11.",
        "Setting the stage for 1.11, the team shipped.",
        "This set the stage for the migration.",
        "The release marks a pivotal moment for the platform.",
        "It underscores our ongoing commitment to the community.",
        "It underscores our commitment to the community.",
        "The release marks a turning point.",
    ):
        assert module.lint(text)["violations"]["significance_inflation"] >= 1, text


def test_every_documented_example_scores_the_category_it_teaches():
    """The acceptance test: the reference files and the linter must agree.

    Each `### \\`category\\`` section opens with the example of the tell. When
    the linter scores it zero, the skill is teaching a rule its own tool cannot
    find.
    """
    module = load_lint()
    examples = documented_examples()
    assert len(examples) >= 18

    missed = []
    for category, example, path in examples:
        report = module.lint(example, register="review")
        count = report["violations"].get(category, report["markers"].get(category))
        assert count is not None, f"{path.name} documents an unknown category {category}"
        if not count:
            missed.append((path.name, category, example[:60]))

    assert missed == []


def test_the_documented_rewrites_score_nothing_in_their_category():
    """The other half: the reference files' own fixes have to come out clean."""
    module = load_lint()
    rewrites = {
        "ai_vocabulary": "The marketplace plugin reads the catalog and lists the plugins.",
        "copula_avoidance": "The dynamic-plugins ConfigMap lists the enabled plugins.",
        "negative_parallelism": "The operator creates the Deployment and the Route.",
        "significance_inflation": "Red Hat Developer Hub 1.10 is generally available today.",
        "staccato_drama": (
            "The marketplace plugin removed the manual ConfigMap edits that"
            " installing a plugin used to require, and it shows the version."
        ),
        "boldface_overuse": "RHDH 1.10 ships the marketplace plugin and adds RBAC support.",
    }

    for category, rewrite in rewrites.items():
        report = module.lint(rewrite, register="review")
        assert report["violations"][category] == 0, (category, rewrite)


# --------------------------------------------------------------------------
# The modern marketing register
# --------------------------------------------------------------------------


def test_every_marketing_term_scores_somewhere():
    module = load_lint()

    unscored = [
        term for term in MARKETING_TERMS if module.lint(f"The team {term} the file.")["total"] < 1
    ]

    assert unscored == []


def test_an_ai_marketing_page_lands_far_over_every_bar():
    """235 words of this scored 2.13 flavored and 1.70 voiced, under both bars."""
    module = load_lint()
    page = (
        "In today's fast-paced world, engineering organizations find themselves"
        " at a crossroads. As they navigate the complexities of an ever-evolving"
        " cloud landscape, the need for a robust and scalable developer portal"
        " has never been more crucial.\n\n"
        "Our next-generation platform is a game changer that empowers teams to"
        " streamline their workflows, elevate the developer experience, and"
        " unlock the power of a seamless internal platform. By leveraging"
        " cutting-edge tooling and best-in-class automation, it delivers a"
        " comprehensive, holistic solution that fosters collaboration and"
        " bolsters productivity.\n\n"
        "Let's dive in. Teams can harness the power of dynamic plugins without a"
        " single line of glue code, which underscores our ongoing commitment to"
        " developer productivity and marks a pivotal moment in the evolution of"
        " the platform.\n\n"
        "In conclusion, the possibilities are endless, and the future of the"
        " platform is bright. Exciting times ahead.\n"
    )

    flavored = module.lint(page)
    voiced = module.lint(page, register="voiced")

    assert flavored["words"] > 130
    assert flavored["total_per100w"] > 10.0
    assert flavored["over_bar"] is True
    assert voiced["total_per100w"] > 10.0
    assert voiced["over_bar"] is True
