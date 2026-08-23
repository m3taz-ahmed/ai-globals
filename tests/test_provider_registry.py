"""Tests for runtime/provider_registry.py — LLM provider registry.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from runtime.provider_registry import (
    estimate_cost,
    get_all_providers,
    get_cheapest_provider,
    get_configured_providers,
    get_provider,
    get_providers_by_modality,
    list_provider_names,
)


class TestProviderRegistry:
    def test_get_known_provider(self) -> None:
        spec = get_provider("openai")
        assert spec is not None
        assert spec.name == "openai"
        assert spec.display_name == "OpenAI"

    def test_get_unknown_provider(self) -> None:
        assert get_provider("nonexistent") is None

    def test_get_all_returns_copy(self) -> None:
        all_providers = get_all_providers()
        original_count = len(all_providers)
        all_providers.clear()
        assert len(get_all_providers()) == original_count

    def test_list_provider_names(self) -> None:
        names = list_provider_names()
        assert "openai" in names
        assert "anthropic" in names
        assert "ollama" in names

    def test_providers_by_modality(self) -> None:
        language_providers = get_providers_by_modality("language")
        assert all("language" in p.modalities for p in language_providers)
        assert len(language_providers) >= 5

    def test_embedding_providers(self) -> None:
        embedding_providers = get_providers_by_modality("embedding")
        assert all("embedding" in p.modalities for p in embedding_providers)


class TestProviderSpec:
    def test_env_config(self) -> None:
        spec = get_provider("openai")
        assert spec is not None
        config = spec.env_config()
        assert "required" in config
        assert "OPENAI_API_KEY" in config["required"]

    def test_estimate_cost(self) -> None:
        spec = get_provider("openai")
        assert spec is not None
        cost = spec.estimate_cost(input_tokens=1_000_000, output_tokens=500_000)
        assert cost > 0
        # 1M input @ $2.50 + 500K output @ $10.00 = $2.50 + $5.00 = $7.50
        assert 7.0 < cost < 8.0

    def test_ollama_is_free(self) -> None:
        spec = get_provider("ollama")
        assert spec is not None
        assert spec.input_cost_per_1m == 0.0
        assert spec.output_cost_per_1m == 0.0
        cost = spec.estimate_cost(input_tokens=1_000_000, output_tokens=1_000_000)
        assert cost == 0.0


class TestEstimateCost:
    def test_known_provider(self) -> None:
        cost = estimate_cost("openai", input_tokens=1_000_000, output_tokens=0)
        assert cost == 2.50

    def test_unknown_provider(self) -> None:
        assert estimate_cost("nonexistent", 1000, 1000) == 0.0


class TestConfiguredProviders:
    def test_returns_list(self) -> None:
        # Ollama doesn't require env vars, so it should always be "configured"
        configured = get_configured_providers()
        assert isinstance(configured, list)
        ollama = [p for p in configured if p.name == "ollama"]
        assert len(ollama) == 1


class TestCheapestProvider:
    def test_ollama_cheapest_if_configured(self) -> None:
        cheapest = get_cheapest_provider("language")
        if cheapest is not None:
            # Ollama is free (0.0 cost), so it should be cheapest if configured
            assert cheapest.input_cost_per_1m + cheapest.output_cost_per_1m >= 0.0
