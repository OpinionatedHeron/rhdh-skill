#!/usr/bin/env python3
"""Score technical prose for slop. Stdlib only.

Heuristics adapted from Ege Çelebi's STE kit (MIT), with always-on checks for
em dashes, chatbot residue, copula avoidance, and "it's not just" parallelism.
Not a certified ASD-STE100 checker. Do not paste the ASD dictionary here.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCORE_VERSION = 3
FLAVORED_BAR = 2.5
STRICT_BAR = 1.5

# Adapted from the STE kit score v2 lists.
MARKETING = (
    "seamless",
    "seamlessly",
    "robust",
    "powerful",
    "cutting-edge",
    "effortless",
    "effortlessly",
    "world-class",
    "next-generation",
    "revolutionary",
    "blazing",
    "lightning-fast",
    "elegant",
    "delightful",
    "turnkey",
    "best-in-class",
    "state-of-the-art",
    "game-changing",
    "first-class",
    "battle-tested",
    "enterprise-grade",
    "supercharge",
    "unlock",
    "unleash",
    "empower",
    "empowers",
)
BANNED = (
    "begin",
    "begins",
    "commence",
    "commences",
    "initiate",
    "initiates",
    "originate",
    "utilize",
    "utilizes",
    "utilizing",
    "leverage",
    "leverages",
    "leveraging",
    "facilitate",
    "facilitates",
    "ensure",
    "ensures",
    "ensuring",
    "prior to",
    "subsequent to",
    "obtain",
    "obtains",
    "acquire",
    "acquires",
    "demonstrate",
    "demonstrates",
    "additionally",
    "furthermore",
    "moreover",
    "comprehensive",
    "comprehensively",
    "utilization",
    "aforementioned",
    "henceforth",
    "therein",
    "whilst",
    "amongst",
    "numerous",
    "myriad",
    "plethora",
    "provide",
    "provides",
    "provided",
    "in order to",
    "a variety of",
    "in the event that",
    "due to the fact that",
    "it is important to note",
)
STRICT_BANNED = (
    "however",
    "since",
    "should",
    "shall",
    "using",
    "follow",
    "follows",
    "followed",
)
PHRASAL = (
    "spin up",
    "spin down",
    "reach out",
    "dive into",
    "dives into",
    "diving into",
    "kick off",
    "kicks off",
    "roll out",
    "rolls out",
    "tear down",
    "ramp up",
    "circle back",
    "drill down",
    "spun up",
    "reaching out",
)
MODAL_HEDGE = (
    "it is important to note",
    "it should be noted",
    "it is worth noting",
    "please note that",
    "as mentioned",
    "as noted above",
)
CHATBOT_RESIDUE = (
    "i hope this helps",
    "let me know if",
    "would you like",
    "you're absolutely right",
    "of course!",
    "here is a",
    "here is an",
)
COPULA_AVOIDANCE = ("serves as", "stands as")

BE = r"(?:am|is|are|was|were|be|been|being)"
PP_IRREG = (
    r"(?:done|made|sent|read|built|kept|held|set|put|run|written|shown|"
    r"given|taken|found|got|gotten|seen|known|thrown|drawn)"
)
STATIVE = (
    r"(?:closed|opened?|damaged|completed?|installed|connected|required|"
    r"expected|configured|enabled|disabled|deprecated|supported)"
)
FUNC_WORDS = set(
    """a an the this that these those of for to in on at by with from as and or but if
when then than not no is are was were be been being am do does did has have had will would can could
may might must should shall it its their your our his her they we you i""".split()
)
CONTRACTION = re.compile(r"\b\w+['’](?:t|re|ve|ll|d|s|m)\b")
NOT_JUST = re.compile(
    r"\bit['’]s not just\b.*?\bit['’]s\b",
    re.IGNORECASE | re.DOTALL,
)


def strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return re.sub(r"`[^`]*`", " ", text)


def sentences(text: str) -> list[str]:
    out: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^\s*#{1,6}\s*", "", stripped)
        stripped = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", stripped)
        if not stripped:
            continue
        for part in re.split(r"(?<=[.!?:])\s+(?=[A-Z0-9\"'\-])", stripped):
            part = part.strip()
            if part:
                out.append(part)
    return out


def word_count(sentence: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-/]*", sentence))


def count_ci(text: str, phrases: tuple[str, ...]) -> tuple[int, list[str]]:
    hits: list[str] = []
    lowered = text.lower()
    for phrase in phrases:
        for _match in re.finditer(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", lowered):
            hits.append(phrase)
    return len(hits), hits


def noun_trains(text: str) -> list[str]:
    hits: list[str] = []
    for sentence in sentences(text):
        words = re.findall(r"[A-Za-z][A-Za-z'\-]*", sentence)[1:]
        run: list[str] = []
        for word in words + [""]:
            if word and word.lower() not in FUNC_WORDS and not word[0].isupper():
                run.append(word)
            else:
                if len(run) >= 4:
                    hits.append(" ".join(run))
                run = []
    return hits


def lint(text: str, strict: bool = False) -> dict[str, Any]:
    raw = text
    text = strip_code(text)
    found = sentences(text)
    words = sum(word_count(sentence) for sentence in found) or 1
    longs = [(word_count(sentence), sentence) for sentence in found if word_count(sentence) > 20]
    marketing_n, marketing_hits = count_ci(text, MARKETING)
    banned_n, banned_hits = count_ci(text, BANNED)
    chatbot_n, chatbot_hits = count_ci(text, CHATBOT_RESIDUE)
    copula_n, _copula_hits = count_ci(text, COPULA_AVOIDANCE)
    phrasal_n, _phrasal_hits = count_ci(text, PHRASAL)
    hedge_n, _hedge_hits = count_ci(text, MODAL_HEDGE)
    em_dash = text.count("—") + text.count("–")
    not_just = len(NOT_JUST.findall(text))
    passive_parts = re.findall(rf"\b{BE}\s+(\w+ed|{PP_IRREG})\b", text, re.I)
    paragraphs = [block for block in re.split(r"\n\s*\n", raw) if block.strip()]
    violations: dict[str, int] = {
        "long_sentence": len(longs),
        "semicolon": text.count(";"),
        "contraction": len(CONTRACTION.findall(text)),
        "passive_voice": sum(1 for part in passive_parts if not re.fullmatch(STATIVE, part, re.I))
        + len(re.findall(rf"\b{BE}\s+{STATIVE}\s+by\b", text, re.I)),
        "complex_tense": len(
            re.findall(
                rf"\b(?:(?:may|might|could|would|should|must|will|shall|can)\s+)?"
                rf"(?:have|has|had)\s+(?:been\s+)?(?:\w+ed|{PP_IRREG})\b",
                text,
                re.I,
            )
        ),
        "ing_main_verb": len(re.findall(rf"\b{BE}\s+\w+ing\b", text, re.I)),
        "nominalization": len(
            re.findall(
                r"\b(?:perform(?:s|ed)?|conduct(?:s|ed)?|carry out|carries out|"
                r"make use of|makes use of)\b",
                text,
                re.I,
            )
        )
        + len(re.findall(r"\b\w{4,}(?:tion|ment|ance|ence)\s+of\b", text, re.I)),
        "phrasal_verb": phrasal_n,
        "banned_word": banned_n,
        "marketing_adjective": marketing_n,
        "modal_hedge": hedge_n,
        "long_paragraph": sum(1 for block in paragraphs if len(sentences(strip_code(block))) > 6),
        "em_dash": em_dash,
        "chatbot_residue": chatbot_n,
        "copula_avoidance": copula_n,
        "not_just_parallelism": not_just,
    }
    if strict:
        strict_n, _strict_hits = count_ci(text, STRICT_BANNED)
        strict_n += len(re.findall(r"(?<![A-Za-z])may(?![a-z])", text))
        violations["strict_banned_word"] = strict_n
    total = sum(violations.values())
    bar = STRICT_BAR if strict else FLAVORED_BAR
    per100 = round(total * 100.0 / words, 2)
    trains = noun_trains(text)
    return {
        "score_version": SCORE_VERSION,
        "mode": "strict" if strict else "flavored",
        "words": words,
        "sentences": len(found),
        "violations": violations,
        "total": total,
        "total_per100w": per100,
        "bar": bar,
        "over_bar": per100 > bar,
        "longest_sentence_words": (
            max(longs)[0] if longs else max((word_count(s) for s in found), default=0)
        ),
        "noun_train": len(trains),
        "samples": {
            "marketing": list(dict.fromkeys(marketing_hits))[:6],
            "banned": list(dict.fromkeys(banned_hits))[:6],
            "chatbot": list(dict.fromkeys(chatbot_hits))[:6],
            "noun_train": trains[:3],
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Score technical prose for slop. Flavored bar is 2.5 violations per "
            "100 words; strict bar is 1.5. Exits 1 when --fail-over is set and "
            "the worst file is over that number."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files to lint. Reads stdin when omitted.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Apply the strict word set and the 1.5 bar (procedures, runbooks, errors).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON even when stdout is a TTY.",
    )
    parser.add_argument(
        "--fail-over",
        type=float,
        metavar="N",
        help="Exit 1 when the worst total_per100w is greater than N.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    want_json = args.json or not sys.stdout.isatty()
    reports: list[dict[str, Any]] = []
    if args.paths:
        for raw_path in args.paths:
            path = Path(raw_path)
            report = lint(path.read_text(encoding="utf-8"), strict=args.strict)
            report["file"] = str(path)
            reports.append(report)
    else:
        reports.append(lint(sys.stdin.read(), strict=args.strict))

    worst = max(report["total_per100w"] for report in reports)
    if want_json:
        payload: Any = reports[0] if len(reports) == 1 else reports
        json.dump(payload, sys.stdout, indent=2)
        print()
    else:
        for report in reports:
            label = Path(report["file"]).name if "file" in report else "-"
            print(
                f"{label:32} words={report['words']:4d} total={report['total']:3d} "
                f"per100w={report['total_per100w']:6.2f} em_dash={report['violations']['em_dash']:2d}"
            )

    if args.fail_over is not None and worst > args.fail_over:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
