#!/usr/bin/env python3
"""Detect usage of deprecated/stale APIs in AI-generated code.

Inspired by open-code-review: AI assistants sometimes use deprecated
APIs from their training data. This module checks code against a
built-in database of deprecated APIs with modern alternatives.

Usage::

    from runtime.stale_api_detector import StaleApiDetector
    detector = StaleApiDetector()
    findings = detector.detect(code, "python", "utils.py")
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class StaleApiSeverity(str, Enum):
    """Severity of a stale API finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class StaleApiFinding:
    """A single stale/deprecated API usage finding."""

    file_path: str
    line_number: int
    api_name: str
    language: str
    deprecated_since: str
    replacement: str
    severity: StaleApiSeverity
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "api_name": self.api_name,
            "language": self.language,
            "deprecated_since": self.deprecated_since,
            "replacement": self.replacement,
            "severity": self.severity.value,
            "reason": self.reason,
        }


# -- Deprecated API database ------------------------------------------------
# Each entry: (pattern, replacement, since, severity, reason)
_DEPRECATED: dict[str, list[tuple[str, str, str, StaleApiSeverity, str]]] = {
    "python": [
        (r"\binspect\.getargspec\b", "inspect.getfullargspec", "3.0",
         StaleApiSeverity.HIGH, "getargspec removed in Python 3.11"),
        (r"\basyncio\.coroutine\b", "async def", "3.8",
         StaleApiSeverity.HIGH, "asyncio.coroutine deprecated in 3.8, removed in 3.11"),
        (r"\basyncio\.@coroutine\b", "async def", "3.8",
         StaleApiSeverity.HIGH, "asyncio.coroutine decorator deprecated"),
        (r"\btyping\.io\b", "io module directly", "3.8",
         StaleApiSeverity.MEDIUM, "typing.io deprecated, use io module"),
        (r"\btyping\.re\b", "re module directly", "3.8",
         StaleApiSeverity.MEDIUM, "typing.re deprecated, use re module"),
        (r"\btyping\.Coroutine\b", "collections.abc.Coroutine", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.AsyncGenerator\b", "collections.abc.AsyncGenerator", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.Generator\b", "collections.abc.Generator", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.Iterable\b", "collections.abc.Iterable", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.Iterator\b", "collections.abc.Iterator", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.Mapping\b", "collections.abc.Mapping", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.Sequence\b", "collections.abc.Sequence", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.Set\b", "collections.abc.Set", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.MutableMapping\b", "collections.abc.MutableMapping", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.MutableSequence\b", "collections.abc.MutableSequence", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.MutableSet\b", "collections.abc.MutableSet", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\btyping\.Callable\b", "collections.abc.Callable", "3.9",
         StaleApiSeverity.LOW, "Use collections.abc instead of typing"),
        (r"\bdistutils\b", "setuptools or packaging", "3.10",
         StaleApiSeverity.HIGH, "distutils deprecated in 3.10, removed in 3.12"),
        (r"\blib2to3\b", "lib2to3 or parso", "3.11",
         StaleApiSeverity.MEDIUM, "lib2to3 deprecated, use parso instead"),
        (r"\bimp\b", "importlib", "3.4",
         StaleApiSeverity.HIGH, "imp module deprecated, use importlib"),
        (r"\bimp\.reload\b", "importlib.reload", "3.4",
         StaleApiSeverity.HIGH, "imp.reload deprecated, use importlib.reload"),
        (r"\bos\.path\b", "pathlib.Path", "3.4",
         StaleApiSeverity.LOW, "pathlib is more modern than os.path"),
        (r"\burlparse\b", "urllib.parse.urlparse", "3.0",
         StaleApiSeverity.MEDIUM, "urlparse moved to urllib.parse in Python 3"),
        (r"\burllib2\b", "urllib.request", "3.0",
         StaleApiSeverity.HIGH, "urllib2 removed in Python 3, use urllib.request"),
        (r"\bhttplib\b", "http.client", "3.0",
         StaleApiSeverity.HIGH, "httplib renamed to http.client in Python 3"),
        (r"\bConfigParser\b", "configparser", "3.0",
         StaleApiSeverity.MEDIUM, "ConfigParser renamed to configparser in Python 3"),
        (r"\bQueue\b", "queue", "3.0",
         StaleApiSeverity.MEDIUM, "Queue renamed to queue in Python 3"),
        (r"\b__builtin__\b", "builtins", "3.0",
         StaleApiSeverity.HIGH, "__builtin__ renamed to builtins in Python 3"),
        (r"\bxrange\b", "range", "3.0",
         StaleApiSeverity.HIGH, "xrange removed in Python 3, use range"),
        (r"\bunicode\b", "str", "3.0",
         StaleApiSeverity.HIGH, "unicode removed in Python 3, use str"),
        (r"\bbasestring\b", "str", "3.0",
         StaleApiSeverity.HIGH, "basestring removed in Python 3"),
        (r"\bapply\b", "func(*args, **kwargs)", "3.0",
         StaleApiSeverity.MEDIUM, "apply() removed in Python 3"),
        (r"\bstring\.letters\b", "string.ascii_letters", "3.0",
         StaleApiSeverity.MEDIUM, "string.letters renamed to string.ascii_letters"),
        (r"\bstring\.lowercase\b", "string.ascii_lowercase", "3.0",
         StaleApiSeverity.MEDIUM, "string.lowercase renamed"),
        (r"\bstring\.uppercase\b", "string.ascii_uppercase", "3.0",
         StaleApiSeverity.MEDIUM, "string.uppercase renamed"),
    ],
    "javascript": [
        (r"\burl\.parse\b", "new URL()", "Node 11",
         StaleApiSeverity.HIGH, "url.parse deprecated, use new URL()"),
        (r"\bcomponentWillMount\b", "useEffect or constructor", "React 16.3",
         StaleApiSeverity.HIGH, "componentWillMount deprecated in React 16.3"),
        (r"\bcomponentWillReceiveProps\b", "getDerivedStateFromProps or useEffect", "React 16.3",
         StaleApiSeverity.HIGH, "componentWillReceiveProps deprecated in React 16.3"),
        (r"\bcomponentWillUpdate\b", "getSnapshotBeforeUpdate or useEffect", "React 16.3",
         StaleApiSeverity.HIGH, "componentWillUpdate deprecated in React 16.3"),
        (r"\bReactDOM\.render\b", "ReactDOM.createRoot().render()", "React 18",
         StaleApiSeverity.HIGH, "ReactDOM.render deprecated in React 18"),
        (r"\bReactDOM\.hydrate\b", "ReactDOM.hydrateRoot()", "React 18",
         StaleApiSeverity.HIGH, "ReactDOM.hydrate deprecated in React 18"),
        (r"\bReactDOMServer\.renderToString\b", "renderToStaticMarkup or streaming", "React 18",
         StaleApiSeverity.MEDIUM, "renderToString deprecated for streaming in React 18"),
        (r"\bfindDOMNode\b", "refs or callback refs", "React 16.x",
         StaleApiSeverity.HIGH, "findDOMNode deprecated, use refs instead"),
        (r"\bstring\s+ref\b", "createRef or useRef", "React 16.3",
         StaleApiSeverity.MEDIUM, "string refs deprecated, use createRef or useRef"),
        (r"\bUNSAFE_componentWillMount\b", "useEffect or constructor", "React 16.3",
         StaleApiSeverity.MEDIUM, "UNSAFE_ prefix added, use useEffect"),
        (r"\bUNSAFE_componentWillReceiveProps\b", "getDerivedStateFromProps", "React 16.3",
         StaleApiSeverity.MEDIUM, "UNSAFE_ prefix added"),
        (r"\bUNSAFE_componentWillUpdate\b", "getSnapshotBeforeUpdate", "React 16.3",
         StaleApiSeverity.MEDIUM, "UNSAFE_ prefix added"),
        (r"\bReact\.createClass\b", "ES6 classes or function components", "React 15.5",
         StaleApiSeverity.HIGH, "createClass deprecated, use ES6 classes"),
        (r"\bReact\.PropTypes\b", "prop-types package", "React 15.5",
         StaleApiSeverity.HIGH, "React.PropTypes moved to prop-types package"),
        (r"\bReact\.DOM\b", "react-dom package", "React 0.14",
         StaleApiSeverity.HIGH, "React.DOM moved to react-dom package"),
        (r"\bnew\s+Buffer\b", "Buffer.from() or Buffer.alloc()", "Node 6",
         StaleApiSeverity.HIGH, "new Buffer() deprecated due to security"),
        (r"\brequire\(['\"]util\.is[A-Z]", "util.types.isX", "Node 8",
         StaleApiSeverity.MEDIUM, "util.isX deprecated, use util.types.isX"),
        (r"\bconsole\.error\b.*\bdeprecated\b", "Remove the call", "N/A",
         StaleApiSeverity.LOW, "Console deprecation warning should be fixed"),
        (r"\bfs\.exists\b", "fs.stat or fs.access", "Node 1",
         StaleApiSeverity.MEDIUM, "fs.exists deprecated, use fs.stat or fs.access"),
        (r"\butil\.log\b", "console.log", "Node 6",
         StaleApiSeverity.MEDIUM, "util.log deprecated, use console.log"),
        (r"\butil\.print\b", "console.log", "Node 6",
         StaleApiSeverity.MEDIUM, "util.print deprecated"),
        (r"\butil\.puts\b", "console.log", "Node 6",
         StaleApiSeverity.MEDIUM, "util.puts deprecated"),
        (r"\butil\.debug\b", "console.error", "Node 6",
         StaleApiSeverity.MEDIUM, "util.debug deprecated"),
        (r"\bvm\.runInThisContext\b", "vm.compileFunction or vm.Script", "Node 10",
         StaleApiSeverity.LOW, "vm.runInThisContext deprecated"),
    ],
}


class StaleApiDetector:
    """Detect usage of deprecated/stale APIs in code.

    Maintains a plain-text database of deprecated APIs across Python and
    JavaScript/TypeScript with modern alternatives and deprecation info.
    """

    def __init__(self) -> None:
        self._deprecated = _DEPRECATED

    def detect(
        self,
        code: str,
        language: str,
        file_path: str = "<unknown>",
    ) -> list[StaleApiFinding]:
        """Detect deprecated API usage in code.

        Args:
            code: Source code string.
            language: "python", "javascript", or "typescript".
            file_path: File path for reporting.
        """
        findings: list[StaleApiFinding] = []
        patterns = self._deprecated.get(language, [])
        for pattern, replacement, since, severity, reason in patterns:
            regex = re.compile(pattern)
            for match in regex.finditer(code):
                line_num = code[: match.start()].count("\n") + 1
                findings.append(StaleApiFinding(
                    file_path=file_path,
                    line_number=line_num,
                    api_name=match.group(0).strip(),
                    language=language,
                    deprecated_since=since,
                    replacement=replacement,
                    severity=severity,
                    reason=reason,
                ))
        return findings

    def scan_file(self, file_path: Path) -> list[StaleApiFinding]:
        """Auto-detect language from file extension and scan."""
        ext = file_path.suffix.lower()
        code = file_path.read_text(encoding="utf-8", errors="ignore")
        if ext == ".py":
            return self.detect(code, "python", str(file_path))
        if ext in (".js", ".jsx", ".mjs", ".cjs"):
            return self.detect(code, "javascript", str(file_path))
        if ext in (".ts", ".tsx", ".mts", ".cts"):
            return self.detect(code, "typescript", str(file_path))
        return []

    def scan_directory(
        self, dir_path: Path, max_files: int = 100
    ) -> list[StaleApiFinding]:
        """Scan all supported files in a directory."""
        findings: list[StaleApiFinding] = []
        extensions = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}
        count = 0
        for path in sorted(dir_path.rglob("*")):
            if count >= max_files:
                break
            if path.is_file() and path.suffix.lower() in extensions:
                findings.extend(self.scan_file(path))
                count += 1
        return findings
