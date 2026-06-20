"""Interview strategy and decision-priority helpers."""

from __future__ import annotations


def classify_question(question: str) -> str:
    lower = question.lower()
    if any(token in lower for token in ("brand", "visual", "editorial", "cinematic", "premium")):
        return "Creative Direction"
    if any(token in lower for token in ("gsap", "stack", "introduce", "install")):
        return "Technical Stack"
    if any(token in lower for token in ("mobile", "reduced", "fallback", "performance")):
        return "Performance And Accessibility"
    if any(token in lower for token in ("hero", "pricing", "cards", "charts", "logos", "form")):
        return "Section Behavior"
    return "Workflow Clarification"


def prioritize_questions(questions: list[str], discovery: dict, mode: str):
    page_structure = discovery["page_structure"]
    patterns = set(page_structure["patterns"])
    ranked = []

    for question in questions:
        score = 0
        lower = question.lower()
        if "hero" in lower and "Hero" in page_structure["sections"]:
            score += 4
        if "gsap" in lower and "GSAP" not in discovery["motion_stack"]:
            score += 5
        if "brand" in lower and not discovery["design_tokens"]["colors"]:
            score += 4
        if "3d" in lower and "3D or canvas surface" in patterns:
            score += 5
        if "charts" in lower and "Data visualization" in patterns:
            score += 4
        if "mobile" in lower or "reduced" in lower:
            score += 3
        if mode == "gsap-refactor" and "wrong" in lower:
            score += 4
        ranked.append((score, question))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [question for _, question in ranked]


def build_interview_brief(questions: list[str], discovery: dict, mode: str):
    prioritized = prioritize_questions(questions, discovery, mode)
    categories = []
    seen = set()
    for question in prioritized:
        category = classify_question(question)
        if category not in seen:
            seen.add(category)
            categories.append(category)

    return {
        "priority_questions": prioritized[:6],
        "categories": categories[:5],
        "interview_mode": "short-gap-fill" if len(prioritized) <= 3 else "targeted-discovery",
    }
