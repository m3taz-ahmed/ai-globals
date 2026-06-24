#!/usr/bin/env python3
"""Unit tests for validate-globals.py checks. Run from repo root: python scripts/tests/test_validator.py"""

import sys
import os
import unittest

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "validate_globals",
    os.path.join(os.path.dirname(__file__), "..", "validate-globals.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ValidationContext = _mod.ValidationContext
is_ai_file = _mod.is_ai_file
_has_yaml_frontmatter_name = _mod._has_yaml_frontmatter_name
check_title = _mod.check_title
check_struct = _mod.check_struct
check_line_endings = _mod.check_line_endings
check_utf8_bom = _mod.check_utf8_bom
check_secrets = _mod.check_secrets
check_mojibake = _mod.check_mojibake
check_symbolic_codes = _mod.check_symbolic_codes
check_trailing_newlines = _mod.check_trailing_newlines
_body_after_frontmatter = _mod._body_after_frontmatter

GLOBAL_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ctx(**kwargs) -> ValidationContext:
    ctx = ValidationContext(fix=False, interactive=False, dry_run=False, force=False)
    vocab_path = os.path.join(GLOBAL_PATH, "rules", "vocabulary.md")
    if os.path.exists(vocab_path):
        import re
        with open(vocab_path, 'r', encoding='utf-8') as f:
            for m in re.finditer(r"\[([A-Z]{3,4}-\d{2})\]", f.read()):
                ctx.defined_codes.add(m.group(1))
    for k, v in kwargs.items():
        setattr(ctx, k, v)
    return ctx


class TestIsAiFile(unittest.TestCase):
    def test_file_tag(self):
        self.assertTrue(is_ai_file("[FILE] foo\n[OBJ] x\n[RULES]\n"))

    def test_skill_tag(self):
        self.assertTrue(is_ai_file("[SKILL] foo\n[OBJ] x\n[RULES]\n"))

    def test_workflow_tag(self):
        self.assertTrue(is_ai_file("[WORKFLOW] foo\n[OBJ] x\n[RULES]\n"))

    def test_tech_tag(self):
        self.assertTrue(is_ai_file("[TECH] foo\n[OBJ] x\n[RULES]\n"))

    def test_frontmatter_with_skill(self):
        self.assertTrue(is_ai_file("---\nname: foo\n---\n[SKILL] foo\n[OBJ] x\n[RULES]\n"))

    def test_human_doc(self):
        self.assertFalse(is_ai_file("# My Human Doc\n\nSome text.\n"))

    def test_frontmatter_only(self):
        self.assertFalse(is_ai_file("---\nname: foo\ndescription: bar\n---\nPlain body.\n"))


class TestCheckTitle(unittest.TestCase):
    def test_ai_tag_passes(self):
        ctx = _ctx()
        self.assertFalse(check_title("[FILE] foo\n[OBJ] x\n[RULES]\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 0)

    def test_h1_passes(self):
        ctx = _ctx()
        self.assertFalse(check_title("# My Title\n\nContent.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 0)

    def test_html_h1_passes(self):
        ctx = _ctx()
        self.assertFalse(check_title("<h1>Title</h1>\n\nContent.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 0)

    def test_yaml_name_passes(self):
        ctx = _ctx()
        self.assertFalse(check_title("---\nname: myskill\n---\nBody.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 0)

    def test_no_title_fails(self):
        ctx = _ctx()
        self.assertTrue(check_title("No title here.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 1)


class TestCheckStruct(unittest.TestCase):
    def test_full_ai_file_passes(self):
        ctx = _ctx()
        self.assertFalse(check_struct("[FILE] foo\n[OBJ] x\n[RULES]\n1. [REQ] y.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 0)

    def test_missing_obj_fails(self):
        ctx = _ctx()
        self.assertTrue(check_struct("[FILE] foo\n[RULES]\n1. [REQ] y.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 1)

    def test_missing_rules_fails(self):
        ctx = _ctx()
        self.assertTrue(check_struct("[FILE] foo\n[OBJ] x\nNo rules.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 1)

    def test_human_doc_skipped(self):
        ctx = _ctx()
        self.assertFalse(check_struct("# Human Doc\nContent.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 0)

    def test_frontmatter_only_skipped(self):
        ctx = _ctx()
        self.assertFalse(check_struct("---\nname: foo\n---\nBody.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 0)


class TestCheckLineEndings(unittest.TestCase):
    def test_lf_passes(self):
        ctx = _ctx()
        _, modified = check_line_endings("line1\nline2\n", "test.md", ctx)
        self.assertFalse(modified)
        self.assertEqual(ctx.warning_count, 0)

    def test_crlf_warns(self):
        ctx = _ctx()
        _, modified = check_line_endings("line1\r\nline2\r\n", "test.md", ctx)
        self.assertFalse(modified)
        self.assertEqual(ctx.warning_count, 1)

    def test_crlf_fix(self):
        ctx = _ctx(fix=True)
        content, modified = check_line_endings("line1\r\nline2\r\n", "test.md", ctx)
        self.assertTrue(modified)
        self.assertNotIn("\r\n", content)


class TestCheckSymbolicCodes(unittest.TestCase):
    def test_defined_code_passes(self):
        ctx = _ctx()
        self.assertFalse(check_symbolic_codes("[FILE] x\n[REQ] Use [SEC-01].\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 0)

    def test_undefined_code_fails(self):
        ctx = _ctx()
        self.assertTrue(check_symbolic_codes("[FILE] x\n[REQ] Use [ZZZ-99].\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 1)

    def test_vocabulary_file_skipped(self):
        ctx = _ctx()
        self.assertFalse(check_symbolic_codes("[ZZZ-99]: Some code.\n", "rules\\vocabulary.md", ctx))
        self.assertEqual(ctx.error_count, 0)


class TestCheckMojibake(unittest.TestCase):
    def test_clean_passes(self):
        ctx = _ctx()
        self.assertFalse(check_mojibake("Clean text. No artifacts.\n", "test.md", ctx))

    def test_replacement_char_fails(self):
        ctx = _ctx()
        self.assertTrue(check_mojibake("Bad \uFFFD char.\n", "test.md", ctx))
        self.assertEqual(ctx.error_count, 1)


class TestCheckTrailingNewlines(unittest.TestCase):
    def test_single_newline_passes(self):
        ctx = _ctx()
        _, mod = check_trailing_newlines("content\n", "test.md", ctx)
        self.assertFalse(mod)
        self.assertEqual(ctx.warning_count, 0)

    def test_missing_newline_warns(self):
        ctx = _ctx()
        _, mod = check_trailing_newlines("content", "test.md", ctx)
        self.assertFalse(mod)
        self.assertEqual(ctx.warning_count, 1)

    def test_double_newline_warns(self):
        ctx = _ctx()
        _, mod = check_trailing_newlines("content\n\n", "test.md", ctx)
        self.assertFalse(mod)
        self.assertEqual(ctx.warning_count, 1)

    def test_missing_newline_fixed(self):
        ctx = _ctx(fix=True)
        content, mod = check_trailing_newlines("content", "test.md", ctx)
        self.assertTrue(mod)
        self.assertTrue(content.endswith("\n"))


class TestFrontmatter(unittest.TestCase):
    def test_strips_frontmatter(self):
        body = _body_after_frontmatter("---\nname: foo\n---\n[SKILL] foo\n")
        self.assertTrue(body.startswith("[SKILL]"))

    def test_no_frontmatter(self):
        body = _body_after_frontmatter("[FILE] foo\n")
        self.assertTrue(body.startswith("[FILE]"))

    def test_yaml_name_detection(self):
        self.assertTrue(_has_yaml_frontmatter_name("---\nname: foo\n---\nbody\n"))
        self.assertFalse(_has_yaml_frontmatter_name("---\ndescription: foo\n---\nbody\n"))
        self.assertFalse(_has_yaml_frontmatter_name("# Title\nbody\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
