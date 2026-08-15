#!/usr/bin/env python3
"""Tests for runtime/rule_compiler."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.rule_compiler import RuleIR, compile_rule_file, compile_rules, to_json
from runtime.rule_compiler import _code_prefix, _parse_rules, _split_rules_section


def _write_rule_file(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / f"{name}.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_compile_synthetic_rule_file(tmp_path: Path) -> None:
    """Compile a synthetic rule file and verify entries, kinds, and codes."""
    content = """\
---
personas: [DEV, ARCH]
always: true
---
[FILE] synthetic
[OBJ] Test parsing of rule compiler.
[RULES]
1. [REQ] [CODE-01] Service-Repo separation. Thin controllers.
2. [PROHIBIT] Logic in Controllers: never put domain logic there.
3. [CMD] L0: Load the runtime context.
4. [REQ] Think Before Coding [BEH-01]: state assumptions first.
"""
    path = _write_rule_file(tmp_path, "synthetic", content)
    rule = compile_rule_file(path)

    assert isinstance(rule, RuleIR)
    assert rule.file == "synthetic"
    assert rule.obj == "Test parsing of rule compiler."
    assert rule.frontmatter["personas"] == ["DEV", "ARCH"]
    assert rule.frontmatter["always"] is True
    assert len(rule.rules) == 4

    assert rule.rules[0].index == 1
    assert rule.rules[0].kind == "REQ"
    assert rule.rules[0].code == "CODE-01"
    assert "Service-Repo separation" in rule.rules[0].text

    assert rule.rules[1].kind == "PROHIBIT"
    assert rule.rules[1].code is None
    assert "Logic in Controllers" in rule.rules[1].text

    assert rule.rules[2].kind == "CMD"
    assert rule.rules[2].code is None
    assert rule.rules[2].text.startswith("L0:")

    assert rule.rules[3].kind == "REQ"
    assert rule.rules[3].code == "BEH-01"
    assert "Think Before Coding" in rule.rules[3].text


def test_compile_core_behavioral_compact() -> None:
    """Load rules/core-behavioral-compact.md and assert basic structure."""
    root = Path(__file__).resolve().parents[2]
    path = root / "rules" / "core-behavioral-compact.md"
    rule = compile_rule_file(path)

    assert rule.file == "core-behavioral-compact"
    assert rule.obj
    assert len(rule.rules) > 0
    assert rule.rules[0].kind == "REQ"
    assert rule.rules[0].code == "BEH-01"
    assert any(r.code == "BEH-04" for r in rule.rules)


def test_compile_vocabulary_extracts_codes() -> None:
    """Load rules/vocabulary.md and verify symbolic codes are extracted."""
    root = Path(__file__).resolve().parents[2]
    path = root / "rules" / "vocabulary.md"
    rule = compile_rule_file(path)

    assert rule.file == "vocabulary"
    assert rule.obj
    assert len(rule.rules) > 0

    codes = [r.code for r in rule.rules]
    assert "BEH-01" in codes
    assert "SEC-03" in codes
    assert "PERF-07" in codes
    assert "VER-01" in codes
    assert "SaaS-04" in codes
    assert all(r.code is not None for r in rule.rules)
    assert all(r.kind for r in rule.rules)


def test_compile_anti_patterns_has_prohibit_code() -> None:
    """Load rules/anti-patterns.md and verify a [PROHIBIT] code is extracted."""
    root = Path(__file__).resolve().parents[2]
    path = root / "rules" / "anti-patterns.md"
    rule = compile_rule_file(path)

    assert rule.file == "anti-patterns"
    prohibit = [r for r in rule.rules if r.kind == "PROHIBIT"]
    assert prohibit
    assert any(r.code == "VER-01" for r in prohibit)


def test_to_json_round_trip(tmp_path: Path) -> None:
    """Serialize and deserialize a compiled rule via JSON."""
    content = """\
[FILE] roundtrip
[OBJ] Round-trip test.
[RULES]
1. [REQ] [RT-01] A sample rule.
"""
    path = _write_rule_file(tmp_path, "roundtrip", content)
    rule = compile_rule_file(path)

    payload = to_json([rule])
    data = json.loads(payload)
    assert isinstance(data, list)
    assert data[0]["file"] == "roundtrip"
    assert data[0]["rules"][0]["kind"] == "REQ"
    assert data[0]["rules"][0]["code"] == "RT-01"
    assert data[0]["source"] == str(path)


def test_compile_rules_with_custom_glob(tmp_path: Path) -> None:
    """Compile a directory using a custom glob."""
    _write_rule_file(tmp_path, "alpha", "[FILE] alpha\n[OBJ] A.\n[RULES]\n1. [REQ] Rule A.\n")
    _write_rule_file(tmp_path, "beta", "[FILE] beta\n[OBJ] B.\n[RULES]\n1. [PROHIBIT] Rule B.\n")

    results = compile_rules(tmp_path, globs=["*.md"])
    files = {r.file for r in results}
    assert "alpha" in files
    assert "beta" in files
    assert all(r.source.parent == tmp_path for r in results)


# ---------------------------------------------------------------------------
# Coverage for internal helpers and edge cases
# ---------------------------------------------------------------------------

def test_code_prefix_extracts_category() -> None:
    """Cover line 52: _code_prefix returns the category prefix."""
    assert _code_prefix("BEH-01") == "BEH"
    assert _code_prefix("SEC-03") == "SEC"


def test_split_rules_section_no_rules_tag() -> None:
    """Cover line 64: _split_rules_section returns (body, '') when no [RULES] tag."""
    body = "[FILE] test\n[OBJ] No rules here.\n"
    prefix, rules = _split_rules_section(body)
    assert prefix == body
    assert rules == ""


def test_parse_rules_stops_at_tag() -> None:
    """Cover line 80: parsing stops when a stop tag like [FILE] is encountered."""
    section = "1. [REQ] First rule.\n[FILE] next-section\n2. [REQ] Should not parse.\n"
    entries = _parse_rules(section)
    assert len(entries) == 1
    assert entries[0].text == "First rule."


def test_parse_rules_bullet_without_bracket_skipped() -> None:
    """Cover line 97: lines not starting with [ are skipped."""
    section = "- some plain text\n1. [REQ] Real rule.\n"
    entries = _parse_rules(section)
    assert len(entries) == 1
    assert entries[0].kind == "REQ"


def test_parse_rules_bullet_stripped() -> None:
    """Cover line 94: bullet prefix is stripped before parsing."""
    section = "* [REQ] Bullet rule.\n"
    entries = _parse_rules(section)
    assert len(entries) == 1
    assert entries[0].kind == "REQ"
    assert entries[0].text == "Bullet rule."


def test_parse_rules_parts_not_starting_with_bracket_skipped() -> None:
    """Cover line 101: when first part doesn't start with [, the line is skipped."""
    section = "1. plain text without bracket\n"
    entries = _parse_rules(section)
    assert len(entries) == 0


def test_parse_rules_empty_text_skipped() -> None:
    """Cover line 128: rules with empty text after stripping are skipped."""
    section = "1. [REQ] :\n"
    entries = _parse_rules(section)
    assert len(entries) == 0


def test_parse_rules_code_as_first_token() -> None:
    """Cover line 52 via _code_prefix: when the first token is a code like [BEH-01]."""
    section = "1. [BEH-01] Some behavioral rule.\n"
    entries = _parse_rules(section)
    assert len(entries) == 1
    assert entries[0].code == "BEH-01"
    assert entries[0].kind == "BEH"
    assert entries[0].text == "Some behavioral rule."


def test_compile_rules_default_globs(tmp_path: Path) -> None:
    """Cover line 157: compile_rules uses default globs when none provided."""
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "test.md").write_text(
        "[FILE] test\n[OBJ] Test.\n[RULES]\n1. [REQ] Rule.\n", encoding="utf-8"
    )
    results = compile_rules(tmp_path)
    assert any(r.file == "test" for r in results)


def test_parse_rules_incomplete_bracket_skipped() -> None:
    """Cover line 101: first part starts with [ but doesn't end with ]."""
    section = "1. [incomplete bracket text\n"
    entries = _parse_rules(section)
    assert len(entries) == 0


def test_parse_rules_empty_kind_skipped() -> None:
    """Cover line 122: kind is empty (token from [] is empty string)."""
    section = "1. [] some text\n"
    entries = _parse_rules(section)
    assert len(entries) == 0
