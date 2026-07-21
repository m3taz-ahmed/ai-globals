"""Prometheus-style metrics collector for AI Global OS."""

from __future__ import annotations

from runtime.kernel import Kernel


def format_metrics(k: Kernel) -> str:
    """Return Prometheus exposition text for key runtime metrics."""
    status = k.status()
    lines: list[str] = [
        "# HELP aios_workflows_total Total number of registered workflows",
        "# TYPE aios_workflows_total gauge",
        f"aios_workflows_total {len(status['workflows'])}",
        "",
        "# HELP aios_rules_total Total number of loaded policy rules",
        "# TYPE aios_rules_total gauge",
        f"aios_rules_total {len(status['rules'])}",
        "",
        "# HELP aios_budgets_total Total number of configured budgets",
        "# TYPE aios_budgets_total gauge",
        f"aios_budgets_total {len(status['budgets'])}",
        "",
    ]

    for scope, usage in k.budget.usage.items():
        labels = f'scope="{scope}"'
        lines.append(f"# HELP aios_budget_tokens_total Total tokens used for scope {scope}")
        lines.append("# TYPE aios_budget_tokens_total counter")
        lines.append(f"aios_budget_tokens_total{{{labels}}} {usage.get('tokens', 0)}")
        lines.append("")
        lines.append(f"# HELP aios_budget_calls_total Total calls for scope {scope}")
        lines.append("# TYPE aios_budget_calls_total counter")
        lines.append(f"aios_budget_calls_total{{{labels}}} {usage.get('calls', 0)}")
        lines.append("")

    return "\n".join(lines)
