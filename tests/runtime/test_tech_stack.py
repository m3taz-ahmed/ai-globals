"""Tests for tech-stack auto-detection."""

from __future__ import annotations

from pathlib import Path

from runtime.kernel import Kernel
from runtime.tech_stack import detect_stack, load_stack_docs


def test_detect_from_package_lock(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "react-18.2.0.md").write_text("# React 18.2\n", encoding="utf-8")
    (project / "package-lock.json").write_text(
        '{"packages": {"": {"dependencies": {"react": "^18.2.0"}}, '
        '"node_modules/react": {"version": "18.2.0"}}}',
        encoding="utf-8",
    )
    detected = detect_stack(project, os_root)
    assert "react" in detected
    assert detected["react"]["version"] == "18.2.0"


def test_load_stack_docs(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "react-18.2.0.md").write_text("# React 18.2\n", encoding="utf-8")
    (project / "package-lock.json").write_text(
        '{"packages": {"node_modules/react": {"version": "18.2.0"}}}',
        encoding="utf-8",
    )
    docs = load_stack_docs(project, os_root)
    assert "react" in docs


def test_kernel_detect_tech_stack(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "react-18.2.0.md").write_text("# React 18.2\n", encoding="utf-8")
    (project / "package-lock.json").write_text(
        '{"packages": {"node_modules/react": {"version": "18.2.0"}}}',
        encoding="utf-8",
    )
    k = Kernel(os_root, project)
    detected = k.detect_tech_stack()
    assert "react" in detected


def test_detect_major_minor_naming(tmp_path: Path) -> None:
    """tech-stack files use hyphenated major-minor names, not exact patch."""
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "php-8-3.md").write_text("# PHP 8.3\n", encoding="utf-8")
    (project / "composer.lock").write_text(
        '{"packages": [{"name": "php", "version": "8.3.11"}]}',
        encoding="utf-8",
    )
    detected = detect_stack(project, os_root)
    assert "php" in detected
    assert detected["php"]["path"] == "tech-stack/php-8-3.md"


def test_detect_from_package_json_without_lock(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "tailwind-4.md").write_text("# Tailwind 4\n", encoding="utf-8")
    (project / "package.json").write_text(
        '{"dependencies": {"tailwindcss": "^4.1.0"}}',
        encoding="utf-8",
    )
    detected = detect_stack(project, os_root)
    assert "tailwindcss" in detected
    assert detected["tailwindcss"]["path"] == "tech-stack/tailwind-4.md"


def test_detect_laravel_from_composer_json(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "laravel-12.md").write_text("# Laravel 12\n", encoding="utf-8")
    (project / "composer.json").write_text(
        '{"require": {"laravel/framework": "^12.0"}}',
        encoding="utf-8",
    )
    detected = detect_stack(project, os_root)
    assert "laravel/framework" in detected
    assert detected["laravel/framework"]["path"] == "tech-stack/laravel-12.md"
