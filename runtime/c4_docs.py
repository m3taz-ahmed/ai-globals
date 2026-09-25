"""C4 documentation generator — consumes graphify-out/graph.json.

Adapted from sopaco/deepwiki-rs (Litho): turn the repo knowledge graph
into C4-style markdown a human can navigate:

    docs/c4/context.md          — system context (externals in/out)
    docs/c4/containers.md       — top-level dirs as C4 containers
    docs/c4/components/<dir>.md — per-container component detail

Containers = top-level source dirs. Components = files. Edges are
aggregated `imports`/`calls`/`uses`/`inherits`/`references` links.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_CODE_RELS = {"imports", "imports_from", "calls", "uses", "inherits", "references"}
_MAX_MERMAID_EDGES = 40
_EXCLUDED_CONTAINERS = {"htmlcov", "node_modules", "__pycache__", ".git", ".venv", "venv", "dist", "build"}


@dataclass
class Container:
    """A top-level directory treated as a C4 container."""

    name: str
    files: set[str] = field(default_factory=set)
    symbols: int = 0
    edges_out: collections.Counter[str] = field(default_factory=collections.Counter)
    edges_in: collections.Counter[str] = field(default_factory=collections.Counter)


def _container_of(source_file: str) -> str:
    parts = (source_file or "").replace("\\", "/").split("/")
    if len(parts) > 1:
        return parts[0]
    return "(root)"


def _mermaid_id(name: str) -> str:
    return "c_" + "".join(ch if ch.isalnum() else "_" for ch in name)


class C4Generator:
    """Generate C4-style markdown docs from a graphify graph."""

    def __init__(self, graph_path: Path):
        data = json.loads(Path(graph_path).read_text(encoding="utf-8"))
        self.nodes: list[dict[str, Any]] = data.get("nodes", [])
        self.links: list[dict[str, Any]] = data.get("links", [])
        self._node_by_id = {n["id"]: n for n in self.nodes}
        self.containers: dict[str, Container] = {}
        self._external: collections.Counter[str] = collections.Counter()
        self._build()

    def _build(self) -> None:
        file_nodes = [n for n in self.nodes if n.get("source_file")]
        for n in file_nodes:
            cname = _container_of(n["source_file"])
            if cname in _EXCLUDED_CONTAINERS:
                continue
            c = self.containers.setdefault(cname, Container(name=cname))
            c.files.add(n["source_file"])
            c.symbols += 1
        for link in self.links:
            if link.get("relation") not in _CODE_RELS:
                continue
            src, tgt = self._node_by_id.get(link.get("source")), self._node_by_id.get(link.get("target"))
            sfile = src.get("source_file", "") if src else ""
            tfile = tgt.get("source_file", "") if tgt else ""
            if sfile and not tfile:
                # External target — imported package or unresolved symbol
                self._external[tgt.get("label", link.get("target", "?")) if tgt else link.get("target", "?")] += 1
                continue
            if not sfile or sfile == tfile:
                continue
            sc, tc = _container_of(sfile), _container_of(tfile)
            if sc == tc:
                continue
            self.containers[sc].edges_out[tc] += 1
            self.containers[tc].edges_in[sc] += 1

    # ---- emitters -------------------------------------------------------

    def context_md(self) -> str:
        lines = [
            "# C4 — System Context",
            "",
            f"Containers: {len(self.containers)} | "
            f"Nodes: {len(self.nodes)} | Edges: {len(self.links)}",
            "",
            "```mermaid",
            "C4Context",
            '    System(sys, "aiZee", "Policy layer for AI coding")',
        ]
        for name in sorted(self.containers):
            c = self.containers[name]
            lines.append(
                f'    Container({_mermaid_id(name)}, "{name}", "", "{len(c.files)} files")'
            )
            lines.append(f"    Rel(sys, {_mermaid_id(name)}, 'contains')")
        for ext, count in self._external.most_common(10):
            safe = ext.replace('"', "'")[:40]
            lines.append(f'    System_Ext({_mermaid_id("ext_" + ext)}, "{safe}")')
            lines.append(f"    Rel(sys, {_mermaid_id('ext_' + ext)}, 'uses x{count}')")
        lines += ["```", ""]
        return "\n".join(lines)

    def containers_md(self) -> str:
        lines = [
            "# C4 — Containers",
            "",
            "| Container | Files | Symbols | Out | In |",
            "|---|---|---|---|---|",
        ]
        for name in sorted(self.containers):
            c = self.containers[name]
            lines.append(
                f"| `{name}` | {len(c.files)} | {c.symbols} | "
                f"{sum(c.edges_out.values())} | {sum(c.edges_in.values())} |"
            )
        lines += ["", "```mermaid", "graph LR"]
        edges: list[tuple[str, str, int]] = []
        for name, c in self.containers.items():
            for tgt, w in c.edges_out.items():
                edges.append((name, tgt, w))
        for s, t, w in sorted(edges, key=lambda e: -e[2])[:_MAX_MERMAID_EDGES]:
            lines.append(f"    {_mermaid_id(s)}[{s}] -->|{w}| {_mermaid_id(t)}[{t}]")
        lines += ["```", ""]
        return "\n".join(lines)

    def component_md(self, name: str) -> str:
        c = self.containers[name]
        rels: collections.Counter[tuple[str, str, str]] = collections.Counter()
        for link in self.links:
            if link.get("relation") not in _CODE_RELS:
                continue
            s = self._node_by_id.get(link.get("source"), {})
            t = self._node_by_id.get(link.get("target"), {})
            if s.get("source_file") and t.get("source_file") and \
               _container_of(s["source_file"]) == name and \
               _container_of(t["source_file"]) == name and \
               s["source_file"] != t["source_file"]:
                rels[(s["source_file"], t["source_file"], link["relation"])] += 1
        lines = [
            f"# C4 — Components: `{name}`",
            "",
            f"Files: {len(c.files)} | Symbols: {c.symbols}",
            "",
            "## Files",
            "",
        ]
        lines += [f"- `{f}`" for f in sorted(c.files)[:100]]
        lines += ["", "## Internal edges", "", "```mermaid", "graph LR"]
        for (s, t, r), w in rels.most_common(_MAX_MERMAID_EDGES):
            sid = _mermaid_id(s.replace("/", "_"))
            tid = _mermaid_id(t.replace("/", "_"))
            lines.append(f'    {sid}["{Path(s).name}"] -->|{r} x{w}| {tid}["{Path(t).name}"]')
        lines += ["```", ""]
        return "\n".join(lines)

    def generate(self, out_dir: Path) -> list[Path]:
        out_dir = Path(out_dir)
        (out_dir / "components").mkdir(parents=True, exist_ok=True)
        written = []
        for fname, text in [
            ("context.md", self.context_md()),
            ("containers.md", self.containers_md()),
        ]:
            p = out_dir / fname
            p.write_text(text, encoding="utf-8")
            written.append(p)
        for name in sorted(self.containers):
            p = out_dir / "components" / f"{name.strip('()') or 'root'}.md"
            p.write_text(self.component_md(name), encoding="utf-8")
            written.append(p)
        return written


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate C4 docs from graphify-out/graph.json")
    p.add_argument("--graph", default="graphify-out/graph.json")
    p.add_argument("--out", default="docs/c4")
    args = p.parse_args(argv)
    gen = C4Generator(Path(args.graph))
    written = gen.generate(Path(args.out))
    for p_ in written:
        print(p_)
    return 0


if __name__ == "__main__":
    sys.exit(main())
