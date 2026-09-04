"""Design Library — 56 brand design systems loaded on demand.

Inspired by zeta92/design-library-plugin. Provides a catalog of real-world
brand design systems (Stripe, Linear, Vercel, Figma, etc.) that can be loaded
and applied to UI work. Each brand is stored as a ``DESIGN.md`` file with
tokens (colors, typography, spacing, radii, shadows, grid) and design
principles.

The library supports:
- **Single brand** — load one brand's full design system
- **Simple mix** — combine 2-3 brands (colors from A, typography from B)
- **Granular mix** — mix specific sections (A:colors + B:typography)
- **Auto-detect** — scan project and suggest best-fit brands
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import ClassVar

from runtime.schemas import AizeeError, ErrorSeverity


class DesignSection(str, Enum):
    """Sections of a brand design system."""

    COLORS = "colors"
    TYPOGRAPHY = "typography"
    COMPONENTS = "components"
    LAYOUT = "layout"
    ELEVATION = "elevation"


class ProjectType(str, Enum):
    """Detected project type for auto-suggestion."""

    LANDING_PAGE = "landing_page"
    SAAS_APP = "saas_app"
    DESIGN_SYSTEM = "design_system"
    ECOMMERCE = "ecommerce"
    PORTFOLIO = "portfolio"
    BLOG = "blog"
    DASHBOARD = "dashboard"
    MOBILE_APP = "mobile_app"
    UNKNOWN = "unknown"


@dataclass
class BrandDesignSystem:
    """A loaded brand design system."""

    name: str
    path: Path
    content: str = ""
    sections: dict[str, str] = field(default_factory=dict)

    def get_section(self, section: DesignSection) -> str:
        """Extract a specific section from the DESIGN.md content."""
        if section.value in self.sections:
            return self.sections[section.value]
        # Try to extract from content
        pattern = f"## {section.value.title()}"
        idx = self.content.lower().find(pattern.lower())
        if idx == -1:
            return ""
        end_idx = self.content.find("\n## ", idx + 1)
        extracted = self.content[idx:] if end_idx == -1 else self.content[idx:end_idx]
        self.sections[section.value] = extracted
        return extracted


@dataclass
class FusionResult:
    """Result of mixing multiple brand design systems."""

    brands: list[str]
    section_mapping: dict[str, str]  # section → brand name
    content: str
    rationale: str


class DesignLibrary:
    """Catalog of brand design systems with loading and mixing capabilities.

    Brand DESIGN.md files live in ``<root>/design-library/<brand>/DESIGN.md``.
    The library lazily loads brands on first access and caches them.
    """

    DESIGN_FILE: ClassVar[str] = "DESIGN.md"

    # Curated catalog of 56 unique brand design systems.
    # In production, these would be downloaded from the awesome-design-md repo.
    CATALOG: ClassVar[list[str]] = [
        "stripe", "linear", "vercel", "figma", "google", "anthropic",
        "apple", "microsoft", "github", "notion", "slack", "discord",
        "spotify", "airbnb", "uber", "shopify", "framer", "supabase",
        "clerk", "resend", "posthog", "plane", "calcom", "dub",
        "openai", "perplexity", "mistral", "cohere", "huggingface",
        "sentry", "datadog", "cloudflare", "netlify", "railway",
        "fly", "render", "heroku", "digitalocean", "linode",
        "tailwind", "shadcn", "radix", "cmdk", "vaul", "sonner",
        "astria", "creatio", "envshare", "nutlope",
        "react-email", "koala", "flightscope",
        "chronark", "leerob", "steven-tey", "shadcn-personal",
    ]

    # Project type → recommended brands mapping
    PROJECT_SUGGESTIONS: ClassVar[dict[ProjectType, list[str]]] = {
        ProjectType.LANDING_PAGE: ["linear", "vercel", "framer", "dub"],
        ProjectType.SAAS_APP: ["stripe", "linear", "supabase", "clerk"],
        ProjectType.DESIGN_SYSTEM: ["figma", "shadcn", "radix", "tailwind"],
        ProjectType.ECOMMERCE: ["shopify", "stripe", "airbnb"],
        ProjectType.PORTFOLIO: ["vercel", "framer", "chronark", "leerob"],
        ProjectType.BLOG: ["vercel", "leerob", "steven-tey"],
        ProjectType.DASHBOARD: ["linear", "sentry", "datadog", "posthog"],
        ProjectType.MOBILE_APP: ["apple", "google", "spotify", "airbnb"],
        ProjectType.UNKNOWN: ["vercel", "linear", "stripe"],
    }

    def __init__(self, library_dir: Path | None = None) -> None:
        """Initialize the design library.

        Args:
            library_dir: Directory containing brand folders. Defaults to
                ``<root>/design-library/``.
        """
        self._dir = library_dir
        self._cache: dict[str, BrandDesignSystem] = {}

    @property
    def available_brands(self) -> list[str]:
        """List all available brand names (catalog + filesystem)."""
        brands: set[str] = set(self.CATALOG)
        if self._dir and self._dir.exists():
            for d in self._dir.iterdir():
                if d.is_dir() and (d / self.DESIGN_FILE).exists():
                    brands.add(d.name.lower())
        return sorted(brands)

    def load(self, brand: str) -> BrandDesignSystem | None:
        """Load a single brand's design system.

        Args:
            brand: Brand name (case-insensitive, e.g., "Stripe" → "stripe").

        Returns:
            BrandDesignSystem or None if not found.
        """
        key = brand.lower().strip()
        # Confine brand key: reject path traversal and separators.
        if not key or key in (".", "..") or ".." in key or "/" in key or "\\" in key:
            return None
        if key in self._cache:
            return self._cache[key]

        if self._dir is None:
            return None

        brand_path = self._dir / key / self.DESIGN_FILE
        if not brand_path.exists():
            return None

        try:
            content = brand_path.read_text(encoding="utf-8")
        except OSError:
            return None

        system = BrandDesignSystem(name=key, path=brand_path, content=content)
        self._cache[key] = system
        return system

    def mix(
        self,
        brands: list[str],
        section_mapping: dict[DesignSection, str] | None = None,
    ) -> FusionResult | None:
        """Mix multiple brand design systems.

        Args:
            brands: List of 2-3 brand names to mix.
            section_mapping: Optional explicit section→brand mapping.
                If None, uses defaults (colors/components/elevation from first,
                typography/layout from second).

        Returns:
            FusionResult or None if any brand is missing.
        """
        loaded: list[BrandDesignSystem] = []
        for b in brands:
            system = self.load(b)
            if system is None:
                return None
            loaded.append(system)

        if section_mapping is None:
            section_mapping = self._default_mapping(brands)

        sections_content: list[str] = []
        mapping_str: dict[str, str] = {}
        for section, brand_name in section_mapping.items():
            # Fail-closed: unknown brand in mapping → abort mix (return None).
            system = next((s for s in loaded if s.name == brand_name.lower()), None)
            if system is None:
                return None
            section_text = system.get_section(section)
            if section_text:
                sections_content.append(section_text)
                mapping_str[section.value] = brand_name

        rationale = self._build_rationale(brands, mapping_str)
        return FusionResult(
            brands=brands,
            section_mapping=mapping_str,
            content="\n\n---\n\n".join(sections_content),
            rationale=rationale,
        )

    def suggest(self, project_type: ProjectType) -> list[str]:
        """Suggest best-fit brands for a project type."""
        return list(self.PROJECT_SUGGESTIONS.get(project_type, self.PROJECT_SUGGESTIONS[ProjectType.UNKNOWN]))

    def detect_project_type(self, project_dir: Path) -> ProjectType:
        """Detect project type from directory contents."""
        if not project_dir.exists():
            return ProjectType.UNKNOWN

        indicators: list[tuple[ProjectType, list[str]]] = [
            (ProjectType.ECOMMERCE, ["shop", "product", "cart", "checkout", "woocommerce"]),
            (ProjectType.DASHBOARD, ["dashboard", "admin", "panel", "analytics"]),
            (ProjectType.LANDING_PAGE, ["landing", "hero", "marketing", "pitch"]),
            (ProjectType.BLOG, ["blog", "article", "post", "markdown"]),
            (ProjectType.PORTFOLIO, ["portfolio", "resume", "cv", "about"]),
            (ProjectType.MOBILE_APP, ["flutter", "react-native", "expo", "ios", "android"]),
            (ProjectType.DESIGN_SYSTEM, ["design-system", "tokens", "storybook", "components"]),
            (ProjectType.SAAS_APP, ["app", "saas", "auth", "dashboard", "api"]),
        ]

        all_files: list[str] = []
        # Bounded scan: max 2000 files, skip vendored dirs, no symlink follow.
        _skip_dirs = {"node_modules", ".git", ".venv", "__pycache__"}
        _count = 0
        _stack: list[Path] = [project_dir]
        while _stack and _count < 2000:
            current = _stack.pop()
            try:
                if current.is_symlink():
                    continue
                if current.is_dir():
                    if current.name in _skip_dirs and current != project_dir:
                        continue
                    try:
                        with os.scandir(current) as it:
                            entries = list(it)
                    except OSError:
                        continue
                    for entry in entries:
                        try:
                            if entry.is_symlink():
                                continue
                        except OSError:
                            continue
                        _stack.append(Path(entry.path))
                elif current.is_file():
                    _count += 1
                    all_files.append(str(current).lower())
            except OSError:
                continue

        scores: dict[ProjectType, int] = {}
        for ptype, keywords in indicators:
            score = sum(1 for kw in keywords if any(kw in fp for fp in all_files))
            if score > 0:
                scores[ptype] = score

        if not scores:
            return ProjectType.UNKNOWN
        return max(scores, key=lambda k: scores[k])

    def _default_mapping(self, brands: list[str]) -> dict[DesignSection, str]:
        """Default section→brand mapping for simple mixes."""
        first = brands[0] if brands else ""
        second = brands[1] if len(brands) > 1 else first
        return {
            DesignSection.COLORS: first,
            DesignSection.COMPONENTS: first,
            DesignSection.ELEVATION: first,
            DesignSection.TYPOGRAPHY: second,
            DesignSection.LAYOUT: second,
        }

    def _build_rationale(self, brands: list[str], mapping: dict[str, str]) -> str:
        """Build a human-readable rationale for the fusion."""
        lines = [f"Fusion: {' + '.join(brands)}"]
        for section, brand in sorted(mapping.items()):
            lines.append(f"  {section} → {brand}")
        lines.append(f"Rationale: This combination pairs {'visual identity from ' + brands[0] if brands else ''}"
                     f" with {'structural rhythm from ' + brands[1] if len(brands) > 1 else 'cohesive design'}.")
        return "\n".join(lines)


# -- Exception -----------------------------------------------------------------


class DesignLibraryError(AizeeError):
    """Raised when the design library encounters an error."""

    def __init__(self, message: str, context: dict[str, object] | None = None) -> None:
        super().__init__("DESIGN_LIBRARY_ERROR", message, ErrorSeverity.LOW, context)
