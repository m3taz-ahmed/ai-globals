"""Higher-level project intelligence for GSAP workflows."""

from __future__ import annotations

from collections import Counter

ARCHETYPE_KEYWORDS = {
    "Marketing Site": ("hero", "cta", "testimonial", "pricing", "landing", "headline"),
    "Dashboard": ("dashboard", "chart", "table", "analytics", "metrics", "sidebar"),
    "Ecommerce": ("cart", "checkout", "product", "sku", "variant", "shop", "wishlist"),
    "Booking Platform": ("booking", "reservation", "calendar", "schedule", "availability"),
    "LMS / Education": ("course", "lesson", "student", "teacher", "school", "quiz"),
    "Portfolio": ("case study", "portfolio", "gallery", "project", "showcase"),
    "Docs / Knowledge Base": ("docs", "documentation", "guide", "faq", "sidebar", "search"),
    "SaaS App": ("workspace", "team", "subscription", "billing", "dashboard", "settings"),
    "Media / Content": ("article", "blog", "editorial", "video", "podcast", "story"),
    "Marketplace": ("vendor", "listing", "marketplace", "buyer", "seller"),
}

INFRA_PACKAGES = {
    "CMS": ("sanity", "contentful", "strapi", "payload", "hygraph", "prismic"),
    "Auth": ("next-auth", "clerk", "supabase", "auth0", "firebase"),
    "Payments": ("stripe", "paypal", "paddle"),
    "i18n": ("next-intl", "react-intl", "i18next", "next-i18next"),
    "State": ("zustand", "redux", "@tanstack/react-query", "jotai", "mobx"),
    "UI Kit": ("radix-ui", "@headlessui", "shadcn", "mantine", "chakra-ui", "mui"),
    "Testing": ("playwright", "cypress", "vitest", "jest"),
}


def infer_project_archetypes(discovery: dict):
    text_parts = []
    text_parts.extend(discovery["page_structure"]["sections"])
    text_parts.extend(discovery["page_structure"]["patterns"])
    text_parts.extend(discovery["design_tokens"]["tone_hints"])
    text_parts.extend(discovery["routes"])
    text_parts.extend(discovery["page_structure"]["selector_keywords"])
    haystack = " ".join(text_parts).lower()

    scores = Counter()
    for archetype, keywords in ARCHETYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in haystack:
                scores[archetype] += 1

    if discovery["page_structure"]["patterns"] and "Data visualization" in discovery["page_structure"]["patterns"]:
        scores["Dashboard"] += 2
    if "Pricing" in discovery["page_structure"]["sections"]:
        scores["Marketing Site"] += 1
        scores["SaaS App"] += 1
    if "Form" in discovery["page_structure"]["sections"] and "Calendar or booking flow" in discovery["page_structure"]["patterns"]:
        scores["Booking Platform"] += 2

    if not scores:
        return ["General Frontend Product"]
    return [name for name, _ in scores.most_common(3)]


def detect_infrastructure(packages: dict):
    findings = {}
    lower_names = {name.lower(): version for name, version in packages.items()}
    for label, package_names in INFRA_PACKAGES.items():
        matches = []
        for package_name in package_names:
            if any(package_name in name for name in lower_names):
                matches.extend(name for name in lower_names if package_name in name)
        if matches:
            findings[label] = sorted(set(matches))
    return findings


def infer_constraints(discovery: dict):
    constraints = []
    patterns = set(discovery["page_structure"]["patterns"])
    motion_stack = set(discovery["motion_stack"].keys())
    infra = detect_infrastructure(discovery["packages"])

    if "3D or canvas surface" in patterns or "Three.js" in motion_stack:
        constraints.append("3D surfaces need strong mobile fallbacks.")
    if "Data visualization" in patterns or "Dashboard" in infer_project_archetypes(discovery):
        constraints.append("Data-heavy screens need clarity-first motion and low distraction.")
    if "i18n" in infra:
        constraints.append("Text animation should tolerate locale-length changes.")
    if "Auth surface" in patterns or "Form" in discovery["page_structure"]["sections"]:
        constraints.append("Forms and auth flows need utility-first motion, not theatrical timing.")
    if "Ecommerce" in infer_project_archetypes(discovery):
        constraints.append("Conversion-critical surfaces should avoid motion that delays purchase actions.")
    if "Docs / Knowledge Base" in infer_project_archetypes(discovery):
        constraints.append("Documentation surfaces should prioritize readability over spectacle.")
    if not constraints:
        constraints.append("No major product-specific motion constraint inferred yet.")
    return constraints[:8]


def build_project_intelligence(discovery: dict):
    archetypes = infer_project_archetypes(discovery)
    infrastructure = detect_infrastructure(discovery["packages"])
    constraints = infer_constraints(discovery)
    return {
        "archetypes": archetypes,
        "infrastructure": infrastructure,
        "constraints": constraints,
    }
