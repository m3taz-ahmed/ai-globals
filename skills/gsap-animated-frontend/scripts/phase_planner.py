"""Phased planning helpers for GSAP workflows."""

from __future__ import annotations


SECTION_RECIPES = {
    "Hero": "hero-text-reveal + layered media parallax",
    "Navigation": "navbar polish on scroll",
    "Feature Grid": "staggered card reveal + hover depth",
    "Stats": "count-up on enter",
    "Testimonials": "quote reveal + soft carousel polish",
    "Showcase": "parallax showcase or marquee",
    "Timeline": "step-by-step reveal",
    "FAQ": "accordion timing polish",
    "Pricing": "pricing-card emphasis + trust hierarchy",
    "Logos": "logo cloud drift + credibility polish",
    "Team": "profile stagger + soft hover depth",
    "Form": "field-focus polish + success transitions",
    "CTA": "cta emphasis + magnetic hover",
}


def default_sections_for_mode(mode: str):
    if mode == "gsap-refactor":
        return ["Audit Existing Motion", "Hero", "Feature Grid", "CTA"]
    return ["Hero", "Feature Grid", "Stats", "CTA"]


def build_phase_tasks(section: str, mode: str, discovery: dict):
    project_type = ", ".join(discovery.get("project_intelligence", {}).get("archetypes", [])) or "general product"
    base = [
        f"Inspect the current code and selectors for the {section} section before editing.",
        f"Align the {section} motion with the inferred product type: {project_type}.",
        f"Document the motion goal, hierarchy, and fallback behavior for {section} in the page artifact.",
        f"Implement the {section} animation with transform/opacity-first properties.",
        f"Verify reduced-motion behavior for {section}.",
        f"Verify mobile downgrade behavior for {section}.",
        f"Update the {section} status and notes in .gsap artifacts.",
    ]
    if mode == "gsap-refactor":
        base.insert(1, f"Preserve any good existing {section} motion and remove duplicate or noisy effects first.")
    return base


def build_phases(page: str, discovery: dict, mode: str):
    sections = discovery["page_structure"]["sections"] or default_sections_for_mode(mode)
    phases = []
    for index, section in enumerate(sections, start=1):
        phase_id = f"P{index:02d}"
        phases.append(
            {
                "id": phase_id,
                "page": page,
                "section": section,
                "recipe": SECTION_RECIPES.get(section, "section-specific reveal and polish"),
                "status": "Planned",
                "objective": f"Make the {section} section feel intentional, modern, and aligned with the page hierarchy.",
                "tasks": build_phase_tasks(section, mode, discovery),
            }
        )
    return phases
