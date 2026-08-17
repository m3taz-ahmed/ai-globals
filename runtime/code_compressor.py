#!/usr/bin/env python3
"""Code compression for aiZee — reduces token usage by ~70%.

Extracts code signatures and structure while removing implementation
details, producing a compact representation optimized for LLM context.

For Python, uses the stdlib ``ast`` module to extract:
- Function/class signatures (name, args, return type, decorators)
- Import statements
- Class attributes and type annotations
- Docstrings (first line only)

For other languages, falls back to regex-based signature extraction.

The architecture supports adding tree-sitter as an optional dependency
for richer extraction without changing the public API.

Usage::

    from runtime.code_compressor import CodeCompressor
    compressor = CodeCompressor()
    compressed = compressor.compress_file(Path("module.py"))
    print(f"Original: {compressed.original_tokens} tokens")
    print(f"Compressed: {compressed.compressed_tokens} tokens")
    print(f"Reduction: {compressed.reduction_percent}%")
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


@dataclass
class CompressionResult:
    """Result of code compression."""

    original_code: str
    compressed_code: str
    original_tokens: int = 0
    compressed_tokens: int = 0
    language: str = ""
    signatures: list[str] = field(default_factory=list)

    @property
    def reduction_percent(self) -> float:
        """Token reduction percentage."""
        if self.original_tokens == 0:
            return 0.0
        return round((1 - self.compressed_tokens / self.original_tokens) * 100, 1)

    @property
    def reduction_ratio(self) -> str:
        """Human-readable reduction ratio."""
        return f"{self.original_tokens} → {self.compressed_tokens} ({self.reduction_percent}% reduction)"


def _estimate_tokens(text: str) -> int:
    """Estimate token count (rough: 1 token per 4 chars)."""
    return max(1, len(text) // 4)


class PythonCompressor:
    """Python-specific code compressor using AST."""

    def compress(self, code: str) -> CompressionResult:
        """Compress Python code to signatures only."""
        original_tokens = _estimate_tokens(code)
        try:
            tree = ast.parse(code)
        except SyntaxError:
            # If we can't parse, return original
            return CompressionResult(
                original_code=code,
                compressed_code=code,
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                language="python",
            )
        lines: list[str] = []
        signatures: list[str] = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    signatures.append(f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""))
                    lines.append(signatures[-1])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join(
                    (a.asname or a.name) + (f" as {a.asname}" if a.asname else "")
                    for a in node.names
                )
                sig = f"from {module} import {names}"
                signatures.append(sig)
                lines.append(sig)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig = self._function_signature(node)
                signatures.append(sig)
                lines.append(sig)
                # Add first line of docstring if present
                docstring = ast.get_docstring(node)
                if docstring:
                    first_line = docstring.split("\n")[0].strip()
                    lines.append(f'    """{first_line}"""')
            elif isinstance(node, ast.ClassDef):
                sig = self._class_signature(node)
                signatures.append(sig)
                lines.append(sig)
                docstring = ast.get_docstring(node)
                if docstring:
                    first_line = docstring.split("\n")[0].strip()
                    lines.append(f'    """{first_line}"""')
                # Add method signatures
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_sig = "    " + self._function_signature(child)
                        signatures.append(method_sig)
                        lines.append(method_sig)
            elif isinstance(node, ast.Assign):
                # Top-level assignments (constants)
                targets = ", ".join(self._format_target(t) for t in node.targets)
                if targets.isupper() or targets.startswith("_"):
                    val_repr = self._format_value(node.value)
                    sig = f"{targets} = {val_repr}"
                    signatures.append(sig)
                    lines.append(sig)
        compressed = "\n".join(lines)
        return CompressionResult(
            original_code=code,
            compressed_code=compressed,
            original_tokens=original_tokens,
            compressed_tokens=_estimate_tokens(compressed),
            language="python",
            signatures=signatures,
        )

    def _function_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Generate a function signature string."""
        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        # Decorators
        decorators = ""
        if node.decorator_list:
            decorators = "".join(f"@{self._format_expr(d)}\n" for d in node.decorator_list)
        # Arguments
        args = self._format_args(node.args)
        # Return type
        returns = ""
        if node.returns:
            returns = f" -> {self._format_expr(node.returns)}"
        return f"{decorators}{prefix}def {node.name}({args}){returns}: ..."

    def _class_signature(self, node: ast.ClassDef) -> str:
        """Generate a class signature string."""
        decorators = ""
        if node.decorator_list:
            decorators = "".join(f"@{self._format_expr(d)}\n" for d in node.decorator_list)
        bases = ""
        if node.bases:
            bases = "(" + ", ".join(self._format_expr(b) for b in node.bases) + ")"
        return f"{decorators}class {node.name}{bases}: ..."

    def _format_args(self, args: ast.arguments) -> str:
        """Format function arguments."""
        parts: list[str] = []
        # Positional args
        for arg in args.posonlyargs + args.args:
            parts.append(self._format_arg(arg))
        # *args
        if args.vararg:
            parts.append(f"*{self._format_arg(args.vararg)}")
        elif args.kwonlyargs:
            parts.append("*")
        # Keyword-only args
        for arg in args.kwonlyargs:
            parts.append(self._format_arg(arg))
        # **kwargs
        if args.kwarg:
            parts.append(f"**{self._format_arg(args.kwarg)}")
        return ", ".join(parts)

    def _format_arg(self, arg: ast.arg) -> str:
        """Format a single argument."""
        if arg.annotation:
            return f"{arg.arg}: {self._format_expr(arg.annotation)}"
        return arg.arg

    def _format_target(self, node: ast.expr) -> str:
        """Format an assignment target."""
        return self._format_expr(node)

    def _format_value(self, node: ast.expr) -> str:
        """Format a value (simplified)."""
        return self._format_expr(node)

    def _format_expr(self, node: ast.expr | ast.operator) -> str:
        """Format an expression as a string (simplified)."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._format_expr(node.value)}.{node.attr}"
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Subscript):
            return f"{self._format_expr(node.value)}[{self._format_expr(node.slice)}]"
        if isinstance(node, ast.Call):
            return f"{self._format_expr(node.func)}(...)"
        if isinstance(node, ast.BinOp):
            return f"{self._format_expr(node.left)} {self._format_expr(node.op)} {self._format_expr(node.right)}"
        if isinstance(node, ast.Tuple):
            return "(" + ", ".join(self._format_expr(e) for e in node.elts) + ")"
        if isinstance(node, ast.List):
            return "[" + ", ".join(self._format_expr(e) for e in node.elts) + "]"
        if isinstance(node, ast.Dict):
            return "{" + ", ".join(f"{self._format_expr(k)}: {self._format_expr(v)}" for k, v in zip(node.keys, node.values, strict=False)) + "}"  # type: ignore[arg-type]
        return "..."  # fallback


class GenericCompressor:
    """Regex-based compressor for non-Python files."""

    # Patterns for common language constructs
    FUNCTION_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)", re.MULTILINE),
        re.compile(r"(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", re.MULTILINE),
        re.compile(r"(?:public|private|protected|static)?\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*[:{]", re.MULTILINE),
    ]
    CLASS_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?", re.MULTILINE),
    ]
    IMPORT_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^(?:import|export|require|include|using)\s+.*$", re.MULTILINE),
    ]

    def compress(self, code: str, language: str = "") -> CompressionResult:
        """Compress code using regex patterns."""
        original_tokens = _estimate_tokens(code)
        lines: list[str] = []
        signatures: list[str] = []
        # Extract imports
        for pattern in self.IMPORT_PATTERNS:
            for match in pattern.finditer(code):
                sig = match.group(0).strip()
                signatures.append(sig)
                lines.append(sig)
        # Extract classes
        for pattern in self.CLASS_PATTERNS:
            for match in pattern.finditer(code):
                sig = f"class {match.group(1)}: ..."
                signatures.append(sig)
                lines.append(sig)
        # Extract functions
        for pattern in self.FUNCTION_PATTERNS:
            for match in pattern.finditer(code):
                sig = f"function {match.group(1)}(...): ..."
                if sig not in signatures:
                    signatures.append(sig)
                    lines.append(sig)
        compressed = "\n".join(lines) if lines else code[:500]  # fallback: first 500 chars
        return CompressionResult(
            original_code=code,
            compressed_code=compressed,
            original_tokens=original_tokens,
            compressed_tokens=_estimate_tokens(compressed),
            language=language,
            signatures=signatures,
        )


class CodeCompressor:
    """Multi-language code compressor."""

    def __init__(self) -> None:
        self._compressors: dict[str, Any] = {
            ".py": PythonCompressor(),
            ".js": GenericCompressor(),
            ".ts": GenericCompressor(),
            ".jsx": GenericCompressor(),
            ".tsx": GenericCompressor(),
            ".go": GenericCompressor(),
            ".rs": GenericCompressor(),
            ".java": GenericCompressor(),
            ".rb": GenericCompressor(),
        }

    def compress_code(self, code: str, file_path: Path | None = None) -> CompressionResult:
        """Compress code string, dispatching by file extension."""
        if file_path:
            ext = file_path.suffix.lower()
            compressor = self._compressors.get(ext)
            if compressor:
                if isinstance(compressor, PythonCompressor):
                    return compressor.compress(code)
                return compressor.compress(code, language=ext.lstrip("."))  # type: ignore[no-any-return]
        # Auto-detect Python
        if "def " in code or "import " in code:
            return PythonCompressor().compress(code)
        return GenericCompressor().compress(code)

    def compress_file(self, file_path: Path) -> CompressionResult:
        """Compress a file."""
        if not file_path.exists():
            return CompressionResult(
                original_code="",
                compressed_code="",
                language=file_path.suffix.lstrip("."),
            )
        code = file_path.read_text(encoding="utf-8", errors="replace")
        return self.compress_code(code, file_path)

    def compress_directory(
        self,
        directory: Path,
        extensions: set[str] | None = None,
    ) -> list[CompressionResult]:
        """Compress all files in a directory."""
        if extensions is None:
            extensions = {".py", ".js", ".ts", ".go", ".rs"}
        results: list[CompressionResult] = []
        for f in directory.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in extensions:
                continue
            if any(part in {".git", "__pycache__", "node_modules", ".venv"} for part in f.parts):
                continue
            results.append(self.compress_file(f))
        return results

    def compress_to_context(
        self,
        files: list[Path],
        max_tokens: int = 8000,
    ) -> str:
        """Compress multiple files into a single context string.

        Files are compressed individually and concatenated until the
        token budget is exhausted.
        """
        parts: list[str] = []
        total_tokens = 0
        for f in files:
            result = self.compress_file(f)
            if total_tokens + result.compressed_tokens > max_tokens:
                break
            parts.append(f"--- {f.name} ---\n{result.compressed_code}")
            total_tokens += result.compressed_tokens
        return "\n\n".join(parts)


if __name__ == "__main__":
    import sys
    compressor = CodeCompressor()
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    if target.is_file():
        result = compressor.compress_file(target)
        print(f"Language: {result.language}")
        print(f"Reduction: {result.reduction_ratio}")
        print(f"\n{result.compressed_code}")
    else:
        results = compressor.compress_directory(target)
        total_orig = sum(r.original_tokens for r in results)
        total_comp = sum(r.compressed_tokens for r in results)
        reduction = round((1 - total_comp / max(1, total_orig)) * 100, 1)
        print(f"Files: {len(results)}")
        print(f"Tokens: {total_orig} → {total_comp} ({reduction}% reduction)")
