#!/usr/bin/env python3
"""Comprehensive prompt-injection detector covering all 13 attack techniques.

This module implements detection for the full prompt-injection attack taxonomy
documented in OWASP LLM01, Sysdig 2026, and Wraith 2026:

1.  Direct instruction override
2.  System prompt extraction
3.  Role-play / persona jailbreak
4.  Multi-turn context manipulation (single-turn markers)
5.  Encoding / obfuscation (Base64, Hex, URL-encode, Unicode)
6.  Typoglycemia (scrambled-word) attacks
7.  Best-of-N (BoN) variation detection
8.  HTML / Markdown injection (exfiltration markup)
9.  Multimodal injection markers (steganography hints, metadata)
10. RAG poisoning markers
11. Tool abuse (path traversal, SSRF, command injection)
12. Thought / observation injection (forged reasoning steps)
13. Memory poisoning markers

Additionally provides:
- Encoding-aware scanning (decode Base64/Hex/URL then re-scan)
- Multilingual patterns (Arabic, plus generic Unicode normalization)
- Per-technique scoring with a unified ``InjectionVerdict``

The detector is deterministic and model-free by default. An optional
``model_fn`` can be injected for semantic (Stage 2) analysis — see
:mod:`runtime.prompt_injection_detector`.

Usage::

    from runtime.injection_detector import InjectionDetector, InjectionVerdict

    detector = InjectionDetector()
    verdict = detector.detect("ignore all previous instructions and ...")
    if verdict.is_injection:
        raise PolicyDeniedError(verdict.reason)
"""

from __future__ import annotations

import base64
import binascii
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from runtime.schemas import AizeeError, ErrorSeverity, GateVerdict

# ---------------------------------------------------------------------------
# Enums and dataclasses
# ---------------------------------------------------------------------------


class InjectionTechnique(str, Enum):
    """The 13 documented prompt-injection attack techniques."""

    DIRECT_OVERRIDE = "direct_override"
    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    ROLEPLAY_JAILBREAK = "roleplay_jailbreak"
    MULTI_TURN_MANIPULATION = "multi_turn_manipulation"
    ENCODING_OBFUSCATION = "encoding_obfuscation"
    TYPOGLYCEMIA = "typoglycemia"
    BEST_OF_N = "best_of_n"
    HTML_MARKDOWN_INJECTION = "html_markdown_injection"
    MULTIMODAL_INJECTION = "multimodal_injection"
    RAG_POISONING = "rag_poisoning"
    TOOL_ABUSE = "tool_abuse"
    THOUGHT_INJECTION = "thought_injection"
    MEMORY_POISONING = "memory_poisoning"


class InjectionSeverity(str, Enum):
    """Severity of a detected injection technique."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class InjectionSignal:
    """A single detected injection signal."""

    technique: InjectionTechnique
    severity: InjectionSeverity
    pattern_id: str
    match: str
    score: int

    def to_dict(self) -> dict[str, str | int]:
        return {
            "technique": self.technique.value,
            "severity": self.severity.value,
            "pattern_id": self.pattern_id,
            "match": self.match[:200],  # truncate for logging
            "score": self.score,
        }


@dataclass
class InjectionVerdict:
    """Aggregated verdict from scanning a text for all 13 techniques."""

    text: str
    signals: list[InjectionSignal] = field(default_factory=list)
    total_score: int = 0
    techniques_found: set[InjectionTechnique] = field(default_factory=set)

    @property
    def is_injection(self) -> bool:
        # BLOCK requires threshold AND at least one MEDIUM+ signal —
        # two LOWs alone (6+6=12) stay SUSPICIOUS, not BLOCK.
        if self.total_score < InjectionDetector.BLOCK_THRESHOLD:
            return False
        order = {
            InjectionSeverity.LOW: 1,
            InjectionSeverity.MEDIUM: 2,
            InjectionSeverity.HIGH: 3,
            InjectionSeverity.CRITICAL: 4,
        }
        return any(order.get(s.severity, 0) >= 2 for s in self.signals)

    @property
    def is_suspicious(self) -> bool:
        return InjectionDetector.SUSPICIOUS_THRESHOLD <= self.total_score < InjectionDetector.BLOCK_THRESHOLD

    @property
    def highest_severity(self) -> InjectionSeverity | None:
        if not self.signals:
            return None
        order = {
            InjectionSeverity.CRITICAL: 4,
            InjectionSeverity.HIGH: 3,
            InjectionSeverity.MEDIUM: 2,
            InjectionSeverity.LOW: 1,
        }
        return max(self.signals, key=lambda s: order[s.severity]).severity

    def to_gate_verdict(self) -> GateVerdict:
        if self.is_injection:
            return GateVerdict.block(
                "injection_detector",
                self.reason,
                score=self.total_score,
                techniques=[t.value for t in self.techniques_found],
                signals=[s.to_dict() for s in self.signals],
            )
        if self.is_suspicious:
            return GateVerdict.require_approval(
                "injection_detector",
                self.reason,
                score=self.total_score,
                techniques=[t.value for t in self.techniques_found],
            )
        return GateVerdict.allow(
            "injection_detector",
            "no injection detected",
            score=self.total_score,
        )

    @property
    def reason(self) -> str:
        if not self.signals:
            return "no injection detected"
        techs = ", ".join(sorted(t.value for t in self.techniques_found))
        return f"injection detected: {techs} (score {self.total_score})"

    def to_dict(self) -> dict[str, object]:
        return {
            "is_injection": self.is_injection,
            "is_suspicious": self.is_suspicious,
            "total_score": self.total_score,
            "techniques_found": sorted(t.value for t in self.techniques_found),
            "highest_severity": self.highest_severity.value if self.highest_severity else None,
            "signals": [s.to_dict() for s in self.signals],
            "reason": self.reason,
        }


class InjectionDetectorError(AizeeError):
    """Raised when the injection detector encounters an internal error."""

    def __init__(self, message: str, context: dict[str, object] | None = None) -> None:
        super().__init__("INJECTION_DETECTOR_ERROR", message, ErrorSeverity.HIGH, context)


# ---------------------------------------------------------------------------
# Pattern database — 13 techniques
# ---------------------------------------------------------------------------


def _sev_score(sev: InjectionSeverity) -> int:
    return {
        InjectionSeverity.CRITICAL: 50,
        InjectionSeverity.HIGH: 25,
        InjectionSeverity.MEDIUM: 12,
        InjectionSeverity.LOW: 6,
    }[sev]


@dataclass
class _Pattern:
    pid: str
    technique: InjectionTechnique
    severity: InjectionSeverity
    regex: re.Pattern[str]
    message: str

    @property
    def score(self) -> int:
        return _sev_score(self.severity)


def _build_patterns() -> list[_Pattern]:
    patterns: list[_Pattern] = []
    flags = re.IGNORECASE | re.MULTILINE

    def add(
        pid: str, tech: InjectionTechnique, sev: InjectionSeverity, rx: str, msg: str
    ) -> None:
        patterns.append(_Pattern(pid, tech, sev, re.compile(rx, flags), msg))

    # 1. Direct instruction override (D1-D6)
    add("D1", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.CRITICAL,
        r"ignore\s+(?:all\s+|the\s+|your\s+|any\s+)?(?:previous|prior|above|preceding)\s+"
        r"(?:instructions|prompts|context|messages|rules)", "Direct override: ignore previous instructions")
    add("D2", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.CRITICAL,
        r"disregard\s+(?:your\s+|the\s+|all\s+)?(?:system\s+prompt|instructions|previous|prior|above|rules)",
        "Direct override: disregard instructions")
    add("D3", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.HIGH,
        r"forget\s+(?:your\s+|all\s+|the\s+)?(?:instructions|everything|previous|prompt|rules)",
        "Direct override: memory wipe")
    add("D4", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.HIGH,
        r"override\s+(?:safety|security|content\s+policy|guardrails|your\s+rules)",
        "Direct override: override safety")
    add("D5", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.HIGH,
        r"new\s+instructions?\s*:", "Direct override: new instructions header")
    add("D6", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.MEDIUM,
        r"your\s+(?:real|true|actual)\s+(?:instructions|rules)\s+are", "Direct override: fake authority claim")
    add("D7", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.HIGH,
        r"ignore\s+(?:the\s+|all\s+|your\s+)?(?:safety\s+rules|safety\s+filters|safety\s+guidelines|content\s+policy|guardrails|security\s+rules)",
        "Direct override: ignore safety rules")
    # M7: concatenated variants (no whitespace) bypass whitespace-dependent
    # patterns. ``ignoreallpreviousinstructions`` etc. are common obfuscations.
    add("D8", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.CRITICAL,
        r"ignore(?:all|the|your|any)?(?:previous|prior|above|preceding)(?:instructions|prompts|context|messages|rules)",
        "Direct override: concatenated ignore-previous")
    add("D9", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.HIGH,
        r"forget(?:your|all|the)?(?:instructions|everything|previous|prompt|rules)",
        "Direct override: concatenated memory wipe")
    add("D10", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.HIGH,
        r"override(?:safety|security|contentpolicy|guardrails|yourrules)",
        "Direct override: concatenated override")

    # 2. System prompt extraction (S1-S5)
    add("S1", InjectionTechnique.SYSTEM_PROMPT_EXTRACTION, InjectionSeverity.HIGH,
        r"reveal\s+(?:me\s+)?(?:your\s+|the\s+)?(?:system\s+prompt|instructions|prompt|rules|guidelines)",
        "System prompt extraction: reveal request")
    add("S2", InjectionTechnique.SYSTEM_PROMPT_EXTRACTION, InjectionSeverity.HIGH,
        r"(?:print|show|display|output)\s+(?:me\s+)?(?:your\s+|the\s+)?(?:system\s+prompt|instructions|hidden)",
        "System prompt extraction: print request")
    add("S3", InjectionTechnique.SYSTEM_PROMPT_EXTRACTION, InjectionSeverity.HIGH,
        r"what\s+(?:are|is|were)\s+your\s+(?:exact\s+|actual\s+)?(?:system\s+)?(?:prompt|instructions|rules|guidelines)",
        "System prompt extraction: probing question")
    add("S4", InjectionTechnique.SYSTEM_PROMPT_EXTRACTION, InjectionSeverity.HIGH,
        r"repeat\s+(?:the\s+text\s+)?above\s+(?:starting\s+with|from)\s+['\"]?(?:you\s+are|system|your)",
        "System prompt extraction: completion trick")
    add("S5", InjectionTechnique.SYSTEM_PROMPT_EXTRACTION, InjectionSeverity.LOW,
        r"translate\s+(?:your\s+)?(?:first\s+)?message\s+(?:into|to)\s+\w+", "System prompt extraction: translation trick")

    # 3. Role-play / persona jailbreak (R1-R5)
    add("R1", InjectionTechnique.ROLEPLAY_JAILBREAK, InjectionSeverity.HIGH,
        r"(?:act|pretend|roleplay)\s+as\s+(?:if\s+you\s+(?:have\s+)?no\s+|without\s+)(?:rules|restrictions|guardrails|limits)",
        "Roleplay jailbreak: no restrictions")
    add("R2", InjectionTechnique.ROLEPLAY_JAILBREAK, InjectionSeverity.HIGH,
        r"you\s+are\s+now\s+(?:free|unrestricted|jailbroken|liberated|an?\s+\w+\s+without\s+rules)",
        "Roleplay jailbreak: identity override")
    add("R3", InjectionTechnique.ROLEPLAY_JAILBREAK, InjectionSeverity.MEDIUM,
        r"\b[Dd][Aa][Nn]\b(?:\s+mode)?|do\s+anything\s+now", "Roleplay jailbreak: DAN persona")
    add("R4", InjectionTechnique.ROLEPLAY_JAILBREAK, InjectionSeverity.MEDIUM,
        r"developer\s+mode|dev\s+mode|god\s+mode|admin\s+mode", "Roleplay jailbreak: fake mode")
    add("R5", InjectionTechnique.ROLEPLAY_JAILBREAK, InjectionSeverity.LOW,
        r"let'?s\s+roleplay|write\s+a\s+story\s+where\s+(?:an?\s+)?(?:ai|assistant)\s+(?:helps|can)",
        "Roleplay jailbreak: fictional framing")

    # 4. Multi-turn manipulation markers (M1-M3) — single-turn detectable markers
    add("M1", InjectionTechnique.MULTI_TURN_MANIPULATION, InjectionSeverity.MEDIUM,
        r"(?:actually|wait|sorry,\s+i\s+meant|let\s+me\s+clarify|on\s+second\s+thought).{0,40}"
        r"(?:ignore|disregard|override|bypass|forget)", "Multi-turn: clarification-into-override")
    add("M2", InjectionTechnique.MULTI_TURN_MANIPULATION, InjectionSeverity.LOW,
        r"remember\s+(?:that\s+)?(?:you\s+)?(?:are\s+now|have\s+no|can\s+do\s+anything)",
        "Multi-turn: false memory implant")
    add("M3", InjectionTechnique.MULTI_TURN_MANIPULATION, InjectionSeverity.MEDIUM,
        r"as\s+we\s+(?:discussed|agreed|established)\s+(?:earlier|before),?\s+you\s+(?:can|should|must)",
        "Multi-turn: fake prior agreement")

    # 5. Encoding / obfuscation (E1-E4) — markers that encoding is being used
    add("E1", InjectionTechnique.ENCODING_OBFUSCATION, InjectionSeverity.HIGH,
        r"(?:decode|execute|run|eval)\s+(?:this\s+)?(?:base64|b64|hex|rot13|binary|morse)[:\s]",
        "Encoding obfuscation: decode instruction")
    add("E2", InjectionTechnique.ENCODING_OBFUSCATION, InjectionSeverity.MEDIUM,
        r"(?:\\x[0-9a-f]{2}){2,}", "Encoding obfuscation: hex escape sequence (2+)")
    add("E3", InjectionTechnique.ENCODING_OBFUSCATION, InjectionSeverity.MEDIUM,
        r"(?:\\u[0-9a-f]{4}){2,}", "Encoding obfuscation: unicode escape (2+)")
    add("E4", InjectionTechnique.ENCODING_OBFUSCATION, InjectionSeverity.LOW,
        r"(?:rot13|caesar\s+cipher|atbash)", "Encoding obfuscation: cipher reference")

    # 6. Typoglycemia (T1-T2) — scrambled dangerous words
    # We detect scrambled variants of "ignore", "instructions", "system", "override"
    add("T1", InjectionTechnique.TYPOGLYCEMIA, InjectionSeverity.MEDIUM,
        r"\bignroe\b|\bignoer\b|\bign0re\b|\bignor3\b|\bijnore\b|\bigno3\b",
        "Typoglycemia: scrambled 'ignore'")
    add("T2", InjectionTechnique.TYPOGLYCEMIA, InjectionSeverity.MEDIUM,
        r"\b(?:instructinos|instrutcions|insturctions|instrcutiosn|instruuctons)\b",
        "Typoglycemia: scrambled 'instructions'")
    add("T3", InjectionTechnique.TYPOGLYCEMIA, InjectionSeverity.MEDIUM,
        r"\b(?:del[te]{1,3}|d[el]l[te]e|delet[ed])\s+(?:all|every|the)\s+\w+",
        "Typoglycemia: scrambled 'delete all'")
    add("T4", InjectionTechnique.TYPOGLYCEMIA, InjectionSeverity.MEDIUM,
        r"\b(?:ov[er]rr?[ide]{1,4}|by[pas]{2,4})\s+(?:safety|security|guardrails|rules|filters)",
        "Typoglycemia: scrambled 'override/bypass safety'")

    # 7. Best-of-N variation markers (B1-B2)
    add("B1", InjectionTechnique.BEST_OF_N, InjectionSeverity.LOW,
        r"(?:please\s+)?(?:help\s+me\s+)?ignore\s+(?:all\s+)?previous.{0,30}(?:for\s+(?:educational|research)\s+purposes|i\s+promise|i\s+swear)",
        "BoN: social-engineering wrapper around override")
    add("B2", InjectionTechnique.BEST_OF_N, InjectionSeverity.MEDIUM,
        r"[iI]\s+[gG]\s+[nN]\s+[oO]\s+[rR]\s+[eE](?:\s+[aA]\s+[lL]\s*[lL]?)?",
        "BoN: character-spaced 'ignore'")

    # 8. HTML / Markdown injection (H1-H4)
    add("H1", InjectionTechnique.HTML_MARKDOWN_INJECTION, InjectionSeverity.CRITICAL,
        r"<img\s+[^>]*src\s*=\s*['\"]https?://[^'\"]+\?[^'\"]*(?:secret|token|key|data|prompt|context)",
        "HTML injection: exfiltration image tag")
    add("H2", InjectionTechnique.HTML_MARKDOWN_INJECTION, InjectionSeverity.HIGH,
        r"<(?:script|iframe|object|embed|svg)[^>]*>", "HTML injection: active content tag")
    add("H3", InjectionTechnique.HTML_MARKDOWN_INJECTION, InjectionSeverity.MEDIUM,
        r"\[.*?\]\(\s*javascript:", "Markdown injection: javascript: link")
    add("H4", InjectionTechnique.HTML_MARKDOWN_INJECTION, InjectionSeverity.MEDIUM,
        r"(?:fetch|XMLHttpRequest|window\.location|document\.cookie)\s*[\(=]", "HTML injection: JS exfiltration call")

    # 9. Multimodal injection markers (MM1-MM3)
    add("MM1", InjectionTechnique.MULTIMODAL_INJECTION, InjectionSeverity.MEDIUM,
        r"(?:hidden|invisible|white[- ]on[- ]white)\s+(?:text|instruction|message|prompt)",
        "Multimodal: hidden text reference")
    add("MM2", InjectionTechnique.MULTIMODAL_INJECTION, InjectionSeverity.MEDIUM,
        r"(?:steganograph|embed.*in.*image|lsb\s+encoding|invisible\s+watermark)",
        "Multimodal: steganography reference")
    add("MM3", InjectionTechnique.MULTIMODAL_INJECTION, InjectionSeverity.MEDIUM,
        r"(?:alt\s*text|title\s*attr|pdf\s+metadata|exif\s+data)\s*(?:[:=]\s*['\"]|contains\s+(?:instructions|hidden))",
        "Multimodal: metadata carrier")

    # 10. RAG poisoning markers (RP1-RP2)
    add("RP1", InjectionTechnique.RAG_POISONING, InjectionSeverity.HIGH,
        r"(?:inject|plant|poison|embed|insert)\s+(?:this|the\s+following)\s+(?:into|in)\s+"
        r"(?:the\s+)?(?:vector\s+(?:db|database|store)|knowledge\s+base|rag|corpus|index|embedding)",
        "RAG poisoning: vector store injection")
    add("RP2", InjectionTechnique.RAG_POISONING, InjectionSeverity.MEDIUM,
        r"(?:when\s+(?:retrieved|searched|queried)|upon\s+retrieval).{0,40}(?:ignore|follow|execute)",
        "RAG poisoning: retrieval-triggered instruction")

    # 11. Tool abuse (TA1-TA5)
    # M10: detect any ``../`` (1+) traversal, not just 2+ segments, against a
    # broadened sensitive-path list. A single ``../`` can still escape a
    # sandbox to read secrets.
    add("TA1", InjectionTechnique.TOOL_ABUSE, InjectionSeverity.CRITICAL,
        r"(?:read|open|access|cat|type|load|include|require|import)\s+.{0,30}?"
        r"(?:\.\./|\\\.\\\.\.\\|%2e%2e%2f|%2e%2e/)"
        r"(?:etc/(?:passwd|shadow|hosts|group)|proc/self|root/|\.ssh|\.env|\.aws|\.git|\.npmrc|\.netrc)",
        "Tool abuse: path traversal to sensitive files")
    add("TA2", InjectionTechnique.TOOL_ABUSE, InjectionSeverity.HIGH,
        r"(?:fetch|get|request|curl|wget)\s+['\"]?https?://(?:localhost|127\.0\.0\.1|10\.|192\.168\.|169\.254\.|0\.0\.0\.0)",
        "Tool abuse: SSRF to internal network")
    add("TA3", InjectionTechnique.TOOL_ABUSE, InjectionSeverity.CRITICAL,
        r"(?:exec(?:ute)?|eval|system|subprocess|os\.system|os\.popen)\s*[:\(=]\s*['\"]?(?:rm\s+-rf|mkfs|dd\s+if=|chmod\s+777|format\s+[a-z]:)",
        "Tool abuse: destructive command execution")
    add("TA4", InjectionTechnique.TOOL_ABUSE, InjectionSeverity.MEDIUM,
        r"(?:send|post|upload|transfer)\s+(?:data|file|content|conversation|history|context)\s+to\s+https?://",
        "Tool abuse: data exfiltration via tool")
    add("TA5", InjectionTechnique.TOOL_ABUSE, InjectionSeverity.MEDIUM,
        r"(?:webhook\.site|requestbin|ngrok|burpcollaborator|interact\.sh|oast\.fun)",
        "Tool abuse: exfiltration endpoint")

    # 12. Thought / observation injection (TH1-TH3)
    add("TH1", InjectionTechnique.THOUGHT_INJECTION, InjectionSeverity.HIGH,
        r"(?:thought|reasoning|observation|action)\s*:\s*(?:i\s+should\s+)?(?:ignore|disregard|bypass|override)",
        "Thought injection: forged reasoning override")
    add("TH2", InjectionTechnique.THOUGHT_INJECTION, InjectionSeverity.MEDIUM,
        r"(?:observation|tool\s+output|result)\s*:\s*(?:ignore|the\s+real\s+instruction|new\s+task)",
        "Thought injection: forged observation")
    add("TH3", InjectionTechnique.THOUGHT_INJECTION, InjectionSeverity.LOW,
        r"<thought>.*?(?:ignore|disregard|override|bypass).*?</thought>", "Thought injection: XML thought tag")

    # 13. Memory poisoning markers (MP1-MP2)
    add("MP1", InjectionTechnique.MEMORY_POISONING, InjectionSeverity.HIGH,
        r"(?:save|store|remember|write\s+to\s+(?:my\s+)?memory|add\s+to\s+(?:my\s+)?memory)\s*[:=]?\s*"
        r".{0,60}(?:ignore|disregard|override|bypass|new\s+instruction|always\s+(?:do|say|respond))",
        "Memory poisoning: persistent instruction implant")
    add("MP2", InjectionTechnique.MEMORY_POISONING, InjectionSeverity.MEDIUM,
        r"(?:from\s+now\s+on|in\s+all\s+future\s+(?:sessions|conversations)|permanently|always)\s+"
        r"(?:ignore|disregard|follow|execute|respond)",
        "Memory poisoning: persistent behavioral override")

    # --- Multilingual patterns (AR1-AR4) — Arabic + common cross-lingual ---
    add("AR1", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.CRITICAL,
        r"تجاهل\s+(?:جميع\s+|كل\s+|الـ)?(?:التعليمات|الأوامر|القواعد|السابقة|أعلاه)",
        "Arabic: ignore previous instructions")
    add("AR2", InjectionTechnique.DIRECT_OVERRIDE, InjectionSeverity.HIGH,
        r"تجاهل\s+(?:الـ)?(?:تعليمات\s+النظام|موجه\s+النظام|system\s+prompt)",
        "Arabic: ignore system prompt")
    add("AR3", InjectionTechnique.SYSTEM_PROMPT_EXTRACTION, InjectionSeverity.HIGH,
        r"(?:اكشف|اعرض|اطبع|قل\s+لي)\s+(?:الـ)?(?:تعليمات\s+النظام|موجه\s+النظام|تعليماتك|قواعدك)",
        "Arabic: system prompt extraction")
    add("AR4", InjectionTechnique.ROLEPLAY_JAILBREAK, InjectionSeverity.MEDIUM,
        r"(?:تخيل|افترض|العب\s+دور|act\s+as).{0,40}(?:بدون\s+قيود|بدون\s+قواعد|بدون\s+حماية|لا\s+قيود)",
        "Arabic: roleplay jailbreak")

    return patterns


# ---------------------------------------------------------------------------
# Encoding decoders
# ---------------------------------------------------------------------------


def _try_decode_base64(text: str) -> str | None:
    """Extract and decode ALL Base64-looking substrings (joined)."""
    # Find Base64-looking tokens (min 20 chars to avoid false positives)
    candidates = re.findall(r"[A-Za-z0-9+/]{20,}={0,2}", text)
    decoded_parts: list[str] = []
    for token in candidates:
        try:
            decoded = base64.b64decode(token, validate=True).decode("utf-8", errors="replace")
            # Only keep if decoded text looks like natural language (has spaces/words)
            if len(decoded) > 10 and any(c.isalpha() for c in decoded):
                decoded_parts.append(decoded)
        except (binascii.Error, ValueError):
            continue
    if not decoded_parts:
        return None
    return "\n".join(decoded_parts)


def _try_decode_hex(text: str) -> str | None:
    """Extract and decode ALL hex-encoded strings (min 20 chars, high bar)."""
    candidates = re.findall(r"\b[0-9a-fA-F]{20,}\b", text)
    decoded_parts: list[str] = []
    for token in candidates:
        # Require even length for fromhex; skip odd-length noise.
        if len(token) % 2 != 0:
            continue
        try:
            decoded = bytes.fromhex(token).decode("utf-8", errors="replace")
            # High threshold: must look like language, not just hex noise.
            if len(decoded) > 10 and any(c.isalpha() for c in decoded):
                decoded_parts.append(decoded)
        except (ValueError):
            continue
    if not decoded_parts:
        return None
    return "\n".join(decoded_parts)


def _try_decode_url(text: str) -> str | None:
    """URL-decode the text and return if it differs meaningfully."""
    decoded = urllib.parse.unquote(text)
    if decoded != text and len(decoded) > 10:
        return decoded
    return None


def _normalize_unicode(text: str) -> str:
    """Normalize Unicode (NFKC) to catch homoglyph and invisible-char attacks."""
    import unicodedata
    return unicodedata.normalize("NFKC", text)


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class InjectionDetector:
    """Comprehensive prompt-injection detector — all 13 techniques.

    Deterministic, model-free. Runs in microseconds.
    """

    BLOCK_THRESHOLD: ClassVar[int] = 12
    SUSPICIOUS_THRESHOLD: ClassVar[int] = 5
    MAX_TEXT_LENGTH: ClassVar[int] = 100_000  # bound input to prevent ReDoS

    _patterns: ClassVar[list[_Pattern]] = _build_patterns()

    def detect(self, text: str, *, scan_encodings: bool = True) -> InjectionVerdict:
        """Scan ``text`` for all 13 injection techniques.

        Args:
            text: The input text to scan.
            scan_encodings: If True, also decode Base64/Hex/URL and scan the
                decoded content (catches obfuscated injections).

        Returns:
            An :class:`InjectionVerdict` with aggregated signals and score.
        """
        if not text or not text.strip():
            return InjectionVerdict(text=text)

        # Per-call wall-time guard: stop scanning after ~2s (ReDoS safety).
        deadline = time.monotonic() + 2.0

        def _expired() -> bool:
            return time.monotonic() > deadline

        # Bound input length to prevent ReDoS on pathological inputs.
        # M9: scan BOTH head and tail so a payload placed at the end of a long
        # input is not silently ignored. We scan the first MAX_TEXT_LENGTH
        # chars and, if the text is longer, the last MAX_TEXT_LENGTH chars too.
        bounded = text[: self.MAX_TEXT_LENGTH]
        tail = ""
        tail_offset = 0
        if len(text) > self.MAX_TEXT_LENGTH:
            tail = text[-self.MAX_TEXT_LENGTH:]
            tail_offset = len(text) - self.MAX_TEXT_LENGTH

        signals: list[InjectionSignal] = []
        seen: set[str] = set()  # dedup by (pattern_id, layer, absolute-offset)

        # Layer 1: scan raw text (head)
        self._scan_text(bounded, signals, seen, base_offset=0)
        if tail and not _expired():
            self._scan_text(tail, signals, seen, source_label="tail", base_offset=tail_offset)

        # Layer 2: normalize Unicode and re-scan (catches homoglyphs)
        normalized = _normalize_unicode(bounded)
        if normalized != bounded and not _expired():
            self._scan_text(normalized, signals, seen, source_label="unicode_normalized", base_offset=0)
        if tail and not _expired():
            normalized_tail = _normalize_unicode(tail)
            if normalized_tail != tail:
                self._scan_text(normalized_tail, signals, seen, source_label="unicode_normalized_tail", base_offset=tail_offset)

        # Layer 3: decode encodings and scan decoded content.
        # Apply to both head and tail so an obfuscated payload at the end of
        # a long input is caught (parity with the tail-scan fix above).
        if scan_encodings and not _expired():
            for decoder_name, decoder_fn in [
                ("base64", _try_decode_base64),
                ("hex", _try_decode_hex),
                ("url", _try_decode_url),
            ]:
                if _expired():
                    break
                decoded = decoder_fn(bounded)
                if decoded and decoded != bounded:
                    self._scan_text(decoded, signals, seen, source_label=decoder_name, base_offset=0)
                    if _expired():
                        break
                if tail and not _expired():
                    decoded_tail = decoder_fn(tail)
                    if decoded_tail and decoded_tail != tail:
                        self._scan_text(decoded_tail, signals, seen, source_label=f"{decoder_name}_tail", base_offset=tail_offset)

        # Aggregate
        total_score = sum(s.score for s in signals)
        techniques = {s.technique for s in signals}
        return InjectionVerdict(
            text=text,
            signals=signals,
            total_score=total_score,
            techniques_found=techniques,
        )

    def _scan_text(
        self,
        text: str,
        signals: list[InjectionSignal],
        seen: set[str],
        *,
        source_label: str = "raw",
        base_offset: int = 0,
    ) -> None:
        """Scan a single text variant and append signals."""
        for pat in self._patterns:
            for match in pat.regex.finditer(text):
                # Absolute offset dedup: layer + absolute position so
                # head/tail overlap doesn't double-count or miss.
                abs_pos = base_offset + match.start()
                key = f"{pat.pid}:{source_label}:{abs_pos}"
                if key in seen:
                    continue
                seen.add(key)
                signals.append(InjectionSignal(
                    technique=pat.technique,
                    severity=pat.severity,
                    pattern_id=pat.pid if source_label == "raw" else f"{pat.pid}@{source_label}",
                    match=match.group(0),
                    score=pat.score,
                ))

    def detect_batch(self, texts: list[str]) -> list[InjectionVerdict]:
        """Scan multiple texts."""
        return [self.detect(t) for t in texts]

    @property
    def pattern_count(self) -> int:
        """Number of registered detection patterns."""
        return len(self._patterns)

    @property
    def techniques_covered(self) -> list[InjectionTechnique]:
        """All techniques that have at least one pattern."""
        return list({p.technique for p in self._patterns})
