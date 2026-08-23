"""LLM provider registry — single source of truth for provider metadata.

Ported from open-notebook (lfnovo/open-notebook)
``open_notebook/ai/provider_registry.py``.
All downstream surfaces (budget cost rates, MCP model selection,
persona model routing) derive from this one registry. Adding a
provider = one entry in ``_PROVIDER_SPECS``.

Each :class:`ProviderSpec` holds:
- ``name``: stable machine-readable key (e.g. ``"openai"``)
- ``display_name``: human-readable label
- ``modalities``: tuple of supported modalities
- ``required_env``: env vars that ALL must be set for the provider
- ``required_any_env``: env vars where at least ONE must be set
- ``optional_env``: env vars read but not required
- ``test_model``: cheapest model for connection testing
- ``docs_url``: where users get an API key
- ``input_cost_per_1m``: USD per 1M input tokens (for budget.py)
- ``output_cost_per_1m``: USD per 1M output tokens (for budget.py)
- ``context_window``: max context window in tokens
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSpec:
    """Everything the runtime needs to know about one LLM provider."""

    name: str
    display_name: str
    modalities: tuple[str, ...]
    required_env: tuple[str, ...] = ()
    required_any_env: tuple[str, ...] = ()
    optional_env: tuple[str, ...] = ()
    test_model: str | None = None
    docs_url: str | None = None
    input_cost_per_1m: float = 0.0  # USD per 1M input tokens
    output_cost_per_1m: float = 0.0  # USD per 1M output tokens
    context_window: int = 0  # max tokens

    def env_config(self) -> dict[str, list[str]]:
        """Env var config in a structured dict shape."""
        config: dict[str, list[str]] = {}
        if self.required_env:
            config["required"] = list(self.required_env)
        if self.required_any_env:
            config["required_any"] = list(self.required_any_env)
        if self.optional_env:
            config["optional"] = list(self.optional_env)
        return config

    def is_configured(self) -> bool:
        """Return True if all required env vars are set."""
        if any(not os.getenv(var) for var in self.required_env):
            return False
        if self.required_any_env:
            return any(os.getenv(var) for var in self.required_any_env)
        return True

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate USD cost for a token usage."""
        return (
            (input_tokens / 1_000_000) * self.input_cost_per_1m
            + (output_tokens / 1_000_000) * self.output_cost_per_1m
        )


_LANGUAGE_ONLY: tuple[str, ...] = ("language",)
_ALL_MODALITIES: tuple[str, ...] = (
    "language", "embedding", "speech_to_text", "text_to_speech",
)


# ---------------------------------------------------------------------------
# Provider registry — the single source of truth.
# Cost rates are approximate as of 2026-08; update when prices change.
# ---------------------------------------------------------------------------

_PROVIDER_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="openai",
        display_name="OpenAI",
        modalities=_ALL_MODALITIES,
        required_env=("OPENAI_API_KEY",),
        test_model="gpt-4o-mini",
        docs_url="https://platform.openai.com/api-keys",
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
        context_window=128_000,
    ),
    ProviderSpec(
        name="anthropic",
        display_name="Anthropic",
        modalities=_LANGUAGE_ONLY,
        required_env=("ANTHROPIC_API_KEY",),
        test_model="claude-3-haiku-20240307",
        docs_url="https://console.anthropic.com/settings/keys",
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        context_window=200_000,
    ),
    ProviderSpec(
        name="google",
        display_name="Google AI",
        modalities=_ALL_MODALITIES,
        required_any_env=("GOOGLE_API_KEY", "GEMINI_API_KEY"),
        test_model="gemini-1.5-flash",
        docs_url="https://aistudio.google.com/app/apikey",
        input_cost_per_1m=0.075,
        output_cost_per_1m=0.30,
        context_window=1_000_000,
    ),
    ProviderSpec(
        name="groq",
        display_name="Groq",
        modalities=("language", "speech_to_text"),
        required_env=("GROQ_API_KEY",),
        test_model="llama-3.1-8b-instant",
        docs_url="https://console.groq.com/keys",
        input_cost_per_1m=0.05,
        output_cost_per_1m=0.08,
        context_window=128_000,
    ),
    ProviderSpec(
        name="mistral",
        display_name="Mistral AI",
        modalities=("language", "embedding", "speech_to_text", "text_to_speech"),
        required_env=("MISTRAL_API_KEY",),
        test_model="mistral-small-latest",
        docs_url="https://console.mistral.ai/api-keys/",
        input_cost_per_1m=0.20,
        output_cost_per_1m=0.60,
        context_window=128_000,
    ),
    ProviderSpec(
        name="deepseek",
        display_name="DeepSeek",
        modalities=_LANGUAGE_ONLY,
        required_env=("DEEPSEEK_API_KEY",),
        test_model="deepseek-chat",
        docs_url="https://platform.deepseek.com/api_keys",
        input_cost_per_1m=0.14,
        output_cost_per_1m=0.28,
        context_window=128_000,
    ),
    ProviderSpec(
        name="ollama",
        display_name="Ollama (local)",
        modalities=_LANGUAGE_ONLY,
        optional_env=("OLLAMA_BASE_URL",),
        test_model="llama3.2",
        docs_url="https://ollama.com/download",
        input_cost_per_1m=0.0,  # local = free
        output_cost_per_1m=0.0,
        context_window=128_000,
    ),
    ProviderSpec(
        name="openrouter",
        display_name="OpenRouter",
        modalities=_LANGUAGE_ONLY,
        required_env=("OPENROUTER_API_KEY",),
        test_model="openai/gpt-4o-mini",
        docs_url="https://openrouter.ai/keys",
        input_cost_per_1m=2.50,  # varies by model
        output_cost_per_1m=10.00,
        context_window=128_000,
    ),
)


# Build a name → spec dict for fast lookup.
_PROVIDERS: dict[str, ProviderSpec] = {spec.name: spec for spec in _PROVIDER_SPECS}


def get_provider(name: str) -> ProviderSpec | None:
    """Return the spec for *name*, or ``None`` if unknown."""
    return _PROVIDERS.get(name)


def get_all_providers() -> dict[str, ProviderSpec]:
    """Return a copy of the full provider registry."""
    return dict(_PROVIDERS)


def get_configured_providers() -> list[ProviderSpec]:
    """Return all providers whose required env vars are set."""
    return [spec for spec in _PROVIDER_SPECS if spec.is_configured()]


def get_providers_by_modality(modality: str) -> list[ProviderSpec]:
    """Return all providers that support *modality*."""
    return [spec for spec in _PROVIDER_SPECS if modality in spec.modalities]


def get_cheapest_provider(modality: str = "language") -> ProviderSpec | None:
    """Return the cheapest configured provider for *modality*."""
    candidates = [
        spec for spec in get_configured_providers()
        if modality in spec.modalities
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda s: s.input_cost_per_1m + s.output_cost_per_1m)


def estimate_cost(
    provider_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate USD cost for a token usage on *provider_name*."""
    spec = get_provider(provider_name)
    if spec is None:
        return 0.0
    return spec.estimate_cost(input_tokens, output_tokens)


def list_provider_names() -> list[str]:
    """Return all registered provider names in declaration order."""
    return [spec.name for spec in _PROVIDER_SPECS]
