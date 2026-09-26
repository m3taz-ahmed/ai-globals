"""Tests for runtime.security_scanner — built-in rules + tool orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.security_scanner import (
    ScanReport,
    ScanSeverity,
    SecurityScanner,
    scan_project,
)


def _write(root: Path, name: str, content: str) -> Path:
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _rule_ids(report: ScanReport) -> set[str]:
    return {f.rule_id for f in report.findings}


def test_detects_hardcoded_secrets(tmp_path: Path) -> None:
    _write(tmp_path, "app.py", 'AWS_KEY = "AKIAZZZZZZZZZZZZZZZZ"\n')
    report = scan_project(tmp_path, use_tools=False)
    assert "SEC-AWS-KEY" in _rule_ids(report)
    assert not report.ok  # blocker present


def test_detects_injection_sinks(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "svc.py",
        "import subprocess, os, yaml, pickle\n"
        "subprocess.run(cmd, shell=True)\n"
        "eval(user_input)\n"
        "os.system(x)\n"
        "yaml.load(raw)\n"
        "pickle.loads(blob)\n",
    )
    ids = _rule_ids(scan_project(tmp_path, use_tools=False))
    for expected in (
        "INJ-SHELL-TRUE", "INJ-EVAL", "INJ-OS-SYSTEM", "INJ-YAML-LOAD", "INJ-PICKLE",
    ):
        assert expected in ids, expected


def test_detects_misconfig_and_fail_open(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "settings.py",
        "DEBUG = True\n"
        'allow_origins = ["*"]\n'
        'app.run(host="0.0.0.0")\n'
        "try:\n    pass\nexcept Exception:\n    pass\n"
        'requests.get(u, verify=False)\n',
    )
    ids = _rule_ids(scan_project(tmp_path, use_tools=False))
    for expected in ("CFG-DEBUG", "CFG-CORS-WILDCARD", "CFG-BIND-ALL", "A10-SWALLOW", "TLS-VERIFY-OFF"):
        assert expected in ids, expected


def test_env_file_is_blocker(tmp_path: Path) -> None:
    _write(tmp_path, ".env", "SECRET=hunter2\n")
    report = scan_project(tmp_path, use_tools=False)
    assert "SEC-ENVFILE" in _rule_ids(report)
    # presence-finding deduped when content findings already cover the file
    assert "SEC-ENV-COMMITTED" not in _rule_ids(report)
    assert not report.ok


def test_empty_env_file_still_flagged(tmp_path: Path) -> None:
    _write(tmp_path, ".env", "# nothing secret here\n")
    report = scan_project(tmp_path, use_tools=False)
    assert "SEC-ENV-COMMITTED" in _rule_ids(report)


def test_dotenv_variants_scanned(tmp_path: Path) -> None:
    _write(tmp_path, ".env.local", "PASSWORD=s3cret-value\n")
    _write(tmp_path, "app/.env.production", "API_TOKEN=tok-abcdefgh\n")
    ids = _rule_ids(scan_project(tmp_path, use_tools=False))
    assert "SEC-ENVFILE" in ids


def test_inline_suppression_specific_rule(tmp_path: Path) -> None:
    _write(tmp_path, "app.py", 'eval(x)  # aizee-scan: ignore INJ-EVAL\n')
    report = scan_project(tmp_path, use_tools=False)
    assert "INJ-EVAL" not in _rule_ids(report)
    assert report.suppressed == 1


def test_inline_suppression_bare_and_rule_mismatch(tmp_path: Path) -> None:
    _write(tmp_path, "app.py", 'eval(x)  # aizee-scan: ignore\n')
    _write(tmp_path, "other.py", 'eval(x)  # aizee-scan: ignore CFG-DEBUG\n')
    ids = _rule_ids(scan_project(tmp_path, use_tools=False))
    # bare marker suppresses; wrong-rule marker does not
    assert ids == {"INJ-EVAL"}


def test_ignore_file_marker_skips_file(tmp_path: Path) -> None:
    _write(tmp_path, "rules.py", '# aizee-scan: ignore-file — detector patterns\neval(x)\n')
    _write(tmp_path, "real.py", "eval(x)\n")
    report = scan_project(tmp_path, use_tools=False)
    assert [f.file for f in report.findings] == [str(tmp_path / "real.py")]


def test_generated_sbom_skipped(tmp_path: Path) -> None:
    _write(tmp_path, "state/sbom.json", '{"x": "http://example.com"}\n')
    _write(tmp_path, "ok.py", "print('ok')\n")
    report = scan_project(tmp_path, use_tools=False)
    assert "HTTP-PLAINTEXT" not in _rule_ids(report)


def test_gitignored_env_downgraded(tmp_path: Path, monkeypatch) -> None:
    import runtime.security_scanner as mod

    _write(tmp_path, ".env", "SECRET=hunter2\nPASSWORD=hunter3\n")

    class _Res:
        returncode = 0
        stdout = ""

    monkeypatch.setattr(mod.shutil, "which", lambda _n: "git")
    monkeypatch.setattr(
        SecurityScanner, "_run_cmd",
        staticmethod(lambda _a, _c: _Res()),
    )
    report = scan_project(tmp_path, use_tools=False)
    env_findings = [f for f in report.findings if f.rule_id.startswith("SEC-ENV")]
    assert env_findings
    assert all(f.severity is ScanSeverity.LOW for f in env_findings)
    assert report.ok  # no blockers


def test_env_ignore_file_marker_skips_all(tmp_path: Path) -> None:
    _write(tmp_path, ".env", "# aizee-scan: ignore-file — local dev credentials\nSECRET=hunter2\n")
    report = scan_project(tmp_path, use_tools=False)
    assert not [f for f in report.findings if f.rule_id.startswith("SEC-ENV")]
    assert report.suppressed >= 1
    assert report.ok


def test_env_unreadable_falls_back_to_presence_check(
    tmp_path: Path, monkeypatch
) -> None:
    _write(tmp_path, ".env", "FOO=bar\n")
    real_read = Path.read_text

    def _denied(
        self: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        if self.name == ".env":
            raise OSError("denied")
        return real_read(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", _denied)
    report = scan_project(tmp_path, use_tools=False)
    assert "SEC-ENV-COMMITTED" in _rule_ids(report)


def test_gitignored_empty_env_is_low(tmp_path: Path, monkeypatch) -> None:
    import runtime.security_scanner as mod

    _write(tmp_path, ".env", "# FOO=bar — no secret-shaped keys\n")

    class _Res:
        returncode = 0
        stdout = ""

    monkeypatch.setattr(mod.shutil, "which", lambda _n: "git")
    monkeypatch.setattr(
        SecurityScanner, "_run_cmd",
        staticmethod(lambda _a, _c: _Res()),
    )
    report = scan_project(tmp_path, use_tools=False)
    committed = [f for f in report.findings if f.rule_id == "SEC-ENV-COMMITTED"]
    assert len(committed) == 1
    assert committed[0].severity is ScanSeverity.LOW
    assert report.ok


def test_tracked_env_stays_blocker(tmp_path: Path, monkeypatch) -> None:
    import runtime.security_scanner as mod

    _write(tmp_path, ".env", "SECRET=hunter2\n")

    class _Res:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(mod.shutil, "which", lambda _n: "git")
    monkeypatch.setattr(
        SecurityScanner, "_run_cmd",
        staticmethod(lambda _a, _c: _Res()),
    )
    report = scan_project(tmp_path, use_tools=False)
    assert not report.ok


def test_gitignore_outside_root_and_no_git(tmp_path: Path, monkeypatch) -> None:
    import runtime.security_scanner as mod

    scanner = SecurityScanner()
    scanner._root = tmp_path
    # path outside root hits the ValueError fallback
    monkeypatch.setattr(mod.shutil, "which", lambda _n: "git")

    class _Res:
        returncode = 0
        stdout = ""

    monkeypatch.setattr(
        SecurityScanner, "_run_cmd",
        staticmethod(lambda _a, _c: _Res()),
    )
    assert scanner._is_git_ignored(Path("C:/elsewhere/x.env")) is True
    # no git available -> not ignored
    monkeypatch.setattr(mod.shutil, "which", lambda _n: None)
    assert scanner._is_git_ignored(tmp_path / ".env") is False


def test_suppression_on_last_line_no_newline(tmp_path: Path) -> None:
    _write(tmp_path, "app.py", "eval(x)  # aizee-scan: ignore")
    report = scan_project(tmp_path, use_tools=False)
    assert "INJ-EVAL" not in _rule_ids(report)
    assert report.suppressed == 1


def test_skips_vendor_and_node_modules(tmp_path: Path) -> None:
    _write(tmp_path, "node_modules/x/index.js", 'eval("x")\n')
    _write(tmp_path, "vendor/lib.php", 'eval($x);\n')
    report = scan_project(tmp_path, use_tools=False)
    assert all("node_modules" not in f.file and "vendor" not in f.file for f in report.findings)


def test_clean_project_passes(tmp_path: Path) -> None:
    _write(tmp_path, "main.py", "import hashlib\nprint(hashlib.sha256(b'x').hexdigest())\n")
    report = scan_project(tmp_path, use_tools=False)
    assert report.ok
    assert report.files_scanned >= 1


def test_missing_target_is_blocker(tmp_path: Path) -> None:
    report = scan_project(tmp_path / "does-not-exist", use_tools=False)
    assert not report.ok
    assert report.findings[0].rule_id == "SCAN-TARGET"


def test_findings_sorted_blockers_first(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "a.py",
        'K = "AKIAZZZZZZZZZZZZZZZZ"\nprint("http://example.com")\n',
    )
    report = scan_project(tmp_path, use_tools=False)
    assert report.findings[0].severity is ScanSeverity.BLOCKER


def test_to_dict_shape(tmp_path: Path) -> None:
    _write(tmp_path, "ok.py", "x = 1\n")
    d = scan_project(tmp_path, use_tools=False).to_dict()
    for key in ("target", "files_scanned", "tools_run", "tools_skipped", "summary", "ok", "findings"):
        assert key in d
    assert set(d["summary"]) == {"blocker", "high", "medium", "low"}


def test_extra_skip_dirs(tmp_path: Path) -> None:
    _write(tmp_path, "ignoreme/x.py", "eval('1')\n")
    scanner = SecurityScanner(extra_skip_dirs={"ignoreme"})
    report = scanner.scan(tmp_path, use_tools=False)
    assert all("ignoreme" not in f.file for f in report.findings)


def test_line_numbers_reported(tmp_path: Path) -> None:
    _write(tmp_path, "f.py", "x = 1\ny = 2\neval(z)\n")
    report = scan_project(tmp_path, use_tools=False)
    hit = next(f for f in report.findings if f.rule_id == "INJ-EVAL")
    assert hit.line == 3


def test_npm_audit_parser(tmp_path: Path) -> None:
    _write(tmp_path, "package.json", "{}")
    payload = json.dumps({
        "vulnerabilities": {
            "lodash": {"severity": "critical"},
            "left-pad": {"severity": "moderate"},
        }
    })

    class _Res:
        stdout = payload

    scanner = SecurityScanner()
    orig = scanner._run_cmd
    scanner._run_cmd = staticmethod(lambda *a, **k: _Res())  # type: ignore[assignment]
    try:
        report = ScanReport(target=str(tmp_path))
        scanner._npm_audit(tmp_path, report)
    finally:
        scanner._run_cmd = orig  # type: ignore[assignment]
    ids = _rule_ids(report)
    assert "lodash" in ids
    sev = {f.rule_id: f.severity for f in report.findings}
    assert sev["lodash"] is ScanSeverity.BLOCKER
    assert sev["left-pad"] is ScanSeverity.MEDIUM


def test_bandit_parser(tmp_path: Path) -> None:
    payload = json.dumps({
        "results": [{
            "test_id": "B602",
            "issue_severity": "HIGH",
            "issue_text": "subprocess shell",
            "filename": "x.py",
            "line_number": 4,
        }]
    })

    class _Res:
        stdout = payload

    scanner = SecurityScanner()
    orig = scanner._run_cmd
    scanner._run_cmd = staticmethod(lambda *a, **k: _Res())  # type: ignore[assignment]
    try:
        report = ScanReport(target=str(tmp_path))
        scanner._bandit(tmp_path, report)
    finally:
        scanner._run_cmd = orig  # type: ignore[assignment]
    f = report.findings[0]
    assert f.rule_id == "B602"
    assert f.severity is ScanSeverity.HIGH
    assert f.line == 4
    assert f.scanner == "bandit"


def test_tools_skipped_when_absent(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _n: None)
    report = scan_project(tmp_path, use_tools=True)
    assert report.tools_run == []
    assert set(report.tools_skipped) >= {"bandit", "ruff", "npm", "composer", "trivy"}


class _Res:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout


def test_finding_to_dict_and_summary_counts(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "eval(x)\n")
    report = scan_project(tmp_path, use_tools=False)
    d = report.findings[0].to_dict()
    assert d["rule_id"] == "INJ-EVAL" and d["line"] == 1
    assert report.summary()["high"] >= 1


def test_dedupes_same_rule_same_line(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", "eval(x); eval(y)\n")
    report = scan_project(tmp_path, use_tools=False)
    assert len([f for f in report.findings if f.rule_id == "INJ-EVAL"]) == 1


def test_skips_non_scanned_extension(tmp_path: Path) -> None:
    _write(tmp_path, "app.log", "eval(1)\n")
    _write(tmp_path, "ok.py", "eval(z)\n")
    report = scan_project(tmp_path, use_tools=False)
    assert all(not f.file.endswith(".log") for f in report.findings)
    assert any(f.rule_id == "INJ-EVAL" for f in report.findings)


def test_oversized_file_skipped(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import runtime.security_scanner as ss

    monkeypatch.setattr(ss, "_MAX_FILE_BYTES", 8)
    _write(tmp_path, "big.py", "eval('" + "x" * 32 + "')\n")
    report = ss.scan_project(tmp_path, use_tools=False)
    assert all("big.py" not in f.file for f in report.findings)
    assert report.files_scanned == 0


def test_read_error_skips_file(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    target = _write(tmp_path, "bad.py", "eval(x)\n")
    orig = Path.read_text

    def flaky(self: Path, *a, **k):  # type: ignore[no-untyped-def]
        if self == target:
            raise OSError("locked")
        return orig(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", flaky)
    report = scan_project(tmp_path, use_tools=False)
    assert all("bad.py" not in f.file for f in report.findings)


def test_allowlisted_example_value_suppressed(tmp_path: Path) -> None:
    _write(tmp_path, "c.py", 'K = "AKIAIOSFODNN7EXAMPLE"\n')
    report = scan_project(tmp_path, use_tools=False)
    assert not any(f.rule_id == "SEC-AWS-KEY" for f in report.findings)


def test_run_cmd_real_and_oserror(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import subprocess as sp
    import sys

    res = SecurityScanner._run_cmd([sys.executable, "-c", "print(1)"], tmp_path)
    assert res is not None and res.stdout.strip() == "1"

    def boom(*a, **k):  # type: ignore[no-untyped-def]
        raise OSError("spawn failed")

    monkeypatch.setattr(sp, "run", boom)
    assert SecurityScanner._run_cmd(["nope"], tmp_path) is None


def test_all_tools_orchestrated(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import shutil

    _write(tmp_path, "requirements.txt", "pkg==1.0\n")
    _write(tmp_path, "package.json", "{}")
    _write(tmp_path, "composer.lock", "{}")
    monkeypatch.setattr(shutil, "which", lambda n: f"/tools/{n}")
    payloads = {
        "bandit": json.dumps({"results": [{
            "test_id": "B1", "issue_severity": "LOW", "issue_text": "t",
            "filename": "f.py", "line_number": 1}]}),
        "ruff": json.dumps([{
            "code": "S102", "message": "exec", "filename": "f.py",
            "location": {"row": 2}}]),
        "pip-audit": json.dumps({"dependencies": [{
            "name": "pkg", "version": "1.0",
            "vulns": [{"id": "CVE-1", "description": "d"}]}]}),
        "npm": json.dumps({"vulnerabilities": {"pkg": {"severity": "critical"}}}),
        "composer": json.dumps({"advisories": {
            "p/x": [{"advisoryId": "A1", "packageName": "p/x"}]}}),
        "trivy": json.dumps({"Results": [{
            "Target": "fs", "Vulnerabilities": [{
                "VulnerabilityID": "CVE-2", "Severity": "CRITICAL",
                "PkgName": "p", "Title": "t"}]}]}),
    }
    scanner = SecurityScanner()
    scanner._run_cmd = staticmethod(  # type: ignore[assignment]
        lambda argv, cwd: _Res(payloads.get(argv[0], ""))
    )
    report = scanner.scan(tmp_path, use_tools=True)
    assert set(report.tools_run) == {
        "bandit", "ruff", "pip-audit", "npm", "composer", "trivy"}
    scanners = {f.scanner for f in report.findings}
    assert {"bandit", "ruff", "pip-audit", "npm-audit",
            "composer-audit", "trivy"} <= scanners


def test_tool_none_empty_badjson_shortcircuit(tmp_path: Path) -> None:
    _write(tmp_path, "requirements.txt", "pkg==1.0\n")
    _write(tmp_path, "package.json", "{}")
    _write(tmp_path, "composer.lock", "{}")
    scanner = SecurityScanner()
    methods = (
        scanner._bandit, scanner._ruff_s, scanner._pip_audit,
        scanner._npm_audit, scanner._composer_audit, scanner._trivy,
    )
    for res in (None, _Res(""), _Res("not json{{{")):
        scanner._run_cmd = staticmethod(lambda a, c, r=res: r)  # type: ignore[assignment]
        report = ScanReport(target=str(tmp_path))
        for m in methods:
            m(tmp_path, report)
        assert not report.findings


def test_manifest_gated_tools_skip_without_files(tmp_path: Path) -> None:
    scanner = SecurityScanner()
    report = ScanReport(target=str(tmp_path))
    scanner._run_cmd = staticmethod(  # type: ignore[assignment]
        lambda a, c: _Res("SHOULD-NOT-RUN")
    )
    scanner._pip_audit(tmp_path, report)
    scanner._npm_audit(tmp_path, report)
    scanner._composer_audit(tmp_path, report)
    assert not report.findings
