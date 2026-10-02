#!/usr/bin/env python3
"""Unit tests for mcp_secrets_loader.py. Run from repo root: python scripts/tests/test_mcp_secrets_loader.py"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "mcp_secrets_loader",
    os.path.join(os.path.dirname(__file__), "..", "mcp_secrets_loader.py"),
)
assert _spec is not None
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)
load_env = _mod.load_env


class LoadEnvEncodingTests(unittest.TestCase):
    def _write(self, data: bytes) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        p = Path(self._tmp.name) / ".env"
        p.write_bytes(data)
        self.addCleanup(self._tmp.cleanup)
        return p

    def test_utf8_file_loads(self) -> None:
        p = self._write(b"TEST_LOADER_UTF8=hello\n")
        self.assertEqual(load_env(p), {"TEST_LOADER_UTF8": "hello"})

    def test_cp1252_file_falls_back(self) -> None:
        # 0x97 = em-dash in Windows-1252, invalid UTF-8 — must not crash the loader
        p = self._write(b"# em-dash \x97\nTEST_LOADER_CP1252=ok\n")
        self.assertEqual(load_env(p), {"TEST_LOADER_CP1252": "ok"})

    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(load_env(Path("definitely_missing_.env_file")), {})


if __name__ == "__main__":
    unittest.main()
