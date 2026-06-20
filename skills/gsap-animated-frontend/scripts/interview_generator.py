"""Interview question generation helpers for GSAP workflows."""

from __future__ import annotations


def build_interview_questions(discovery: dict, mode: str):
    page_structure = discovery["page_structure"]
    motion_stack = discovery["motion_stack"]
    design_tokens = discovery["design_tokens"]
    packages = discovery["packages"]
    questions = []

    if not page_structure["sections"]:
        questions.append("Which page sections should carry the strongest motion hierarchy first?")
    if "GSAP" not in motion_stack and "gsap" not in packages:
        questions.append("Should the workflow install GSAP now, or only prepare the spec and phased plan?")
    if "Lenis" not in motion_stack and "lenis" not in packages:
        questions.append("Do you want smooth scrolling like Lenis, or should native scrolling stay untouched?")
    if not design_tokens["colors"]:
        questions.append("What brand colors, references, or websites should the motion language visually respect?")
    if not design_tokens["fonts"]:
        questions.append("Should the motion feel editorial, product-polished, playful, cinematic, or ultra-minimal?")
    if "Feature Grid" in page_structure["sections"]:
        questions.append("Should repeated cards share one reveal system, or should featured cards feel more premium than the rest?")
    if "Hero" in page_structure["sections"]:
        questions.append("Should the hero motion feel premium and cinematic, or quiet and product-focused?")
    if "Pricing" in page_structure["sections"]:
        questions.append("Should pricing cards feel calm and trustworthy, or more high-conversion and attention-grabbing?")
    if "Logos" in page_structure["sections"]:
        questions.append("Should partner or client logos stay subtle, or should they get motion emphasis as social proof?")
    if "Form" in page_structure["sections"]:
        questions.append("Should forms use only subtle focus polish, or do you want stronger field and success-state motion?")
    if "Data visualization" in page_structure["patterns"]:
        questions.append("Should charts and metrics animate softly for readability, or should they feel more dramatic and presentational?")
    if "Sidebar or drawer" in page_structure["patterns"]:
        questions.append("Do sidebars and drawers need utility-first motion, or should they feel more premium and layered?")
    if "3D or canvas surface" in page_structure["patterns"]:
        questions.append("Should 3D moments be decorative only, or are they core to the story and worth heavier engineering?")
    if mode == "gsap-refactor" and "GSAP" not in motion_stack:
        questions.append("This page does not appear to use GSAP yet. Should the refactor introduce GSAP or stay within the current motion stack?")
    if mode == "gsap-refactor":
        questions.append("Which current motion feels worst right now: too static, too noisy, too slow, too generic, or too inconsistent?")

    deduped = []
    for item in questions:
        if item not in deduped:
            deduped.append(item)
    return deduped[:8]


def build_recommendations(discovery: dict, mode: str):
    page_structure = discovery["page_structure"]
    recommendations = []

    if "Hero" in page_structure["sections"]:
        recommendations.append("Use a staged hero reveal with headline, supporting copy, and CTA arriving in deliberate sequence.")
    if "Feature Grid" in page_structure["sections"]:
        recommendations.append("Use one card system for the grid and keep the stagger controlled so the section feels premium, not noisy.")
    if "Stats" in page_structure["sections"]:
        recommendations.append("Use count-up animation only when the stats enter view and only once.")
    if "Navigation" in page_structure["sections"]:
        recommendations.append("Consider a subtle navbar polish on scroll rather than a dramatic transformation.")
    if "Pricing" in page_structure["sections"]:
        recommendations.append("Use restrained pricing-card emphasis so the CTA hierarchy stays clear without making the section feel gimmicky.")
    if "Logos" in page_structure["sections"]:
        recommendations.append("Keep logo motion understated and credibility-focused rather than attention-seeking.")
    if "Form" in page_structure["sections"]:
        recommendations.append("Use state-based form polish like focus, validation, and success transitions instead of theatrical entrance effects.")
    if "Showcase" in page_structure["sections"]:
        recommendations.append("Reserve marquee, parallax, or layered depth for a showcase section instead of distributing spectacle everywhere.")
    if "Data visualization" in page_structure["patterns"]:
        recommendations.append("Animate charts and dashboards for clarity first, spectacle second.")
    if "Search and filtering" in page_structure["patterns"]:
        recommendations.append("Use fast, low-friction transitions for search and filter changes so the UI stays responsive.")
    if "3D or canvas surface" in page_structure["patterns"]:
        recommendations.append("Keep 3D and depth moments focused to one section with strong mobile fallbacks.")

    recommendations.append("Define reduced-motion and mobile downgrade rules before implementation starts.")
    if mode == "gsap-refactor":
        recommendations.append("Preserve any strong existing motion patterns and remove duplication before adding new ones.")
    else:
        recommendations.append("Build section phases from strongest story beat to weakest so the page gains hierarchy, not just effects.")

    deduped = []
    for item in recommendations:
        if item not in deduped:
            deduped.append(item)
    return deduped[:10]
