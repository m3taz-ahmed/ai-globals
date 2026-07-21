"""Pydantic schemas for runtime configuration and action validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from runtime.budget import ALLOWED_EXCEED, ALLOWED_PERIODS


class BudgetSchema(BaseModel):
    """Budget configuration schema."""

    model_config = ConfigDict(extra="allow")

    max_tokens: int | None = None
    max_cost_usd: float | None = None
    max_calls: int | None = None
    period: str = "session"
    on_exceed: str = "block"
    fallback_model: str | None = None

    @field_validator("period")
    @classmethod
    def _validate_period(cls, v: str) -> str:
        if v not in ALLOWED_PERIODS:
            raise ValueError(f"period must be one of {ALLOWED_PERIODS}")
        return v

    @field_validator("on_exceed")
    @classmethod
    def _validate_on_exceed(cls, v: str) -> str:
        if v not in ALLOWED_EXCEED:
            raise ValueError(f"on_exceed must be one of {ALLOWED_EXCEED}")
        return v


class PolicyRuleSchema(BaseModel):
    """Policy rule schema."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., min_length=1)
    condition: str = Field(..., min_length=1)
    action: str = Field(..., pattern="^(allow|ask|deny)$")
    description: str = ""
    approvers: list[str] = Field(default_factory=list)


class PolicyFileSchema(BaseModel):
    """Top-level policy YAML schema."""

    name: str = "default"
    api_version: str = "governance.ai-global-os/v1"
    default_action: str = "ask"
    rules: list[PolicyRuleSchema] = Field(default_factory=list)

    @field_validator("default_action")
    @classmethod
    def _validate_default_action(cls, v: str) -> str:
        if v not in ("allow", "ask", "deny"):
            raise ValueError("default_action must be allow, ask, or deny")
        return v
