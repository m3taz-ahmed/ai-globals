"""Persona detection from natural-language prompts for AI Global OS."""

from __future__ import annotations

from typing import Any, ClassVar, cast


class PersonaDetector:
    """Map user prompts to one of the nine AI Global OS personas.

    The detector uses weighted keyword matching.  Weights let narrow,
    high-signal domains (security, game, publishing) win against broad
    engineering vocabulary when the user explicitly mentions them.
    """

    PERSONAS: ClassVar[dict[str, dict[str, Any]]] = {
        "ARCH": {
            "name": "Principal 10x Engineer & Chief Architect",
            "weight": 1.0,
            "keywords": [
                "architecture",
                "scalability",
                "scalable",
                "system design",
                "microservices",
                "distributed",
                "ddd",
                "domain driven",
                "design pattern",
                "refactor",
                "schema",
                "data model",
                "event driven",
                "principal engineer",
                "chief architect",
                "platform",
            ],
        },
        "QA": {
            "name": "Software Tester",
            "weight": 1.2,
            "keywords": [
                "test",
                "tests",
                "testing",
                "coverage",
                "pytest",
                "unit test",
                "integration test",
                "e2e",
                "edge case",
                "regression",
                "qa",
                "quality assurance",
                "bug hunt",
                "fuzz",
                "tdd",
            ],
        },
        "UX": {
            "name": "Principal Full-Stack Designer & UX Architect",
            "weight": 1.1,
            "keywords": [
                "ui",
                "ux",
                "design",
                "user journey",
                "user experience",
                "prototype",
                "wireframe",
                "figma",
                "accessibility",
                "wcag",
                "pixel perfect",
                "frontend design",
                "animation",
                "interaction",
                "responsive",
            ],
        },
        "DEV": {
            "name": "Master Developer",
            "weight": 1.0,
            "keywords": [
                "backend",
                "api",
                "server",
                "database",
                "crud",
                "feature",
                "implement",
                "function",
                "endpoint",
                "service",
                "repository",
                "clean code",
                "performance",
                "optimize",
                "refactor code",
            ],
        },
        "SRE": {
            "name": "God-Tier SRE & Cloud Dictator",
            "weight": 1.2,
            "keywords": [
                "cloud",
                "aws",
                "gcp",
                "azure",
                "kubernetes",
                "k8s",
                "docker",
                "terraform",
                "deploy",
                "deployment",
                "ci/cd",
                "cicd",
                "observability",
                "monitoring",
                "logging",
                "chaos",
                "reliability",
                "sre",
                "devops",
                "infrastructure",
            ],
        },
        "SEC": {
            "name": "Hardcore Linux Kernel Master & SecOps Warlord",
            "weight": 1.3,
            "keywords": [
                "security",
                "secure",
                "vulnerability",
                "zero trust",
                "zerotrust",
                "auth",
                "authentication",
                "authorization",
                "ebpf",
                "linux",
                "kernel",
                "penetration",
                "pentest",
                "encryption",
                "audit",
                "firewall",
                "ids",
                "ips",
                "cve",
            ],
        },
        "GAME": {
            "name": "Principal Game Architect & JavaScript Engine Master",
            "weight": 1.3,
            "keywords": [
                "game",
                "game loop",
                "gameplay",
                "render",
                "rendering",
                "babylon",
                "babylon.js",
                "three.js",
                "unity",
                "unreal",
                "capacitor",
                "60 fps",
                "60fps",
                "frame drop",
                "webgl",
                "webgpu",
                "shader",
                "physics engine",
                "collision",
            ],
        },
        "PLAY": {
            "name": "Google Play Ecosystem Warlord & Android Publishing Expert",
            "weight": 1.3,
            "keywords": [
                "google play",
                "play console",
                "play store",
                "android publish",
                "publish app",
                "aab",
                "apk",
                "iap",
                "in app purchase",
                "aso",
                "anr",
                "crash",
                "target api",
                "targetsdk",
                "app bundle",
                "rollout",
            ],
        },
        "MOBILE": {
            "name": "Elite Mobile Game Producer & Full-Stack Innovator",
            "weight": 1.2,
            "keywords": [
                "mobile game",
                "mobile app",
                "fastlane",
                "anti cheat",
                "anticheat",
                "game state",
                "retention",
                "ltv",
                "lifetime value",
                "ios",
                "flutter",
                "react native",
                "push notification",
                "offline sync",
                "mobile",
            ],
        },
    }

    def __init__(self, default: str = "ARCH") -> None:
        if default not in self.PERSONAS:
            raise ValueError(f"Unknown default persona: {default}")
        self.default = default

    def detect(self, text: str) -> dict[str, Any]:
        """Return the best persona and a score distribution for *text*."""
        lowered = text.lower()
        scores: dict[str, float] = {}
        for key, info in self.PERSONAS.items():
            score = 0.0
            for kw in info["keywords"]:
                if kw.lower() in lowered:
                    score += info["weight"]
            scores[key] = round(score, 3)

        total = sum(scores.values()) or 1.0
        normalized = {k: round(v / total, 3) for k, v in scores.items()}
        best = max(scores, key=lambda k: scores[k])
        if scores[best] == 0:
            best = self.default

        return {
            "persona": best,
            "scores": normalized,
            "default": self.default,
        }

    def list_personas(self) -> list[str]:
        return list(self.PERSONAS.keys())


def detect_persona(text: str, default: str = "ARCH") -> str:
    """Convenience helper that returns only the persona code."""
    return cast(str, PersonaDetector(default).detect(text)["persona"])
