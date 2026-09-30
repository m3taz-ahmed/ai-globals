"""Tests for overengineering detector + curriculum synthesis."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.curriculum import synthesize_curriculum
from runtime.overengineering import detect_overengineering


def test_overcheck_no_plan(tmp_path: Path) -> None:
    r = detect_overengineering(tmp_path, tmp_path)
    assert r.ok and not r.findings and "no active task plan" in r.notes[0]


def test_overcheck_flags_unused_produce(tmp_path: Path) -> None:
    plan = {
        "tasks": [
            {"id": "t1", "produces": ["src/util.py"]},
            {"id": "t2", "produces": ["src/api.py"], "consumes": []},
        ]
    }
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(json.dumps(plan))
    r = detect_overengineering(tmp_path, tmp_path)
    kinds = [f.kind for f in r.findings]
    assert "unused_produce" in kinds
    subjects = [f.subject for f in r.findings if f.kind == "unused_produce"]
    assert "src/util.py" in subjects and "src/api.py" in subjects


def test_overcheck_consumed_artifact_clean(tmp_path: Path) -> None:
    plan = {
        "tasks": [
            {"id": "t1", "produces": ["src/schema.py"]},
            {"id": "t2", "consumes": ["src/schema.py"]},
        ]
    }
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(json.dumps(plan))
    r = detect_overengineering(tmp_path, tmp_path)
    assert not [f for f in r.findings if f.kind == "unused_produce"]


def test_overcheck_orphan_module_via_graph(tmp_path: Path) -> None:
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(json.dumps({"scope": ["src/lonely.py"]}))
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text(
        json.dumps({"edges": [{"source": "a", "target": "other.py", "relation": "imports"}]})
    )
    r = detect_overengineering(tmp_path, tmp_path)
    assert any(f.kind == "orphan_module" for f in r.findings)


def test_curriculum_stages(tmp_path: Path) -> None:
    ts = tmp_path / "tech-stack"
    ts.mkdir()
    (ts / "python-3.md").write_text("x")
    (ts / "laravel-11.md").write_text("x")
    (ts / "docker-27.md").write_text("x")
    cur = synthesize_curriculum(tmp_path, ["python-3", "laravel-11", "docker-27"])
    stage_names = [s.name for s in cur.stages]
    assert stage_names == ["Foundations", "Core", "Operations"]
    assert "laravel-11" in cur.stages[1].items


def test_curriculum_missing_target(tmp_path: Path) -> None:
    cur = synthesize_curriculum(tmp_path, ["nonexistent-fw-99"])
    assert "nonexistent-fw-99" in cur.missing


def test_curriculum_plan_export(tmp_path: Path) -> None:
    ts = tmp_path / "tech-stack"
    ts.mkdir()
    (ts / "react-19.md").write_text("x")
    cur = synthesize_curriculum(tmp_path, ["react-19"])
    tasks = cur.to_plan_tasks()
    assert tasks and tasks[0]["id"].startswith("stage-")
    if len(tasks) > 1:
        assert tasks[1]["depends_on"] == [tasks[0]["id"]]


def test_curriculum_to_dict(tmp_path: Path) -> None:
    ts = tmp_path / "tech-stack"
    ts.mkdir()
    (ts / "react-19.md").write_text("x")
    cur = synthesize_curriculum(tmp_path, ["react-19"])
    d = cur.to_dict()
    assert d["target"] == ["react-19"] and isinstance(d["stages"], list)


def test_overcheck_to_dict(tmp_path: Path) -> None:
    r = detect_overengineering(tmp_path, tmp_path)
    d = r.to_dict()
    assert d["ok"] is True and d["findings"] == []
    assert "no active task plan" in d["notes"][0]


def test_overcheck_bad_plan_json_falls_through(tmp_path: Path) -> None:
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text("{broken")
    r = detect_overengineering(tmp_path, tmp_path)
    assert "no active task plan" in r.notes[0]


def test_overcheck_second_plan_candidate(tmp_path: Path) -> None:
    (tmp_path / ".ai" / "task").mkdir(parents=True)
    (tmp_path / ".ai" / "task" / "plan.json").write_text(
        json.dumps({"tasks": [{"id": "t", "produces": ["a.py"]}]})
    )
    r = detect_overengineering(tmp_path, tmp_path)
    assert any(f.kind == "unused_produce" for f in r.findings)


def test_overcheck_bad_graph_json_project_falls_to_os(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    os_root = tmp_path / "os"
    (project / ".task").mkdir(parents=True)
    (project / ".task" / "plan.json").write_text(json.dumps({"scope": {"files": ["x.py"]}}))
    (project / "graphify-out").mkdir()
    (project / "graphify-out" / "graph.json").write_text("{bad")
    (os_root / "graphify-out").mkdir(parents=True)
    (os_root / "graphify-out" / "graph.json").write_text(
        json.dumps({"edges": [{"source": "s", "target": "x.py", "relation": "imports"}]})
    )
    r = detect_overengineering(os_root, project)
    # dict-scope resolved, edge to x.py matched -> not an orphan.
    assert not any(f.kind == "orphan_module" for f in r.findings)


def test_overcheck_scope_dict_and_inbound_edge(tmp_path: Path) -> None:
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(
        json.dumps({"scope": {"files": ["lib/core.py"]}})
    )
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text(
        json.dumps({"edges": [{"source": "lib/api.py", "target": "lib/core.py"}]})
    )
    r = detect_overengineering(tmp_path, tmp_path)
    assert not [f for f in r.findings if f.kind == "orphan_module"]


def test_inbound_edges_no_graph() -> None:
    from runtime.overengineering import _inbound_edges

    assert _inbound_edges(None, "x.py") == -1


def test_overcheck_skips_nonexistent_and_nonpy_scope(tmp_path: Path) -> None:
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(
        json.dumps({"scope": ["ghost.py", "README.md"]})
    )
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text(
        json.dumps({"edges": [{"source": "a", "target": "ghost.py"}, {"source": "a", "target": "README.md"}]})
    )
    r = detect_overengineering(tmp_path, tmp_path)
    assert not [f for f in r.findings if f.kind == "single_impl_abstraction"]


def test_overcheck_single_impl_abstraction(tmp_path: Path) -> None:
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(json.dumps({"scope": ["mod.py"]}))
    (tmp_path / "mod.py").write_text("from typing import Protocol\nclass Repo(Protocol): ...\n")
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text(
        json.dumps({"edges": [{"relation": "implements", "target": "Repo", "source": "impl"}]})
    )
    r = detect_overengineering(tmp_path, tmp_path)
    assert any(f.kind == "single_impl_abstraction" for f in r.findings)


def test_overcheck_abstraction_with_two_impls_clean(tmp_path: Path) -> None:
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(json.dumps({"scope": ["mod.py"]}))
    (tmp_path / "mod.py").write_text("from typing import Protocol\nclass Repo(Protocol): ...\n")
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text(
        json.dumps({"edges": [
            {"relation": "implements", "target": "Repo", "source": "a"},
            {"relation": "subclass", "target": "Repo", "source": "b"},
        ]})
    )
    r = detect_overengineering(tmp_path, tmp_path)
    assert not [f for f in r.findings if f.kind == "single_impl_abstraction"]


def test_overcheck_py_dir_unreadable(tmp_path: Path) -> None:
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(json.dumps({"scope": ["pkg.py"]}))
    (tmp_path / "pkg.py").mkdir()  # directory with .py suffix -> read_text OSError
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text(json.dumps({"edges": []}))
    r = detect_overengineering(tmp_path, tmp_path)
    assert r.ok


def test_count_implementors_no_graph() -> None:
    from runtime.overengineering import _count_implementors

    assert _count_implementors(None, "X") == 0


def test_finding_to_dict(tmp_path: Path) -> None:
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(
        json.dumps({"tasks": [{"id": "t", "produces": ["a.py"]}]})
    )
    r = detect_overengineering(tmp_path, tmp_path)
    d = r.to_dict()
    assert d["findings"][0]["kind"] == "unused_produce"


def test_count_implementors_skips_non_inheritance(tmp_path: Path) -> None:
    (tmp_path / ".task").mkdir()
    (tmp_path / ".task" / "plan.json").write_text(json.dumps({"scope": ["mod.py"]}))
    (tmp_path / "mod.py").write_text("from abc import ABC\nclass Base(ABC): ...\n")
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text(
        json.dumps({"edges": [{"relation": "imports", "target": "Base", "source": "x"}]})
    )
    r = detect_overengineering(tmp_path, tmp_path)
    assert any(f.kind == "single_impl_abstraction" for f in r.findings)
