"""Persona detection and skill composition for AI Global OS."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any, ClassVar, cast

from runtime.skill_resolver import SkillResolver


class PersonaDetector:
    """Map user prompts to one or more AI Global OS personas and related skills.

    The detector uses weighted keyword matching for personas and a separate
    keyword index for domain ("lord") skills. Results compose a primary persona,
    a ranked list of personas, and a list of skill names that should be loaded.
    """

    DEFAULT: ClassVar[str] = "ARCH"
    PERSONA_LORD_BONUS: ClassVar[float] = 0.5

    PERSONAS: ClassVar[dict[str, dict[str, Any]]] = {
        "ARCH": {
            "name": "Principal 10x Engineer & Chief Architect",
            "weight": 1.0,
            "skill": "ai-agents-architect",
            "lords": ["subagent-driven-development"],
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
            "skill": "qa-debugger",
            "lords": ["test-driven-development", "test-guard"],
            "keywords": [
                "test",
                "tests",
                "testing",
                "coverage",
                "pytest",
                "unit test",
                "unit tests",
                "unit testing",
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
            "skill": "frontend-ui-expert",
            "lords": ["frontend-frameworks-lord", "gsap-animated-frontend", "page-sections-lord"],
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
                "landing page",
                "page builder",
                "page sections",
                "content page",
                "hero section",
                "builder",
            ],
        },
        "DEV": {
            "name": "Master Developer",
            "weight": 1.0,
            "skill": "backend-api-expert",
            "lords": ["clean-code-guard", "language-lord", "page-sections-lord"],
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
                "page builder",
                "landing page",
                "page sections",
                "filament builder",
                "content page",
                "hero section",
                "builder",
            ],
        },
        "SRE": {
            "name": "God-Tier SRE & Cloud Dictator",
            "weight": 1.2,
            "skill": "sre",
            "lords": ["cloud-platforms-lord", "devops-lord", "linux-systems-lord"],
            "keywords": [
                "cloud",
                "aws",
                "gcp",
                "azure",
                "kubernetes",
                "k8s",
                "docker",
                "terraform",
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
            "skill": "security-auditor",
            "lords": ["security-lord", "linux-systems-lord"],
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
            "skill": "game-architect",
            "lords": [],
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
            "skill": "google-play-warlord",
            "lords": [],
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
            "skill": "mobile-game-producer",
            "lords": ["game-architect"],
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
        "DATA": {
            "name": "Data Engineer & DBA",
            "weight": 1.2,
            "skill": "data-engineer",
            "lords": ["database-lord", "mariadb-lord"],
            "keywords": [
                "data",
                "database",
                "sql",
                "etl",
                "analytics",
                "data pipeline",
                "data warehouse",
                "big data",
                "spark",
                "airflow",
                "data modeling",
                "data migration",
                "data quality",
                "query optimization",
                "mariadb",
                "galera",
                "schema",
                "migration",
                "backup",
                "replication",
                "indexing",
                "db",
            ],
        },
        "ML": {
            "name": "Machine Learning Engineer",
            "weight": 1.3,
            "skill": "ml-engineer",
            "lords": ["ai-ml-lord", "search-vector-lord"],
            "keywords": [
                "machine learning",
                "ml",
                "model",
                "training",
                "inference",
                "tensorflow",
                "pytorch",
                "scikit-learn",
                "neural network",
                "deep learning",
                "llm",
                "openai",
                "anthropic",
                "onnx",
                "model deployment",
                "mlops",
                "fine tuning",
                "embedding",
                "vector",
                "classification",
                "regression",
            ],
        },
        "DEVOPS": {
            "name": "DevOps & CI/CD Engineer",
            "weight": 1.2,
            "skill": "devops-engineer",
            "lords": ["devops-lord", "cloud-platforms-lord", "linux-systems-lord"],
            "keywords": [
                "devops",
                "cicd",
                "ci/cd",
                "pipeline",
                "jenkins",
                "github actions",
                "gitlab ci",
                "automation",
                "docker registry",
                "artifact management",
                "deployment",
                "release",
                "infrastructure as code",
                "iac",
                "terraform",
                "ansible",
            ],
        },
        "API": {
            "name": "API Architect & Integration Specialist",
            "weight": 1.1,
            "skill": "api-architect",
            "lords": ["backend-frameworks-lord", "security-lord"],
            "keywords": [
                "api",
                "rest",
                "graphql",
                "microservices",
                "integration",
                "api gateway",
                "swagger",
                "openapi",
                "api documentation",
                "rate limiting",
                "api versioning",
                "webhook",
                "endpoint",
            ],
        },
        "LEGAL": {
            "name": "Legal & Compliance Officer",
            "weight": 1.3,
            "skill": "legal-compliance",
            "lords": [],
            "keywords": [
                "gdpr",
                "compliance",
                "privacy",
                "legal",
                "data protection",
                "regulatory",
                "audit",
                "terms of service",
                "privacy policy",
                "cookie consent",
                "data retention",
                "license",
                "coppa",
                "hipaa",
                "soc2",
            ],
        },
        "PRODUCT": {
            "name": "Product Manager",
            "weight": 1.1,
            "skill": "product-manager",
            "lords": [],
            "keywords": [
                "requirements",
                "user story",
                "roadmap",
                "product",
                "user research",
                "product backlog",
                "feature prioritization",
                "product strategy",
                "market analysis",
                "user feedback",
                "mvp",
                "prd",
            ],
        },
        "DOC": {
            "name": "Technical Writer & Documentation Lead",
            "weight": 1.0,
            "skill": "technical-writer",
            "lords": ["docs-guard"],
            "keywords": [
                "documentation",
                "readme",
                "api docs",
                "changelog",
                "technical writing",
                "docs",
                "wiki",
                "guide",
                "tutorial",
                "how-to",
            ],
        },
        "PERF": {
            "name": "Performance Engineer",
            "weight": 1.1,
            "skill": "performance-engineer",
            "lords": ["fullstack-optimizer", "database-lord", "mariadb-lord", "language-lord"],
            "keywords": [
                "performance",
                "profiling",
                "latency",
                "benchmark",
                "optimization",
                "throughput",
                "memory leak",
                "cpu",
                "bottleneck",
                "load test",
                "stress test",
                "caching",
                "query optimization",
            ],
        },
    }

    PERSONA_SKILLS: ClassVar[dict[str, str]] = {
        code: info["skill"] for code, info in PERSONAS.items()
    }

    LORD_SKILLS: ClassVar[dict[str, list[str]]] = {
        "database-lord": [
            "database", "sql", "postgres", "mysql", "mongodb", "redis", "sqlite",
            "query", "schema", "migration", "index", "replication", "sharding",
            "backup", "transaction", "wal", "mvcc", "lsm", "btree", "normalize",
        ],
        "ai-ml-lord": [
            "machine learning", "ml", "model", "training", "inference", "pytorch",
            "tensorflow", "scikit-learn", "neural network", "deep learning", "llm",
            "openai", "anthropic", "onnx", "fine tuning", "embedding", "vector",
            "classification", "regression", "clustering", "transformer",
        ],
        "devops-lord": [
            "docker", "kubernetes", "k8s", "terraform", "ansible", "cicd", "ci/cd",
            "pipeline", "deploy", "helm", "gitops", "podman", "container",
            "registry", "artifact", "github actions", "gitlab ci",
        ],
        "cloud-platforms-lord": [
            "aws", "azure", "gcp", "cloud", "serverless", "lambda", "ec2", "s3",
            "cloudfront", "gke", "aks", "ecs", "vpc", "iam", "landing zone",
            "multi cloud", "hybrid cloud",
        ],
        "frontend-frameworks-lord": [
            "react", "vue", "angular", "svelte", "frontend framework", "component",
            "hooks", "signals", "routing", "csr", "ssr", "ssg", "islands",
        ],
        "backend-frameworks-lord": [
            "laravel", "django", "spring", "spring boot", "express", "nestjs",
            "rails", "asp.net", "backend framework", "orm", "middleware", "auth",
        ],
        "language-lord": [
            "python", "javascript", "typescript", "java", "c#", "c++", "go", "golang",
            "rust", "php", "ruby", "language design", "runtime", "compiler",
            "garbage collector", "memory model",
        ],
        "linux-systems-lord": [
            "linux", "kernel", "systemd", "ebpf", "ubuntu", "debian", "syscall",
            "file system", "network namespace", "cgroup", "selinux", "sysctl",
        ],
        "messaging-streaming-lord": [
            "kafka", "rabbitmq", "nats", "redis streams", "event-driven", "pub sub",
            "streaming", "message broker", "queue", "topic", "partition",
        ],
        "search-vector-lord": [
            "elasticsearch", "opensearch", "meilisearch", "vector search", "pinecone",
            "milvus", "rag", "vector db", "embedding search", "hybrid search",
        ],
        "security-lord": [
            "owasp", "vulnerability", "pentest", "penetration", "encryption", "xss",
            "sql injection", "csrf", "auth", "zero trust", "firewall", "cve",
            "secure", "sanitize",
        ],
        "fullstack-optimizer": [
            "performance", "bundle", "caching", "i18n", "localization", "optimization",
            "fullstack", "cdn", "compression", "lazy load", "preload",
        ],
        "clean-code-guard": [
            "clean code", "refactor", "solid", "dry", "kiss", "code smell",
            "technical debt", "readability", "maintainability",
        ],
        "test-guard": [
            "test", "unit test", "integration test", "coverage", "tdd", "mock",
            "fixture", "assertion", "regression test",
        ],
        "frontend-ui-expert": [
            "tailwind", "design system", "ui", "ux", "figma", "component library",
            "accessibility", "wcag", "responsive", "icon",
        ],
        "gsap-animated-frontend": [
            "gsap", "animation", "motion", "scroll trigger", "timeline", "easing",
        ],
        "docs-guard": [
            "documentation", "readme", "docs", "api docs", "changelog", "wiki",
        ],
    }

    def __init__(self, default: str = DEFAULT, skill_resolver: SkillResolver | None = None) -> None:
        if default not in self.PERSONAS:
            raise ValueError(f"Unknown default persona: {default}")
        self.default = default
        self.skill_resolver = skill_resolver or SkillResolver()

    def list_personas(self) -> list[str]:
        """Return all defined persona codes."""
        return list(self.PERSONAS.keys())

    def list_lord_skills(self) -> list[str]:
        """Return all known lord skill names."""
        return list(self.LORD_SKILLS.keys())

    def skill_for(self, persona: str) -> str:
        """Primary skill name for a persona code."""
        return cast(str, self.PERSONAS.get(persona, self.PERSONAS[self.default])["skill"])

    def _keyword_match(self, text: str, keyword: str) -> bool:
        """Match a keyword as a whole word/phrase to avoid substring false positives."""
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _score_personas(self, text: str) -> dict[str, float]:
        scores: dict[str, float] = {}
        for code, info in self.PERSONAS.items():
            score = 0.0
            for kw in info["keywords"]:
                if self._keyword_match(text, kw):
                    score += info["weight"]
            scores[code] = round(score, 3)
        return scores

    def _lord_matches(self, text: str, skill: str) -> int:
        """Count how many of a lord skill's keywords appear in the prompt."""
        return sum(1 for kw in self.LORD_SKILLS.get(skill, []) if self._keyword_match(text, kw))

    def _detect_lords(self, text: str) -> list[str]:
        """Return lord skills whose keywords appear in the prompt."""
        matched: set[str] = set()
        for skill in self.LORD_SKILLS:
            if self._lord_matches(text, skill):
                matched.add(skill)
        return sorted(matched)

    def detect_multiple(
        self,
        text: str,
        max_personas: int = 3,
        max_lords: int = 5,
        include_lords: bool = True,
    ) -> dict[str, Any]:
        """Detect the top N personas and the skill set they compose.

        The returned dict contains:
        - persona: primary persona code
        - personas: ranked list of selected persona codes
        - skill: primary skill name
        - skills: primary skill names for selected personas
        - lords: additional domain skills triggered by the prompt or persona
        - scores: normalized score distribution across all personas
        - default: the default persona code
        """
        scores = self._score_personas(text)
        sorted_personas = sorted(scores, key=lambda k: scores[k], reverse=True)
        selected = [p for p in sorted_personas if scores[p] > 0][:max_personas]
        if not selected:
            selected = [self.default]

        primary = selected[0]
        primary_skills: list[str] = []
        seen_skills: set[str] = set()
        for p in selected:
            sk = self.skill_for(p)
            if sk not in seen_skills:
                seen_skills.add(sk)
                primary_skills.append(sk)

        lord_scores: dict[str, float] = {}
        if include_lords:
            for p in selected:
                for lord in self.PERSONAS[p].get("lords", []):
                    lord_scores[lord] = lord_scores.get(lord, 0.0) + self.PERSONA_LORD_BONUS
            for skill in self.LORD_SKILLS:
                matches = self._lord_matches(text, skill)
                if matches:
                    lord_scores[skill] = lord_scores.get(skill, 0.0) + matches

        # Lords that duplicate a primary skill are promoted to primary skill list.
        ranked_lords = sorted(
            ((lord, score) for lord, score in lord_scores.items() if lord not in seen_skills),
            key=lambda x: (-x[1], x[0]),
        )
        lords = [lord for lord, _ in ranked_lords[:max_lords]]

        total = sum(scores.values()) or 1.0
        normalized = {k: round(v / total, 3) for k, v in scores.items()}

        return {
            "persona": primary,
            "personas": selected,
            "skill": primary_skills[0] if primary_skills else self.skill_for(self.default),
            "skills": primary_skills,
            "lords": lords,
            "scores": normalized,
            "default": self.default,
        }

    def detect(self, text: str) -> dict[str, Any]:
        """Backwards-compatible single-persona detection."""
        result = self.detect_multiple(text, max_personas=1, include_lords=False)
        return {
            "persona": result["persona"],
            "skill": result["skill"],
            "scores": result["scores"],
            "default": result["default"],
        }

    def resolve_skills(
        self,
        personas: Iterable[str],
        lords: Iterable[str] | None = None,
    ) -> list[str]:
        """Return unique, existing skill names for the given personas and lords."""
        names: list[str] = [self.skill_for(p) for p in personas]
        if lords:
            names.extend(lords)
        seen: set[str] = set()
        valid: list[str] = []
        for name in names:
            if name in seen or not self.skill_resolver.exists(name):
                continue
            seen.add(name)
            valid.append(name)
        return valid


def detect_persona(text: str, default: str = "ARCH") -> str:
    """Convenience helper that returns only the persona code."""
    return cast(str, PersonaDetector(default).detect(text)["persona"])
