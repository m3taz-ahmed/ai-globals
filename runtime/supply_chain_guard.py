#!/usr/bin/env python3
"""Supply-chain guard: detect undeclared external imports.

Inspired by repo-contract's dependency guard. An AI agent commonly adds
``import newpkg`` (or ``require``/``use``/``import`` in other ecosystems)
without declaring the package in the project's lockfile/manifest. This module
scans source files and diffs against the declared dependency set and reports
:class:`UndeclaredImport` findings.

Supported ecosystems: Python (``pyproject.toml``/``requirements.txt``),
Node (``package.json``), PHP (``composer.json``), Go (``go.mod``).
"""

from __future__ import annotations

import ast
import re
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity, ValidationError


class DependencyEcosystem(str, Enum):
    """Package ecosystem for a dependency or import."""

    PYTHON = "python"
    NODE = "node"
    PHP = "php"
    GO = "go"


@dataclass
class DeclaredDependency:
    """A dependency declared in a project manifest."""

    name: str
    version: str
    ecosystem: DependencyEcosystem


@dataclass
class UndeclaredImport:
    """An import of a module/package not declared in the project manifest."""

    module: str
    file: str
    ecosystem: DependencyEcosystem
    line: int = 0


# Python standard-library modules excluded from undeclared detection.
_PYTHON_STDLIB: frozenset[str] = frozenset(
    {
        "os", "sys", "re", "json", "pathlib", "typing", "dataclasses", "enum",
        "collections", "functools", "ast", "threading", "hashlib", "datetime",
        "abc", "io", "csv", "math", "itertools", "warnings", "contextlib",
        "urllib", "logging", "time", "copy", "inspect", "unittest",
        "configparser", "sqlite3", "xml", "html", "base64", "uuid", "secrets",
        "hmac", "ssl", "socket", "select", "signal", "struct", "codecs",
        "locale", "pprint", "textwrap", "shutil", "tempfile", "subprocess",
        "platform", "getpass", "argparse",
    }
)

# Regex for TS/JS import/require statements.
_TS_IMPORT_RE = re.compile(
    r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"])"""
    r"""|(?:import\s+['"]([^'"]+)['"])"""
    r"""|(?:require\(\s*['"]([^'"]+)['"]\s*\))""",
)

# Regex for PHP `use` statements.
_PHP_USE_RE = re.compile(r"^\s*use\s+([\w\\]+)", re.MULTILINE)

# Regex for Go import blocks / single imports.
_GO_IMPORT_RE = re.compile(
    r"""^\s*import\s+(?:\(\s*([\s\S]*?)\s*\)|"([^"]+)")""",
    re.MULTILINE,
)
_GO_IMPORT_LINE_RE = re.compile(r'"([^"]+)"')


class SupplyChainGuardError(AizeeError):
    """Raised when the supply-chain guard encounters an internal error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("SUPPLY_CHAIN_ERROR", message, ErrorSeverity.HIGH, context)


class SupplyChainGuard:
    """Detect imports of external packages not declared in project manifests.

    Constructed with a project root; :meth:`load_declared` reads the manifests
    present in that root, and :meth:`scan_imports`/:meth:`check_diff` report
    imports whose top-level package is neither declared nor stdlib/builtin.
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self._declared: dict[DependencyEcosystem, set[str]] | None = None
        self._lock = threading.RLock()

    # -- declared dependency loading ----------------------------------------

    def load_declared(self) -> dict[DependencyEcosystem, set[str]]:
        """Read manifests in the project root and return declared package sets."""
        with self._lock:
            declared: dict[DependencyEcosystem, set[str]] = {
                DependencyEcosystem.PYTHON: self._load_python_declared(),
                DependencyEcosystem.NODE: self._load_node_declared(),
                DependencyEcosystem.PHP: self._load_php_declared(),
                DependencyEcosystem.GO: self._load_go_declared(),
            }
            self._declared = declared
            return declared

    def _load_python_declared(self) -> set[str]:
        names: set[str] = set()
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            names.update(_parse_pyproject_deps(pyproject.read_text(encoding="utf-8")))
        reqs = self.project_root / "requirements.txt"
        if reqs.exists():
            names.update(_parse_requirements(reqs.read_text(encoding="utf-8")))
        return names

    def _load_node_declared(self) -> set[str]:
        pkg = self.project_root / "package.json"
        if not pkg.exists():
            return set()
        return _parse_package_json(pkg.read_text(encoding="utf-8"))

    def _load_php_declared(self) -> set[str]:
        composer = self.project_root / "composer.json"
        if not composer.exists():
            return set()
        return _parse_composer_json(composer.read_text(encoding="utf-8"))

    def _load_go_declared(self) -> set[str]:
        gomod = self.project_root / "go.mod"
        if not gomod.exists():
            return set()
        return _parse_go_mod(gomod.read_text(encoding="utf-8"))

    # -- import scanning ----------------------------------------------------

    def scan_imports(self, file_path: Path) -> list[UndeclaredImport]:
        """Scan a single file and return undeclared imports for its ecosystem."""
        with self._lock:
            path = Path(file_path)
            if not path.exists():
                raise ValidationError(f"File not found: {path}")
            suffix = path.suffix.lower()
            source = path.read_text(encoding="utf-8")
            if suffix == ".py":
                ecosystem = DependencyEcosystem.PYTHON
                modules = self._extract_python_imports(source)
            elif suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
                ecosystem = DependencyEcosystem.NODE
                modules = self._extract_ts_imports(source)
            elif suffix == ".php":
                ecosystem = DependencyEcosystem.PHP
                modules = self._extract_php_imports(source)
            elif suffix == ".go":
                ecosystem = DependencyEcosystem.GO
                modules = self._extract_go_imports(source)
            else:
                return []
            return self._build_findings(modules, ecosystem, str(path))

    def check_file(self, file_path: Path) -> list[UndeclaredImport]:
        """Alias for :meth:`scan_imports` (single-file check)."""
        with self._lock:
            return self.scan_imports(file_path)

    def check_diff(self, diff_text: str) -> list[UndeclaredImport]:
        """Extract added import lines from *diff_text* and check them."""
        with self._lock:
            findings: list[UndeclaredImport] = []
            current_file: str | None = None
            for line in diff_text.splitlines():
                if line.startswith("+++ b/"):
                    current_file = line[6:]
                elif line.startswith("+++") and current_file is None:
                    current_file = line[4:].strip() if len(line) > 4 else None
                if not line.startswith("+") or line.startswith("+++"):
                    continue
                if current_file is None:
                    continue
                added = line[1:]
                finding = self._check_diff_line(added, current_file)
                if finding is not None:
                    findings.append(finding)
            return findings

    def _check_diff_line(self, added: str, file_path: str) -> UndeclaredImport | None:
        suffix = Path(file_path).suffix.lower()
        if suffix == ".py":
            modules = self._extract_python_imports(added)
            ecosystem = DependencyEcosystem.PYTHON
        elif suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            modules = self._extract_ts_imports(added)
            ecosystem = DependencyEcosystem.NODE
        elif suffix == ".php":
            modules = self._extract_php_imports(added)
            ecosystem = DependencyEcosystem.PHP
        elif suffix == ".go":
            modules = self._extract_go_imports(added)
            ecosystem = DependencyEcosystem.GO
        else:
            return None
        if not modules:
            return None
        undeclared = self._build_findings(modules, ecosystem, file_path)
        return undeclared[0] if undeclared else None

    def _build_findings(
        self,
        modules: list[tuple[str, int]],
        ecosystem: DependencyEcosystem,
        file_str: str,
    ) -> list[UndeclaredImport]:
        declared = self._ensure_declared()
        allowed = declared.get(ecosystem, set())
        findings: list[UndeclaredImport] = []
        for module, line_no in modules:
            top = self._top_level_name(module, ecosystem)
            if self._is_allowed(top, ecosystem, allowed):
                continue
            findings.append(
                UndeclaredImport(
                    module=module,
                    file=file_str,
                    ecosystem=ecosystem,
                    line=line_no,
                )
            )
        return findings

    def _ensure_declared(self) -> dict[DependencyEcosystem, set[str]]:
        if self._declared is None:
            return self.load_declared()
        return self._declared

    @staticmethod
    def _top_level_name(module: str, ecosystem: DependencyEcosystem) -> str:
        if ecosystem == DependencyEcosystem.NODE:
            if module.startswith("@"):
                parts = module.split("/", 2)
                return "/".join(parts[:2]) if len(parts) > 1 else module
            return module.split("/", 1)[0]
        if ecosystem == DependencyEcosystem.PHP:
            return module.split("\\", 1)[0]
        if ecosystem == DependencyEcosystem.GO:
            return module
        return module.split(".", 1)[0]

    @staticmethod
    def _is_allowed(
        top: str,
        ecosystem: DependencyEcosystem,
        declared: set[str],
    ) -> bool:
        if ecosystem == DependencyEcosystem.PYTHON:
            if top in _PYTHON_STDLIB:
                return True
            if top.startswith("."):
                return True
        if ecosystem == DependencyEcosystem.NODE and (top.startswith(".") or top.startswith("/") or top == "node:"):
            return True
        if ecosystem == DependencyEcosystem.PHP:
            # PHP `use` namespaces map to composer vendor prefixes case-insensitively.
            top_lower = top.lower()
            for dep in declared:
                vendor = dep.split("/", 1)[0].lower()
                if top_lower == vendor:
                    return True
            return False
        if ecosystem == DependencyEcosystem.GO:
            # Go stdlib detection is non-trivial; only declared deps are allowed.
            return top in declared
        return top in declared

    # -- per-language extractors --------------------------------------------

    def _extract_python_imports(self, source: str) -> list[tuple[str, int]]:
        MAX_SOURCE_SIZE = 10 * 1024 * 1024  # 10MB  # noqa: N806
        if len(source) > MAX_SOURCE_SIZE:
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        modules: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                modules.append((node.module, node.lineno))
        return modules

    def _extract_ts_imports(self, source: str) -> list[tuple[str, int]]:
        modules: list[tuple[str, int]] = []
        for line_no, line in enumerate(source.splitlines(), start=1):
            for match in _TS_IMPORT_RE.finditer(line):
                name = match.group(1) or match.group(2) or match.group(3)
                if name:
                    modules.append((name, line_no))
        return modules

    def _extract_php_imports(self, source: str) -> list[tuple[str, int]]:
        modules: list[tuple[str, int]] = []
        for match in _PHP_USE_RE.finditer(source):
            line_no = source.count("\n", 0, match.start()) + 1
            modules.append((match.group(1), line_no))
        return modules

    def _extract_go_imports(self, source: str) -> list[tuple[str, int]]:
        modules: list[tuple[str, int]] = []
        for match in _GO_IMPORT_RE.finditer(source):
            line_no = source.count("\n", 0, match.start()) + 1
            block = match.group(1)
            single = match.group(2)
            if block:
                for line_match in _GO_IMPORT_LINE_RE.finditer(block):
                    modules.append((line_match.group(1), line_no))
            elif single:
                modules.append((single, line_no))
        return modules


def _extract_dependency_name(spec: str) -> str | None:
    """Extract a bare dependency name from a manifest spec line."""
    # Strip environment markers / extras: requests>=2.0 ; python_version<"3.10"
    spec = spec.split(";")[0].strip()
    if not spec:
        return None
    # Strip extras: package[extra]==1.0 -> package
    spec = spec.split("[")[0]
    for sep in ("==", ">=", "<=", "!=", "~=", ">", "<", "="):
        if sep in spec:
            spec = spec.split(sep, 1)[0]
            break
    name = spec.strip()
    if not name or name.startswith("-"):
        return None
    return name


def _parse_pyproject_deps(text: str) -> set[str]:
    """Parse dependency names from pyproject.toml (naive, tomllib-free).

    Handles two layouts: ``[tool.poetry.dependencies]`` section headers and
    ``dependencies = [...]`` array keys under ``[project]``.
    """
    names: set[str] = set()
    in_section = False
    in_array = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_section = "dependencies" in stripped
            in_array = False
            continue
        if in_section:
            for quoted in re.findall(r'["\']([^"\']+)["\']', stripped):
                name = _extract_dependency_name(quoted)
                if name:
                    names.add(name)
            continue
        # Handle `dependencies = [...]` key (possibly multi-line).
        if stripped.startswith("dependencies") and "=" in stripped:
            in_array = "]" not in stripped
            for quoted in re.findall(r'["\']([^"\']+)["\']', stripped):
                name = _extract_dependency_name(quoted)
                if name:
                    names.add(name)
        elif in_array:
            for quoted in re.findall(r'["\']([^"\']+)["\']', stripped):
                name = _extract_dependency_name(quoted)
                if name:
                    names.add(name)
            if "]" in stripped:
                in_array = False
    return names


def _parse_requirements(text: str) -> set[str]:
    """Parse dependency names from a requirements.txt file."""
    names: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        name = _extract_dependency_name(stripped)
        if name:
            names.add(name)
    return names


def _parse_package_json(text: str) -> set[str]:
    """Parse dependency names from a package.json file."""
    import json as _json

    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return set()
    names: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        deps = data.get(key) or {}
        if isinstance(deps, dict):
            names.update(deps.keys())
    return names


def _parse_composer_json(text: str) -> set[str]:
    """Parse dependency names from a composer.json file."""
    import json as _json

    try:
        data = _json.loads(text)
    except _json.JSONDecodeError:
        return set()
    names: set[str] = set()
    for key in ("require", "require-dev"):
        deps = data.get(key) or {}
        if isinstance(deps, dict):
            names.update(deps.keys())
    return names


def _parse_go_mod(text: str) -> set[str]:
    """Parse dependency module paths from a go.mod file."""
    names: set[str] = set()
    in_require = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require and stripped == ")":
            in_require = False
            continue
        if in_require:
            parts = stripped.split()
            if parts:
                names.add(parts[0])
        elif stripped.startswith("require "):
            parts = stripped[len("require "):].split()
            if parts:
                names.add(parts[0])
    return names


__all__ = [
    "DeclaredDependency",
    "DependencyEcosystem",
    "SupplyChainGuard",
    "SupplyChainGuardError",
    "UndeclaredImport",
]
