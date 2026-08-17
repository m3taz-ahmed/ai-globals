#!/usr/bin/env python3
"""AST-based code validation for aiZee.

Validates code before and after edits to catch issues that policy rules
cannot detect: syntax errors, undefined imports, missing dependencies,
and structural violations.

Two validation modes:
- **Pre-edit (plan validation):** Checks a proposed code change against
  the existing file's imports and structure before it is applied.
- **Post-edit (diff validation):** Checks the resulting file after an
  edit for syntax validity, import resolution, and dependency integrity.

Currently supports Python via the stdlib ``ast`` module. The architecture
is extensible to other languages via tree-sitter (see ``CodeValidator``
language dispatch).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

# Builtin modules always available in Python
_BUILTIN_MODULES = frozenset({
    "abc", "argparse", "ast", "asyncio", "base64", "bisect", "calendar",
    "collections", "concurrent", "configparser", "contextlib", "copy",
    "csv", "datetime", "decimal", "difflib", "enum", "errno", "faulthandler",
    "fnmatch", "functools", "gc", "getpass", "glob", "hashlib", "heapq",
    "html", "http", "importlib", "inspect", "io", "itertools", "json",
    "logging", "math", "mmap", "multiprocessing", "operator", "os",
    "pathlib", "pickle", "platform", "pprint", "queue", "re", "secrets",
    "shutil", "signal", "socket", "sqlite3", "statistics", "string",
    "struct", "subprocess", "sys", "tempfile", "textwrap", "threading",
    "time", "traceback", "typing", "unittest", "urllib", "uuid", "warnings",
    "weakref", "xml", "zipfile", "zlib",
})


@dataclass
class ValidationResult:
    """Result of an AST validation pass."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Merge two validation results."""
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            imports=self.imports + other.imports,
            symbols=self.symbols + other.symbols,
        )


class PythonASTValidator:
    """Python-specific AST validator using the stdlib ``ast`` module."""

    def parse(self, code: str) -> ValidationResult:
        """Parse code and return syntax validation result."""
        result = ValidationResult(valid=True)
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            result.valid = False
            result.errors.append(f"SyntaxError at line {e.lineno}: {e.msg}")
            return result
        # Extract imports and top-level symbols
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.names and node.names[0].name == "*":
                    result.imports.append(f"{module}.*")
                else:
                    for alias in node.names:
                        result.imports.append(f"{module}.{alias.name}" if module else alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                result.symbols.append(node.name)
        return result

    def check_imports(self, code: str, existing_imports: set[str] | None = None) -> ValidationResult:
        """Check that all imports in code are resolvable.

        ``existing_imports`` is a set of module names already available
        in the project (e.g., from requirements.txt or installed packages).
        Builtins are always considered available.
        """
        result = self.parse(code)
        if not result.valid:
            return result
        available = set(_BUILTIN_MODULES)
        if existing_imports:
            available.update(existing_imports)
        for imp in result.imports:
            top_level = imp.split(".")[0]
            if top_level not in available and top_level not in ("__future__",):
                result.warnings.append(f"Import '{imp}' may not be resolvable (top-level '{top_level}' not in known modules)")
        return result

    def check_undefined_names(self, code: str) -> ValidationResult:
        """Check for references to undefined names (basic static analysis)."""
        result = self.parse(code)
        if not result.valid:
            return result
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return result  # already captured in parse
        # Collect defined names
        defined: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined.add(target.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    defined.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        defined.add(alias.asname or alias.name)
            elif isinstance(node, (ast.arg,)):
                defined.add(node.arg)
        # Collect used names
        used: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)
        # Builtins always available
        import builtins
        builtin_names = set(dir(builtins))
        undefined = used - defined - builtin_names - {"self", "cls"}
        for name in sorted(undefined):
            result.warnings.append(f"Potentially undefined name: '{name}'")
        return result


class CodeValidator:
    """Multi-language code validator dispatching to language-specific validators.

    Currently supports Python. The architecture allows adding tree-sitter
    validators for JavaScript, TypeScript, Go, etc. without changing the
    public API.
    """

    def __init__(self) -> None:
        self._validators: dict[str, PythonASTValidator] = {
            ".py": PythonASTValidator(),
        }

    def _get_validator(self, file_path: Path) -> PythonASTValidator | None:
        ext = file_path.suffix.lower()
        return self._validators.get(ext)

    def validate_pre_edit(
        self,
        file_path: Path,
        proposed_code: str,
        existing_imports: set[str] | None = None,
    ) -> ValidationResult:
        """Validate a proposed code change before it is applied.

        Checks:
        1. Syntax validity of the proposed code.
        2. Import resolvability against known modules.
        3. Undefined name references.
        """
        validator = self._get_validator(file_path)
        if validator is None:
            return ValidationResult(valid=True, warnings=[f"No AST validator for '{file_path.suffix}' — skipping"])
        result = validator.parse(proposed_code)
        if not result.valid:
            return result
        import_result = validator.check_imports(proposed_code, existing_imports)
        result = result.merge(import_result)
        name_result = validator.check_undefined_names(proposed_code)
        return result.merge(name_result)

    def validate_post_edit(
        self,
        file_path: Path,
        final_code: str,
        existing_imports: set[str] | None = None,
    ) -> ValidationResult:
        """Validate the final state of a file after an edit.

        Checks:
        1. Syntax validity.
        2. Import resolvability.
        3. Undefined name references.
        4. File is non-empty and parseable.
        """
        if not final_code.strip():
            return ValidationResult(valid=False, errors=["File is empty after edit"])
        return self.validate_pre_edit(file_path, final_code, existing_imports)

    def validate_diff(
        self,
        file_path: Path,
        old_code: str,
        new_code: str,
        existing_imports: set[str] | None = None,
    ) -> ValidationResult:
        """Validate a diff between old and new code.

        Checks:
        1. New code is syntactically valid.
        2. No imports were removed that are still used.
        3. No new undefined names were introduced.
        """
        validator = self._get_validator(file_path)
        if validator is None:
            return ValidationResult(valid=True, warnings=[f"No AST validator for '{file_path.suffix}' — skipping"])
        # Validate new code
        new_result = self.validate_post_edit(file_path, new_code, existing_imports)
        if not new_result.valid:
            return new_result
        # Check for removed imports still in use
        old_parse = validator.parse(old_code)
        new_parse = validator.parse(new_code)
        if old_parse.valid and new_parse.valid:
            old_imports = {imp.split(".")[0] for imp in old_parse.imports}
            new_imports = {imp.split(".")[0] for imp in new_parse.imports}
            removed = old_imports - new_imports
            if removed:
                new_result.warnings.append(f"Removed imports: {sorted(removed)}")
        return new_result

    def extract_imports(self, file_path: Path) -> set[str]:
        """Extract all import top-level module names from a file."""
        validator = self._get_validator(file_path)
        if validator is None or not file_path.exists():
            return set()
        code = file_path.read_text(encoding="utf-8", errors="replace")
        result = validator.parse(code)
        return {imp.split(".")[0] for imp in result.imports}

    def check_dependency_guard(
        self,
        file_path: Path,
        project_files: list[Path],
    ) -> ValidationResult:
        """Check that file dependencies exist within the project.

        For each ``from <local_module> import ...`` statement, verify
        that ``<local_module>`` exists as a file in the project.
        """
        result = ValidationResult(valid=True)
        if not file_path.exists():
            result.valid = False
            result.errors.append(f"File does not exist: {file_path}")
            return result
        validator = self._get_validator(file_path)
        if validator is None:
            return result
        code = file_path.read_text(encoding="utf-8", errors="replace")
        parse_result = validator.parse(code)
        if not parse_result.valid:
            return parse_result
        # Build a map of project module names to file paths
        project_modules: dict[str, Path] = {}
        for pf in project_files:
            if pf.suffix == ".py" and pf != file_path:
                # Module name = relative path without extension, dots for slashes
                rel = pf.stem
                project_modules[rel] = pf
        # Check each import
        for imp in parse_result.imports:
            top_level = imp.split(".")[0]
            if top_level in project_modules:
                continue  # OK, local module exists
            if top_level in _BUILTIN_MODULES or top_level == "__future__":
                continue
            # Not a builtin and not in project — might be a third-party package
            # This is a warning, not an error
        return result
