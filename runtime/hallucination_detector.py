#!/usr/bin/env python3
"""Detect hallucinated imports in AI-generated code.

Inspired by open-code-review: AI coding assistants sometimes import
packages that do not exist (hallucinated imports). This module parses
Python and JavaScript/TypeScript code, extracts import statements, and
checks them against a built-in set of known packages.

Usage::

    from runtime.hallucination_detector import HallucinationDetector
    detector = HallucinationDetector()
    findings = detector.detect_python(code, "utils.py")
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

# -- Known Python packages (stdlib + popular PyPI) --------------------------
_PYTHON_STDLIB: frozenset[str] = frozenset({
    "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
    "asyncore", "atexit", "audioop", "base64", "bdb", "binascii", "binhex",
    "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk",
    "cmath", "cmd", "code", "codecs", "codeop", "collections", "colorsys",
    "compileall", "concurrent", "configparser", "contextlib", "contextvars",
    "copy", "copyreg", "cProfile", "crypt", "csv", "ctypes", "curses",
    "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis",
    "distutils", "doctest", "email", "encodings", "ensurepip", "enum",
    "errno", "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
    "fractions", "ftplib", "functools", "gc", "getopt", "getpass", "gettext",
    "glob", "graphlib", "grp", "gzip", "hashlib", "heapq", "hmac", "html",
    "http", "idlelib", "imaplib", "imghdr", "imp", "importlib", "inspect",
    "io", "ipaddress", "itertools", "json", "keyword", "lib2to3",
    "linecache", "locale", "logging", "lzma", "mailbox", "mailcap",
    "marshal", "math", "mimetypes", "mmap", "modulefinder", "msilib",
    "msvcrt", "multiprocessing", "netrc", "nis", "nntplib", "numbers",
    "operator", "optparse", "os", "ossaudiodev", "pathlib", "pdb",
    "pickle", "pickletools", "pipes", "pkgutil", "platform", "plistlib",
    "poplib", "posix", "posixpath", "pprint", "profile", "pstats", "pty",
    "pwd", "py_compile", "pyclbr", "pydoc", "pydoc_data", "queue",
    "quopri", "random", "re", "readline", "reprlib", "resource",
    "rlcompleter", "runpy", "sched", "secrets", "select", "selectors",
    "shelve", "shlex", "shutil", "signal", "site", "smtpd", "smtplib",
    "sndhdr", "socket", "socketserver", "spwd", "sqlite3", "sre_compile",
    "sre_constants", "sre_parse", "ssl", "stat", "statistics", "string",
    "stringprep", "struct", "subprocess", "sunau", "symtable", "sys",
    "sysconfig", "syslog", "tabnanny", "tarfile", "telnetlib", "tempfile",
    "termios", "test", "textwrap", "threading", "time", "timeit",
    "tkinter", "token", "tokenize", "tomllib", "trace", "traceback",
    "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing",
    "unicodedata", "unittest", "urllib", "uu", "uuid", "venv", "warnings",
    "wave", "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
    "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
    "zoneinfo",
})

_PYTHON_POPULAR: frozenset[str] = frozenset({
    "numpy", "pandas", "matplotlib", "scipy", "scikit-learn", "sklearn",
    "tensorflow", "torch", "torchvision", "transformers", "datasets",
    "django", "flask", "fastapi", "starlette", "uvicorn", "gunicorn",
    "pydantic", "sqlalchemy", "alembic", "tortoise", "beanie",
    "requests", "httpx", "aiohttp", "urllib3", "httpcore",
    "pytest", "unittest2", "nose", "tox", "coverage", "hypothesis",
    "ruff", "black", "mypy", "flake8", "pylint", "isort",
    "celery", "redis", "rq", "dramatiq",
    "jinja2", "mako", "chameleon",
    "psycopg2", "psycopg", "asyncpg", "aiomysql", "aiosqlite",
    "boto3", "botocore", "aiobotocore",
    "openai", "anthropic", "google-generativeai", "google-cloud-aiplatform",
    "langchain", "langgraph", "langsmith", "llama-index", "llamaindex",
    "chromadb", "pinecone", "weaviate", "qdrant", "faiss", "milvus",
    "pillow", "PIL", "opencv-python", "cv2", "imageio", "scikit-image",
    "sympy", "networkx", "bokeh", "plotly", "seaborn",
    "tqdm", "rich", "click", "typer", "fire", "argcomplete",
    "pyyaml", "toml", "tomli", "tomllib", "configparser",
    "cryptography", "pyjwt", "jwt", "passlib", "bcrypt", "argon2",
    "pydantic-settings", "python-dotenv", "dotenv",
    "structlog", "loguru", "logging",
    "mcp", "fastmcp",
    "aiofiles", "watchdog", "pathspec",
    "dateutil", "pytz", "arrow", "pendulum",
    "more-itertools", "toolz", "cytoolz",
    "attrs", "marshmallow", "dataclasses-json",
    "grpc", "grpcio", "protobuf",
    "kafka", "kafka-python", "aiokafka",
    "pika", "aio-pika",
    "sentry-sdk", "opentelemetry", "opentelemetry-sdk",
    "prometheus-client", "prometheus_api_client",
    "psutil", "distro",
    "orjson", "ujson", "msgpack",
    "lxml", "beautifulsoup4", "bs4", "selectolax", "parsel",
    "selenium", "playwright", "pyppeteer",
    "scrapy",
    "twisted", "tornado",
    "uvloop", "httptools", "aiodns",
    "Cython", "numba", "llvmlite",
    "xgboost", "lightgbm", "catboost",
    "optuna", "ray", "dask", "modin",
    "mlflow", "wandb", "tensorboard",
    "spacy", "nltk", "gensim", "textblob",
    "openpyxl", "xlrd", "xlwt", "python-docx", "python-pptx",
    "reportlab", "weasyprint", "fpdf", "fpdf2",
    "qrcode",
    "pytest-asyncio", "pytest-cov", "pytest-mock", "pytest-xdist",
    "respx", "responses", "freezegun", "time-machine",
    "moto", "localstack",
    "docker", "kubernetes",
    "ansible", "fabric", "paramiko",
    "pywin32", "win32com", "win32api",
    "pyobjc", "pygtk", "PyQt5", "PyQt6", "PySide2", "PySide6",
    "kivy", "flet", "nicegui", "streamlit", "gradio", "dash",
    "textual", "textual-dev",
    "h2", "h3",
    "websockets", "wsproto",
    "aiosmtplib", "aiomonitor",
})

# -- Known npm packages (popular) ------------------------------------------
_NPM_POPULAR: frozenset[str] = frozenset({
    "react", "react-dom", "react-router", "react-router-dom",
    "next", "nuxt", "vue", "vue-router", "vuex", "pinia",
    "@vue/reactivity", "@vue/runtime-core", "@vue/shared",
    "angular", "@angular/core", "@angular/common", "@angular/router",
    "svelte", "@sveltejs/kit", "solid-js",
    "express", "fastify", "koa", "hapi", "nestjs", "@nestjs/core",
    "lodash", "lodash-es", "ramda", "date-fns", "dayjs", "moment",
    "axios", "got", "node-fetch", "undici", "ky",
    "typescript", "ts-node", "tsx",
    "webpack", "vite", "rollup", "esbuild", "parcel", "turbo",
    "babel", "@babel/core", "swc",
    "eslint", "@typescript-eslint/parser", "prettier", "biome",
    "jest", "vitest", "mocha", "chai", "sinon", "playwright",
    "tailwindcss", "postcss", "autoprefixer", "sass", "less",
    "framer-motion", "react-spring", "popmotion",
    "zustand", "jotai", "recoil", "redux", "@reduxjs/toolkit",
    "rxjs", "mobx", "valtio",
    "three", "@react-three/fiber", "d3", "chart.js", "recharts",
    "i18next", "react-i18next", "vue-i18n",
    "zod", "yup", "joi", "superstruct", "valibot",
    "prisma", "@prisma/client", "drizzle-orm", "kysely",
    "mongoose", "sequelize", "typeorm", "knex",
    "graphql", "@apollo/client", "urql", "graphql-request",
    "socket.io", "ws", "engine.io",
    "redis", "ioredis", "bull", "bullmq",
    "winston", "pino", "bunyan", "loglevel",
    "dotenv", "convict", "envalid",
    "crypto-js", "bcryptjs", "argon2", "jsonwebtoken",
    "passport", "passport-jwt", "passport-local", "next-auth",
    "multer", "sharp", "jimp", "canvas",
    "commander", "yargs", "inquirer", "prompts", "clack",
    "chalk", "kleur", "picocolors", "ansi-colors",
    "ora", "cli-spinners", "listr2",
    "debug",
    "uuid", "nanoid", "cuid",
    "clsx", "classnames", "tailwind-merge",
    "react-query", "@tanstack/react-query",
    "swr", "react-async",
    "immer", "structura",
    "fast-equals", "fast-deep-equal", "dequal",
    "ms", "humanize-duration",
    "glob", "fast-glob", "tinyglobby",
    "chokidar", "watchpack",
    "fs-extra", "graceful-fs",
    "zlib", "minizlib",
    "mime", "mime-types",
    "cookie", "cookie-parser",
    "cors", "helmet", "compression",
    "body-parser",
    "express-rate-limit", "express-validator",
    "swagger-ui-express", "swagger-jsdoc",
    "winston-daily-rotate-file",
    "pino-pretty",
    "react-hook-form", "formik", "conform",
    "@tanstack/table", "react-table",
    "react-select", "react-datepicker", "react-dropzone",
    "lucide-react", "react-icons", "@heroicons/react",
    "headlessui", "@headlessui/react",
    "radix-ui", "@radix-ui/react-dialog",
    "shadcn-ui", "@shadcn/ui",
    "cmdk", "sonner", "react-hot-toast",
    "embla-carousel", "keen-slider",
    "react-window", "react-virtualized", "@tanstack/react-virtual",
    "react-error-boundary",
    "react-helmet", "react-helmet-async",
    "next-themes",
    "next-seo",
    "next-sitemap",
    "next-pwa",
    "next-mdx", "@next/mdx",
    "remark", "rehype", "unified",
    "gray-matter",
    "shiki", "prismjs", "highlight.js",
    "katex", "mathjax",
    "mermaid",
    "canvas-confetti",
    "react-pdf", "@react-pdf/renderer",
    "xlsx", "exceljs",
    "papaparse",
    "pdfjs-dist", "pdf-lib",
    "qrcode", "qrcode.react",
})


class HallucinationSeverity(str, Enum):
    """Severity of a hallucinated import finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class HallucinationFinding:
    """A single hallucinated import finding."""

    file_path: str
    line_number: int
    import_statement: str
    package_name: str
    language: str
    severity: HallucinationSeverity
    reason: str
    fix: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "import_statement": self.import_statement,
            "package_name": self.package_name,
            "language": self.language,
            "severity": self.severity.value,
            "reason": self.reason,
            "fix": self.fix,
        }


class HallucinationDetector:
    """Detect hallucinated imports in AI-generated code.

    Checks Python and JavaScript/TypeScript imports against a built-in
    set of known packages. Unknown imports are flagged as potential
    hallucinations.
    """

    def __init__(self) -> None:
        self._python_known = _PYTHON_STDLIB | _PYTHON_POPULAR
        self._npm_known = _NPM_POPULAR

    def detect_python(
        self, code: str, file_path: str = "<unknown>"
    ) -> list[HallucinationFinding]:
        """Detect hallucinated imports in Python code using AST.

        Parses ``import X`` and ``from X import Y`` statements and
        checks the top-level package against known Python packages.
        """
        findings: list[HallucinationFinding] = []
        try:
            tree = ast.parse(code, filename=file_path)
        except SyntaxError as exc:
            _logger.debug("Python parse error in %s: %s", file_path, exc)
            return findings

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".")[0]
                    if pkg not in self._python_known:
                        findings.append(self._make_finding(
                            file_path, node.lineno,
                            f"import {alias.name}", pkg, "python",
                        ))
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                pkg = node.module.split(".")[0]
                if pkg not in self._python_known:
                    names = ", ".join(a.name for a in node.names)
                    findings.append(self._make_finding(
                        file_path, node.lineno,
                        f"from {node.module} import {names}", pkg, "python",
                    ))
        return findings

    def detect_javascript(
        self, code: str, file_path: str = "<unknown>"
    ) -> list[HallucinationFinding]:
        """Detect hallucinated imports in JavaScript code.

        Parses ``import ... from 'pkg'`` and ``require('pkg')`` statements.
        """
        return self._detect_js_ts(code, file_path, "javascript")

    def detect_typescript(
        self, code: str, file_path: str = "<unknown>"
    ) -> list[HallucinationFinding]:
        """Detect hallucinated imports in TypeScript code.

        Parses ``import ... from 'pkg'`` and ``require('pkg')`` statements,
        including type-only imports.
        """
        return self._detect_js_ts(code, file_path, "typescript")

    def _detect_js_ts(
        self, code: str, file_path: str, language: str
    ) -> list[HallucinationFinding]:
        """Shared detection logic for JS and TS."""
        findings: list[HallucinationFinding] = []
        # Match: import { x } from 'pkg' / import x from 'pkg' / import 'pkg'
        import_re = re.compile(
            r"""^\s*import\s+(?:type\s+)?(?:[^'"]+\s+from\s+)?['"]([^'\"./][^'"]*)['"]""",
            re.MULTILINE,
        )
        # Match: require('pkg') / require("pkg")
        require_re = re.compile(
            r"""require\(\s*['"]([^'\"./][^'"]*)['"]\s*\)""",
        )
        for match in import_re.finditer(code):
            pkg = match.group(1).split("/")[0]
            if pkg.startswith("@"):
                parts = match.group(1).split("/", 2)
                pkg = "/".join(parts[:2])
            line_num = code[: match.start()].count("\n") + 1
            if pkg not in self._npm_known:
                findings.append(self._make_finding(
                    file_path, line_num, match.group(0).strip(),
                    pkg, language,
                ))
        for match in require_re.finditer(code):
            pkg = match.group(1).split("/")[0]
            if pkg.startswith("@"):
                parts = match.group(1).split("/", 2)
                pkg = "/".join(parts[:2])
            line_num = code[: match.start()].count("\n") + 1
            if pkg not in self._npm_known:
                findings.append(self._make_finding(
                    file_path, line_num, match.group(0).strip(),
                    pkg, language,
                ))
        return findings

    def scan_file(self, file_path: Path) -> list[HallucinationFinding]:
        """Auto-detect language from file extension and scan."""
        ext = file_path.suffix.lower()
        code = file_path.read_text(encoding="utf-8", errors="ignore")
        if ext == ".py":
            return self.detect_python(code, str(file_path))
        if ext in (".js", ".jsx", ".mjs", ".cjs"):
            return self.detect_javascript(code, str(file_path))
        if ext in (".ts", ".tsx", ".mts", ".cts"):
            return self.detect_typescript(code, str(file_path))
        return []

    def scan_directory(
        self, dir_path: Path, max_files: int = 100
    ) -> list[HallucinationFinding]:
        """Scan all supported files in a directory."""
        findings: list[HallucinationFinding] = []
        extensions = {".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts"}
        count = 0
        for path in sorted(dir_path.rglob("*")):
            if count >= max_files:
                break
            if path.is_file() and path.suffix.lower() in extensions:
                findings.extend(self.scan_file(path))
                count += 1
        return findings

    def _make_finding(
        self,
        file_path: str,
        line_number: int,
        import_statement: str,
        package_name: str,
        language: str,
    ) -> HallucinationFinding:
        """Create a hallucination finding."""
        return HallucinationFinding(
            file_path=file_path,
            line_number=line_number,
            import_statement=import_statement,
            package_name=package_name,
            language=language,
            severity=HallucinationSeverity.HIGH,
            reason=f"Package '{package_name}' is not in the known package registry",
            fix=f"Verify '{package_name}' exists in the package registry or replace with a known package",
        )
