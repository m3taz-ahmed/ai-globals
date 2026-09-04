"""AI-Slop Verifier — detects generic, templated "AI slop" in design output.

Inspired by claude-design-mode's design-verifier subagent. Reviews screenshots
and HTML against a 7-category checklist to catch the cookie-cutter patterns
that scream "AI generated this": gradient washes, accent-border cards, SVG
illustrations, overused fonts, emoji decorations, three-column feature grids,
and AI-headline phrases.

The verifier is model-free by default (deterministic pattern matching on HTML
text) and optionally accepts an injectable ``judge_fn`` for visual/screenshot
analysis via a vision model.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from runtime.schemas import AizeeError, ErrorSeverity


class SlopCategory(str, Enum):
    """The 7 categories of AI design slop."""

    GRADIENT_WASH = "gradient_wash"
    ACCENT_BORDER_CARDS = "accent_border_cards"
    SVG_ILLUSTRATIONS = "svg_illustrations"
    OVERUSED_FONTS = "overused_fonts"
    EMOJI_DECORATION = "emoji_decoration"
    THREE_COLUMN_GRID = "three_column_grid"
    AI_HEADLINE_PHRASES = "ai_headline_phrases"


class SlopSeverity(str, Enum):
    """Severity of a slop finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SlopFinding:
    """A single AI-slop detection finding."""

    category: SlopCategory
    severity: SlopSeverity
    evidence: str
    suggestion: str


@dataclass
class SlopVerdict:
    """Full verdict from the AI-slop verifier."""

    html: str
    findings: list[SlopFinding] = field(default_factory=list)
    passed: bool = True
    slop_threshold: int = 30

    @property
    def score(self) -> int:
        """0 (clean) to 100 (maximum slop). Weighted by severity."""
        weights = {
            SlopSeverity.CRITICAL: 25,
            SlopSeverity.HIGH: 15,
            SlopSeverity.MEDIUM: 8,
            SlopSeverity.LOW: 3,
        }
        return min(100, sum(weights.get(f.severity, 5) for f in self.findings))

    @property
    def is_slop(self) -> bool:
        """True if the output has enough slop to warrant a redesign."""
        return self.score >= self.slop_threshold or any(
            f.severity == SlopSeverity.CRITICAL for f in self.findings
        )

    def summary(self) -> str:
        """Human-readable summary."""
        if self.passed:
            return "✅ Pass — no significant AI slop detected"
        lines = [f"❌ Slop detected (score {self.score}/100):"]
        for f in self.findings:
            lines.append(f"  [{f.severity.value}] {f.category.value}: {f.evidence}")
        return "\n".join(lines)


class DesignSlopVerifier:
    """Verify design output against an AI-slop checklist.

    The verifier scans HTML/CSS text for the 7 categories of generic AI design
    patterns. An optional ``judge_fn`` can be injected for visual analysis of
    screenshots (vision-model-based).
    """

    # -- Pattern definitions --------------------------------------------------

    _GRADIENT_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"linear-gradient\s*\([^)]*(?:purple|indigo|violet|blue-pink|pink-blue)", "purple/blue gradient wash"),
        (r"background\s*:\s*linear-gradient\s*\([^)]*135deg", "generic 135deg gradient"),
        (r"bg-gradient-to-[brtr]\s+from-(?:purple|indigo|violet)\b", "Tailwind purple gradient"),
    ]

    _ACCENT_BORDER_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"border-(?:l|r|t|b)-[248]\s+border-(?:purple|indigo|blue|violet)", "accent left-border card"),
        (r"border-l-[248].*?border-[a-z]+-500", "colored left-border accent"),
    ]

    _SVG_ILLUSTRATION_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"<svg[^>]*(?:illustration|undraw|storyset|heroicons|lucide)", "generic SVG illustration set"),
        (r"data:image/svg.*?(?:undraw|storyset)", "embedded illustration SVG"),
    ]

    _OVERUSED_FONTS: ClassVar[set[str]] = {
        "inter",
        "poppins",
        "montserrat",
        "roboto",
        "open sans",
        "lato",
        "raleway",
    }

    _EMOJI_PATTERN: ClassVar[str] = (
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        r"\U0001F1E0-\U0001F1FF\U00002700-\U000027BF]"
    )

    _THREE_COLUMN_PATTERNS: ClassVar[list[tuple[str, str]]] = [
        (r"grid-cols-3.*?grid-cols-3", "repeated 3-column grid layout"),
        (r"display\s*:\s*grid.*?grid-template-columns\s*:\s*repeat\(3", "CSS 3-column grid"),
    ]

    _AI_HEADLINE_PHRASES: ClassVar[list[str]] = [
        "supercharge your",
        "supercharge their",
        "unlock the power",
        "unlock your potential",
        "seamlessly integrate",
        "seamless integration",
        "powerful and intuitive",
        "intuitive and powerful",
        "next-generation platform",
        "cutting-edge solution",
        "revolutionary approach",
        "game-changing",
        "game changer",
        "one-stop solution",
        "all-in-one platform",
        "elevate your",
        "transform your business",
        "empower your team",
        "harness the power",
        "leverage ai",
        "ai-powered platform",
        "built for the future",
        "future-proof",
        "scale effortlessly",
        "effortlessly scale",
    ]

    def __init__(
        self,
        *,
        slop_threshold: int = 30,
        judge_fn: Callable[[str, str], list[SlopFinding]] | None = None,
    ) -> None:
        """Initialize the verifier.

        Args:
            slop_threshold: Score threshold above which output is flagged as slop.
            judge_fn: Optional injectable vision-model judge. Receives
                (html, screenshot_path) and returns additional findings.
        """
        if slop_threshold < 0:
            raise DesignSlopError(
                f"slop_threshold must be >= 0, got {slop_threshold}",
                context={"slop_threshold": slop_threshold},
            )
        self._threshold = slop_threshold
        self._judge_fn = judge_fn

    def verify(self, html: str, *, screenshot_path: str | None = None) -> SlopVerdict:
        """Verify HTML output for AI slop.

        Args:
            html: The HTML/CSS text to check.
            screenshot_path: Optional path to a screenshot for visual analysis.

        Returns:
            A SlopVerdict with all findings and a pass/fail determination.
        """
        findings: list[SlopFinding] = []
        findings.extend(self._check_gradients(html))
        findings.extend(self._check_accent_borders(html))
        findings.extend(self._check_svg_illustrations(html))
        findings.extend(self._check_overused_fonts(html))
        findings.extend(self._check_emoji_decoration(html))
        findings.extend(self._check_three_column_grid(html))
        findings.extend(self._check_ai_headlines(html))

        # Optional vision-model judge: failure must mark result uncertain,
        # never silently pass.
        if self._judge_fn and screenshot_path:
            try:
                findings.extend(self._judge_fn(html, screenshot_path))
            except Exception as exc:
                findings.append(SlopFinding(
                    category=SlopCategory.SVG_ILLUSTRATIONS,
                    severity=SlopSeverity.LOW,
                    evidence=f"vision judge unavailable ({type(exc).__name__}); visual review uncertain",
                    suggestion="Retry visual review manually or re-run with a working judge_fn.",
                ))

        verdict = SlopVerdict(html=html, findings=findings, passed=True, slop_threshold=self._threshold)
        verdict.passed = not verdict.is_slop
        return verdict

    def verify_batch(
        self,
        items: list[tuple[str, str | None]],
    ) -> list[SlopVerdict]:
        """Verify multiple HTML files. Each item is (html, screenshot_path)."""
        return [self.verify(html, screenshot_path=ss) for html, ss in items]

    # -- Individual category checks -------------------------------------------

    def _check_gradients(self, html: str) -> list[SlopFinding]:
        results: list[SlopFinding] = []
        for pattern, desc in self._GRADIENT_PATTERNS:
            if re.search(pattern, html, re.IGNORECASE):
                results.append(SlopFinding(
                    category=SlopCategory.GRADIENT_WASH,
                    severity=SlopSeverity.HIGH,
                    evidence=desc,
                    suggestion="Use a solid brand color or a restrained duotone instead of a gradient wash.",
                ))
        return results

    def _check_accent_borders(self, html: str) -> list[SlopFinding]:
        results: list[SlopFinding] = []
        for pattern, desc in self._ACCENT_BORDER_PATTERNS:
            if re.search(pattern, html, re.IGNORECASE):
                results.append(SlopFinding(
                    category=SlopCategory.ACCENT_BORDER_CARDS,
                    severity=SlopSeverity.MEDIUM,
                    evidence=desc,
                    suggestion="Use elevation, background tint, or a full border instead of a left-accent stripe.",
                ))
        return results

    def _check_svg_illustrations(self, html: str) -> list[SlopFinding]:
        results: list[SlopFinding] = []
        for pattern, desc in self._SVG_ILLUSTRATION_PATTERNS:
            if re.search(pattern, html, re.IGNORECASE):
                results.append(SlopFinding(
                    category=SlopCategory.SVG_ILLUSTRATIONS,
                    severity=SlopSeverity.MEDIUM,
                    evidence=desc,
                    suggestion="Use custom photography, product screenshots, or original illustrations.",
                ))
        return results

    def _check_overused_fonts(self, html: str) -> list[SlopFinding]:
        results: list[SlopFinding] = []
        font_matches = re.findall(r"font-family\s*:\s*['\"]?([^;'\"{]+)", html, re.IGNORECASE)
        # Tailwind utility classes: class="... font-sans ...", class='... font-mono ...'
        tailwind_fonts = re.findall(r"""class\s*=\s*["'][^"']*\bfont-(sans|mono)\b[^"']*["']""", html, re.IGNORECASE)
        for tf in tailwind_fonts:
            font_matches.append(tf)
        for font in font_matches:
            font_clean = font.strip().lower()
            if font_clean in self._OVERUSED_FONTS or font_clean in ("sans", "mono"):
                label = f"'{font_clean}' is an overused AI-default font" if font_clean in self._OVERUSED_FONTS else (
                    f"'font-{font_clean}' Tailwind default stack (often Inter/ui-monospace) — pick a distinctive pairing"
                )
                results.append(SlopFinding(
                    category=SlopCategory.OVERUSED_FONTS,
                    severity=SlopSeverity.MEDIUM,
                    evidence=label,
                    suggestion="Pair a distinctive display font (e.g., Fraunces, Space Grotesk) with a clean body font.",
                ))
                break  # One finding per file is enough
        return results

    def _check_emoji_decoration(self, html: str) -> list[SlopFinding]:
        results: list[SlopFinding] = []
        emoji_count = len(re.findall(self._EMOJI_PATTERN, html))
        if emoji_count >= 3:
            results.append(SlopFinding(
                category=SlopCategory.EMOJI_DECORATION,
                severity=SlopSeverity.LOW,
                evidence=f"{emoji_count} emoji found in HTML (decorative overuse)",
                suggestion="Replace emoji with proper iconography (Iconsax, Phosphor, Lucide).",
            ))
        return results

    def _check_three_column_grid(self, html: str) -> list[SlopFinding]:
        results: list[SlopFinding] = []
        for pattern, desc in self._THREE_COLUMN_PATTERNS:
            if re.search(pattern, html, re.IGNORECASE | re.DOTALL):
                results.append(SlopFinding(
                    category=SlopCategory.THREE_COLUMN_GRID,
                    severity=SlopSeverity.HIGH,
                    evidence=desc,
                    suggestion="Use asymmetric layouts, bento grids, or editorial spacing instead of 3-equal-columns.",
                ))
        return results

    def _check_ai_headlines(self, html: str) -> list[SlopFinding]:
        results: list[SlopFinding] = []
        text = re.sub(r"<[^>]+>", " ", html)  # Strip tags for text analysis
        text_lower = text.lower()
        for phrase in self._AI_HEADLINE_PHRASES:
            if phrase in text_lower:
                results.append(SlopFinding(
                    category=SlopCategory.AI_HEADLINE_PHRASES,
                    severity=SlopSeverity.CRITICAL,
                    evidence=f"'{phrase}' is a cliché AI headline phrase",
                    suggestion="Write specific, concrete copy that describes what the product actually does.",
                ))
                break  # One finding per file
        return results


# -- Exception -----------------------------------------------------------------


class DesignSlopError(AizeeError):
    """Raised when the slop verifier encounters an error."""

    def __init__(self, message: str, context: dict[str, object] | None = None) -> None:
        super().__init__("SLOP_ERROR", message, ErrorSeverity.MEDIUM, context)
