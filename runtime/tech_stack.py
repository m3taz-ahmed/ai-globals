"""Auto-detect installed tech-stack versions from lockfiles and manifests."""

from __future__ import annotations

import json
import re
from pathlib import Path

# Map a package name (as it appears in lock/manifest files) to one or more
# tech-stack file name prefixes.  Both slash and dash forms are listed where
# composer normalizes the slash to a dash.
_TECH_STACK_ALIASES: dict[str, list[str]] = {
    # JavaScript / npm
    "next": ["nextjs"],
    "tailwindcss": ["tailwind"],
    "alpinejs": ["alpine"],
    "zod": ["zod-validation"],
    "zustand": ["zustand-state"],
    "framer-motion": ["framer-motion"],
    "@tanstack/react-query": ["tanstack-query"],
    "@tanstack/vue-query": ["tanstack-query"],
    "@tanstack/angular-query": ["tanstack-query"],
    "@tanstack/solid-query": ["tanstack-query"],
    "tanstack-react-query": ["tanstack-query"],
    "tanstack-vue-query": ["tanstack-query"],
    "tanstack-angular-query": ["tanstack-query"],
    "tanstack-solid-query": ["tanstack-query"],
    "react-query": ["tanstack-query"],
    "vue-query": ["tanstack-query"],
    "angular-query": ["tanstack-query"],
    "solid-query": ["tanstack-query"],
    "@clerk/nextjs": ["clerk-auth"],
    "@clerk/clerk-react": ["clerk-auth"],
    "@clerk/clerk-js": ["clerk-auth"],
    "clerk-nextjs": ["clerk-auth"],
    "clerk-react": ["clerk-auth"],
    "clerk-js": ["clerk-auth"],
    # PHP / composer
    "laravel/framework": ["laravel"],
    "laravel-framework": ["laravel"],
    "filament/filament": ["filament"],
    "filament/forms": ["filament"],
    "filament/tables": ["filament"],
    "filament/notifications": ["filament"],
    "filament-filament": ["filament"],
    "filament-forms": ["filament"],
    "filament-tables": ["filament"],
    "filament-notifications": ["filament"],
    "livewire/livewire": ["livewire"],
    "livewire-livewire": ["livewire"],
    "pestphp/pest": ["pest"],
    "pestphp-pest": ["pest"],
    "spatie/laravel-permission": ["spatie-permission"],
    "spatie-laravel-permission": ["spatie-permission"],
    "laravel-permission": ["spatie-permission"],
    "permission": ["spatie-permission"],
    "spatie/laravel-activitylog": ["spatie-activitylog"],
    "spatie-laravel-activitylog": ["spatie-activitylog"],
    "laravel-activitylog": ["spatie-activitylog"],
    "activitylog": ["spatie-activitylog"],
    "stripe/stripe-php": ["stripe-integration"],
    "stripe-stripe-php": ["stripe-integration"],
    "stripe-php": ["stripe-integration"],
    "stripe": ["stripe-integration"],
    "sentry/sentry": ["sentry-tracking"],
    "sentry-sentry": ["sentry-tracking"],
    "predis/predis": ["redis"],
    "predis-predis": ["redis"],
    "meilisearch/meilisearch": ["meilisearch"],
    "meilisearch-meilisearch": ["meilisearch"],
    "php": ["php"],
    "mysql": ["mysql"],
    "redis": ["redis"],
    "node": ["nodejs"],
    "nodejs": ["nodejs"],
}


def _clean_version(constraint: str) -> str | None:
    """Return a usable numeric version string from a semver constraint."""
    if not isinstance(constraint, str):
        return None
    constraint = constraint.strip()
    if constraint in ("*", "latest", ""):
        return None
    if constraint.startswith(("dev-", "git+", "file:", "https:", "github:")):
        return None
    # Take the first alternative if the constraint is a range.
    token = re.split(r"[|, ]", constraint)[0].strip()
    token = token.lstrip("v^~<>= ")
    if token in ("", "*", "x"):
        return None
    # Convert wildcard ranges like 8.x / 8.* into 8.0.
    if token.endswith((".x", ".*")):
        token = token[:-2] + ".0"
    return token


def _version_triple(version: str) -> tuple[int, int, int] | None:
    m = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0)


def _package_names(raw: str) -> list[str]:
    """Expand a raw package name into candidate base names."""
    names: set[str] = set()
    raw = raw.strip()
    if raw.startswith("node_modules/"):
        raw = raw[len("node_modules/"):]
    names.add(raw)
    # composer normalizes '/' to '-'.
    hyphenated = raw.replace("/", "-")
    if hyphenated != raw:
        names.add(hyphenated)
    if "-" in hyphenated:
        parts = hyphenated.split("-")
        names.add(parts[0])  # vendor / scope
        names.add(parts[-1])  # package tail
        if len(parts) >= 3:
            names.add("-".join(parts[1:]))  # middle
    if raw.startswith("@"):
        scope, pkg = raw[1:].split("/", 1)
        names.add(pkg)
        names.add(f"{scope}-{pkg}")
    return list(names)


def _candidate_prefixes(raw_name: str) -> list[str]:
    """Return ordered tech-stack filename prefixes to try for a package."""
    prefixes: list[str] = []
    seen: set[str] = set()
    for name in _package_names(raw_name):
        for prefix in _TECH_STACK_ALIASES.get(name, [name]):
            if prefix not in seen:
                seen.add(prefix)
                prefixes.append(prefix)
    return prefixes


def _candidate_stems(prefix: str, version: str) -> list[str]:
    """Generate filename stems to try for a prefix + version."""
    candidates = [prefix]
    triple = _version_triple(version)
    if triple is None:
        return candidates
    major, minor, patch = triple
    candidates.extend(
        [
            f"{prefix}-{version}",
            f"{prefix}-{major}",
            f"{prefix}-{major}.{minor}",
            f"{prefix}-{major}-{minor}",
            f"{prefix}-{major}.{minor}.{patch}",
            f"{prefix}-{major}-{minor}-{patch}",
            f"{prefix}-ecosystem",
        ]
    )
    return candidates


def _resolve_tech_stack(raw_name: str, version: str, os_root: Path) -> Path | None:
    """Find the best matching tech-stack markdown file for a package."""
    tech_dir = os_root / "tech-stack"
    if not tech_dir.is_dir():
        return None
    for prefix in _candidate_prefixes(raw_name):
        for stem in _candidate_stems(prefix, version):
            path = tech_dir / f"{stem}.md"
            if path.is_file():
                return path
    return None


def _parse_package_lock(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    versions: dict[str, str] = {}
    packages = data.get("packages") or data.get("dependencies") or {}
    for key, info in packages.items():
        if not isinstance(info, dict):
            continue
        if key == "":
            # npm v3 root package carries constraints in dependencies.
            for dep_key in ("dependencies", "devDependencies"):
                for dep_name, constraint in (info.get(dep_key) or {}).items():
                    cleaned = _clean_version(constraint)
                    if cleaned:
                        versions[dep_name] = cleaned
            continue
        if key.startswith("node_modules/"):
            raw_name = key[len("node_modules/"):]
            version = info.get("version")
            if version and isinstance(version, str):
                versions[raw_name] = version
            continue
        # Legacy lockfile: keys are package names.
        version = info.get("version")
        if version and isinstance(version, str):
            versions[key] = version
    return versions


def _parse_composer_lock(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    versions: dict[str, str] = {}
    for section in ("packages", "packages-dev"):
        for pkg in data.get(section, []) or []:
            name = pkg.get("name", "")
            version = pkg.get("version", "")
            if name and version:
                versions[name] = version
    return versions


def _parse_package_json(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    versions: dict[str, str] = {}
    for section in ("dependencies", "devDependencies"):
        for name, constraint in (data.get(section) or {}).items():
            cleaned = _clean_version(constraint)
            if cleaned:
                versions[name] = cleaned
    return versions


def _parse_composer_json(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    versions: dict[str, str] = {}
    for section in ("require", "require-dev"):
        for name, constraint in (data.get(section) or {}).items():
            cleaned = _clean_version(constraint)
            if cleaned:
                versions[name] = cleaned
    return versions


def detect_stack(project_root: Path, os_root: Path) -> dict[str, dict[str, object]]:
    """Detect installed stack and return matched tech-stack docs info."""
    detected: dict[str, dict[str, object]] = {}

    # Lockfiles are ground truth and take precedence.
    lockfiles = [
        (project_root / "package-lock.json", _parse_package_lock),
        (project_root / "composer.lock", _parse_composer_lock),
    ]
    for lockfile, parser in lockfiles:
        if not lockfile.exists():
            continue
        try:
            versions = parser(lockfile)
        except Exception:
            continue
        for name, version in versions.items():
            path = _resolve_tech_stack(name, version, os_root)
            if path:
                detected[name] = {"version": version, "path": path.relative_to(os_root).as_posix()}

    # Manifests provide constraints when a lockfile is absent or incomplete.
    manifests = [
        (project_root / "package.json", _parse_package_json),
        (project_root / "composer.json", _parse_composer_json),
    ]
    for manifest, parser in manifests:
        if not manifest.exists():
            continue
        try:
            versions = parser(manifest)
        except Exception:
            continue
        for name, version in versions.items():
            if name in detected:
                continue
            path = _resolve_tech_stack(name, version, os_root)
            if path:
                detected[name] = {"version": version, "path": path.relative_to(os_root).as_posix()}

    return detected


def load_stack_docs(project_root: Path, os_root: Path) -> dict[str, str]:
    """Load contents of matched tech-stack docs."""
    contents: dict[str, str] = {}
    for name, info in detect_stack(project_root, os_root).items():
        path = os_root / str(info["path"])
        if path.exists():
            contents[name] = path.read_text(encoding="utf-8")
    return contents
