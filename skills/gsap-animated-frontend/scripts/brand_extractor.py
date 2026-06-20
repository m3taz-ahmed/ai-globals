"""Brand and design signal extraction helpers for GSAP workflows."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

STYLE_EXTENSIONS = (".css", ".scss", ".sass", ".less", ".pcss")
COLOR_PATTERN = re.compile(
    r"(#(?:[0-9a-fA-F]{3,8})\b|rgba?\([^)]+\)|hsla?\([^)]+\)|oklch\([^)]+\)|oklab\([^)]+\))"
)

TONE_KEYWORDS = (
    "luxury",
    "premium",
    "playful",
    "editorial",
    "booking",
    "dashboard",
    "minimal",
    "bold",
    "3d",
    "glass",
    "cinematic",
    "futuristic",
    "sleek",
    "energetic",
    "corporate",
    "elegant",
    "immersive",
    "clean",
    "vibrant",
    "brutalist",
    "organic",
    "minimalist",
    "fashion",
    "saas",
    "fintech",
    "ai",
    "startup",
)


def find_brand_files(root: Path, scan_files):
    """Return likely files that define design language."""
    candidate_paths = [
        root / "tailwind.config.ts",
        root / "tailwind.config.js",
        root / "tailwind.config.cjs",
        root / "src" / "app" / "globals.css",
        root / "src" / "styles" / "globals.css",
        root / "app" / "globals.css",
        root / "styles" / "globals.css",
        root / "styles" / "theme.css",
        root / "styles" / "tokens.css",
        root / "styles" / "variables.css",
        root / "src" / "styles" / "theme.css",
        root / "src" / "styles" / "tokens.css",
        root / "src" / "styles" / "variables.css",
        root / "src" / "theme" / "index.ts",
        root / "src" / "theme" / "tokens.ts",
        root / "src" / "design-system" / "tokens.ts",
        root / "src" / "design-system" / "theme.ts",
        root / "apps" / "web" / "tailwind.config.ts",
        root / "apps" / "web" / "tailwind.config.js",
        root / "apps" / "web" / "src" / "app" / "globals.css",
        root / "apps" / "web" / "src" / "styles" / "globals.css",
        root / "apps" / "web" / "src" / "styles" / "theme.css",
    ]

    files = [path for path in candidate_paths if path.exists()]
    for source_file in scan_files(root, include_styles=True):
        if source_file.suffix in STYLE_EXTENSIONS:
            files.append(source_file)

    unique = []
    for path in files:
        if path not in unique:
            unique.append(path)
    return unique[:60]


def extract_brand_signals(root: Path, scan_files, read_text):
    """Extract colors, fonts, css vars, and style direction hints."""
    colors = Counter()
    fonts = Counter()
    css_vars = Counter()
    shadows = Counter()
    radii = Counter()
    tone_hints = Counter()
    gradients = 0
    blur_usage = 0
    backdrop_usage = 0
    uppercase_usage = 0
    letter_spacing_usage = 0

    for source_file in find_brand_files(root, scan_files):
        content = read_text(source_file)
        lower = content.lower()

        for color in COLOR_PATTERN.findall(content):
            colors[color] += 1
        for font_match in re.findall(r"font-family\s*:\s*([^;]+);", content, flags=re.I):
            fonts[font_match.strip()] += 1
        for var_match in re.findall(r"(--[A-Za-z0-9-_]+)\s*:", content):
            css_vars[var_match] += 1
        for shadow_match in re.findall(r"box-shadow\s*:\s*([^;]+);", content, flags=re.I):
            shadows[shadow_match.strip()] += 1
        for radius_match in re.findall(r"border-radius\s*:\s*([^;]+);", content, flags=re.I):
            radii[radius_match.strip()] += 1
        if "gradient" in lower:
            gradients += lower.count("gradient")
        if "blur" in lower:
            blur_usage += lower.count("blur")
        if "backdrop-filter" in lower:
            backdrop_usage += lower.count("backdrop-filter")
        if "text-transform: uppercase" in lower:
            uppercase_usage += lower.count("text-transform: uppercase")
        if "letter-spacing" in lower or "tracking-" in lower:
            letter_spacing_usage += lower.count("letter-spacing") + lower.count("tracking-")
        for keyword in TONE_KEYWORDS:
            if keyword in lower:
                tone_hints[keyword] += lower.count(keyword)

    visual_direction = []
    if gradients:
        visual_direction.append("gradient-rich")
    if blur_usage or backdrop_usage or any("blur" in item.lower() for item in css_vars):
        visual_direction.append("glass-friendly")
    if any("rem" in item or "px" in item for item in radii):
        visual_direction.append("rounded-ui")
    if any("shadow" in item.lower() or "0 " in item for item in shadows):
        visual_direction.append("depth-layering")
    if uppercase_usage or letter_spacing_usage:
        visual_direction.append("editorial-typography")

    return {
        "colors": [item for item, _ in colors.most_common(10)],
        "fonts": [item for item, _ in fonts.most_common(6)],
        "css_vars": [item for item, _ in css_vars.most_common(12)],
        "shadows": [item for item, _ in shadows.most_common(6)],
        "radii": [item for item, _ in radii.most_common(6)],
        "tone_hints": [item for item, _ in tone_hints.most_common(8)],
        "visual_direction": visual_direction,
        "gradient_count": gradients,
        "blur_usage": blur_usage,
        "backdrop_usage": backdrop_usage,
    }
