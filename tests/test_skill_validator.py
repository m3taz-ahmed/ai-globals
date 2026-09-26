"""Tests for runtime.skill_validator — the ``aizee skill validate`` engine."""

from __future__ import annotations

from pathlib import Path

from runtime.skill_validator import (
    SkillFinding,
    SkillReport,
    _frontmatter,
    _skill_files,
    validate_skills,
)


def _write(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


GOOD = (
    "---\nname: good-skill\ndescription: Use when testing things.\n"
    "triggers: [test]\n---\n[SKILL] good\n[OBJ] x\n[RULES]\n1. [REQ] r\n"
)


def test_finding_and_report_to_dict() -> None:
    f = SkillFinding("s", "error", "R", "m")
    assert f.to_dict() == {"skill": "s", "level": "error", "rule": "R", "message": "m"}
    rep = SkillReport(skills_checked=2, findings=[
        f, SkillFinding("s", "warn", "W", "m2")])
    assert not rep.ok
    assert len(rep.errors) == 1 and len(rep.warnings) == 1
    d = rep.to_dict()
    assert d["skills_checked"] == 2 and d["errors"] == 1 and d["warnings"] == 1
    assert len(d["findings"]) == 2


def test_empty_report_ok() -> None:
    assert SkillReport().ok


def test_skill_files_both_layouts(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _write(skills, "flat-one.md", GOOD)
    _write(skills, "dir-one/SKILL.md", GOOD)
    _write(skills, "dir-no-skill/other.txt", "x")
    _write(skills, "README.md", "# readme")
    _write(skills, "notes.txt", "not md")
    found = dict(_skill_files(skills))
    assert set(found) == {"flat-one", "dir-one"}
    assert _skill_files(tmp_path / "nope") == []


def test_frontmatter_variants() -> None:
    assert _frontmatter("no frontmatter at all") is None
    assert _frontmatter("---\n: bad: yaml: [\n---\n") is None
    assert _frontmatter("---\n- a\n- list\n---\n") is None
    assert _frontmatter(GOOD) == {"name": "good-skill",
                                  "description": "Use when testing things.",
                                  "triggers": ["test"]}


def test_validate_happy_path(tmp_path: Path) -> None:
    _write(tmp_path / "skills", "good-skill.md", GOOD)
    report = validate_skills(tmp_path / "skills")
    assert report.ok and report.skills_checked == 1


def test_validate_flags_all_contract_rules(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    _write(skills, "Bad_Name.md", GOOD.replace("good-skill", "bad-name"))
    _write(skills, "no-fm.md", "plain text\n")
    _write(skills, "mismatch.md", GOOD.replace("name: good-skill", "name: other"))
    _write(skills, "noname.md", "---\ndescription: Use when x.\n---\nbody\n")
    _write(skills, "nodesc.md", "---\nname: nodesc\ntriggers: [x]\n---\nbody\n")
    _write(skills, "toolong.md",
           "---\nname: toolong\ndescription: " + "x" * 1100 + "\n---\n[OBJ] o\n")
    _write(skills, "vague.md",
           "---\nname: vague\ndescription: does stuff quietly\n---\nplain body\n")
    _write(skills, "vague-marker.md",
           "---\nname: vague-marker\ndescription: does stuff quietly\n---\n[TRIGGER] t\n")
    _write(skills, "vague-triggers.md",
           "---\nname: vague-triggers\ndescription: does stuff quietly\ntriggers: [x]\n---\nbody\n")
    report = validate_skills(skills)
    rules = {(f.skill, f.rule) for f in report.findings}
    assert ("Bad_Name", "NAME_KEBAB") in rules
    assert ("Bad_Name", "NAME_MISMATCH") in rules
    assert ("no-fm", "FRONTMATTER") in rules
    assert ("mismatch", "NAME_MISMATCH") in rules
    assert ("noname", "NAME_MISSING") in rules
    assert ("nodesc", "DESCRIPTION_MISSING") in rules
    assert ("toolong", "DESCRIPTION_LEN") in rules
    assert ("vague", "DESCRIPTION_VAGUE") in rules
    # marker/trigger-bearing files must NOT be flagged vague
    assert ("vague-marker", "DESCRIPTION_VAGUE") not in rules
    assert ("vague-triggers", "DESCRIPTION_VAGUE") not in rules


def test_oversized_skill_warns(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import runtime.skill_validator as sv

    monkeypatch.setattr(sv, "MAX_SKILL_BYTES", 50)
    _write(tmp_path / "skills", "big.md", GOOD)
    report = sv.validate_skills(tmp_path / "skills")
    assert any(f.rule == "FILE_SIZE" and f.level == "warn" for f in report.findings)


def test_read_failure_is_error(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    skills = tmp_path / "skills"
    target = _write(skills, "locked.md", GOOD)
    orig = Path.read_text

    def flaky(self: Path, *a, **k):  # type: ignore[no-untyped-def]
        if self == target:
            raise OSError("denied")
        return orig(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", flaky)
    report = validate_skills(skills)
    assert any(f.rule == "READ_FAIL" and f.skill == "locked" for f in report.findings)
