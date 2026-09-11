"""aiZee runtime kernel.

NOTE: This module re-exports ~100 symbols for convenient access. Not all are
wired into the production kernel pipeline - some are internal/experimental
modules used only by their own tests or by cross-references between themselves.
The production-wired modules are: kernel, managers/*, policy, budget, audit,
guardian, probity, persona, loop_detector, saga, workflow, repository, crypto,
telemetry, tracing, metrics, middleware, mcp_firewall, mcp_client, tech_stack,
settings, skill_resolver, sovereign, design_library, design_slop_verifier,
agent_baseline, agent_discovery, local_responder, chat, preloop, approval_cache,
approval_service, defensive_injection, injection_detector, taint,
tool_output_sanitizer, plugin_system, spec_engine, spec/*, guardrails/*,
uninstaller, uninstaller_gui, ci, astryx, governance, enums, schemas,
storage_backend, service_catalog, rule_compiler, rule_frontmatter,
mcp_orchestrator, tracing_otel, attribution_model, billing_ledger,
crm_manager, drip_engine, experiment_tracker, feature_flags, funnel_tracker,
lead_scorer, marketing_compliance, pipeline_analytics, pricing_calculator,
post_queue. The remaining exports are retained for test compatibility and
potential future wiring.
"""

from __future__ import annotations

import config

__version__ = config.VERSION

# Re-export the production Kernel facade and managers.
# Re-export new governance modules for convenient access.
import runtime.attribution_model as attribution_model
import runtime.billing_ledger as billing_ledger
import runtime.crm_manager as crm_manager
import runtime.drip_engine as drip_engine
import runtime.experiment_tracker as experiment_tracker
import runtime.feature_flags as feature_flags
import runtime.funnel_tracker as funnel_tracker
import runtime.lead_scorer as lead_scorer
import runtime.marketing_compliance as marketing_compliance
import runtime.pipeline_analytics as pipeline_analytics
import runtime.post_queue as post_queue

# Freelance + Marketing/E-marketing runtime modules (Phase 1).
import runtime.pricing_calculator as pricing_calculator
from runtime.agent_baseline import AgentAction as AgentAction
from runtime.agent_baseline import AgentBaseline as AgentBaseline
from runtime.agent_baseline import AnomalyAlert as AnomalyAlert
from runtime.agent_baseline import AnomalyType as AnomalyType
from runtime.agent_baseline import BaselineRegistry as BaselineRegistry
from runtime.agent_catalog import AgentCatalog as AgentCatalog
from runtime.agent_catalog import CatalogAgent as CatalogAgent
from runtime.agent_catalog import CatalogFlow as CatalogFlow
from runtime.agent_catalog import CatalogModel as CatalogModel
from runtime.agent_circuit_breaker import CbConfig as CbConfig
from runtime.agent_circuit_breaker import CbState as CbState
from runtime.agent_circuit_breaker import SemanticCircuitBreaker as SemanticCircuitBreaker
from runtime.agent_discovery import AgentDiscovery as AgentDiscovery
from runtime.agent_gateway import AgentGateway as AgentGateway
from runtime.agent_gateway import GuardrailContext as GuardrailContext
from runtime.agent_gateway import GuardrailPhase as GuardrailPhase
from runtime.agent_gateway import GuardrailResult as GuardrailResult
from runtime.agent_gateway import Verdict as Verdict
from runtime.agent_sli import AgentSliCollector as AgentSliCollector
from runtime.agent_sli import SliResult as SliResult
from runtime.agent_sli import SliStatus as SliStatus
from runtime.agent_sli import TaskRecord as TaskRecord
from runtime.approval_channels import DiscordChannel as DiscordChannel
from runtime.approval_channels import EmailChannel as EmailChannel
from runtime.approval_channels import SlackChannel as SlackChannel
from runtime.approval_service import ApprovalService as ApprovalService
from runtime.approval_sla import ApprovalSlaManager as ApprovalSlaManager
from runtime.approval_sla import DecisionDelta as DecisionDelta
from runtime.approval_sla import SlaAction as SlaAction
from runtime.approval_sla import SlaPolicy as SlaPolicy
from runtime.audit_signing import AuditSigner as AuditSigner
from runtime.audit_signing import SignatureResult as SignatureResult
from runtime.audit_signing import SignatureScheme as SignatureScheme
from runtime.blade_template_linter import BladeFinding as BladeFinding
from runtime.blade_template_linter import BladeSeverity as BladeSeverity
from runtime.blade_template_linter import BladeTemplateLinter as BladeTemplateLinter
from runtime.blast_radius import BlastEdge as BlastEdge
from runtime.blast_radius import BlastNode as BlastNode
from runtime.blast_radius import BlastPath as BlastPath
from runtime.blast_radius import BlastRadiusGraph as BlastRadiusGraph
from runtime.blast_radius import ImpactLevel as ImpactLevel
from runtime.blast_radius import NodeType as NodeType
from runtime.budget_advanced import BurnForecast as BurnForecast
from runtime.budget_advanced import BurnForecaster as BurnForecaster
from runtime.budget_advanced import ModelCostOptimizer as ModelCostOptimizer
from runtime.budget_advanced import ReserveHold as ReserveHold
from runtime.budget_advanced import ReserveSettleProtocol as ReserveSettleProtocol
from runtime.budget_advanced import ShadowModeTracker as ShadowModeTracker
from runtime.budget_advanced import SpendAnomaly as SpendAnomaly
from runtime.budget_advanced import SpendAnomalyDetector as SpendAnomalyDetector
from runtime.budget_advanced import ThrottleConfig as ThrottleConfig
from runtime.budget_advanced import ThrottleTier as ThrottleTier
from runtime.closure_evaluator import ClosureEvaluator as ClosureEvaluator
from runtime.closure_evaluator import GuardianClosureEvaluator as GuardianClosureEvaluator
from runtime.commands import Command as Command
from runtime.commands import CommandBus as CommandBus
from runtime.commands import CommandResult as CommandResult
from runtime.commands import CommandStatus as CommandStatus
from runtime.composite_identity import CompositeIdentity as CompositeIdentity
from runtime.composite_identity import CompositeIdentityRegistry as CompositeIdentityRegistry
from runtime.composite_identity import Principal as Principal
from runtime.composite_identity import PrincipalRole as PrincipalRole
from runtime.confidence_gate import ConfidenceGate as ConfidenceGate
from runtime.confidence_gate import ConfidenceLevel as ConfidenceLevel
from runtime.confidence_gate import ConfidenceVerdict as ConfidenceVerdict
from runtime.confidence_gate import Evidence as Evidence
from runtime.context_manager import ContextManager as ContextManager
from runtime.contract_emitter import ContractArtifact as ContractArtifact
from runtime.contract_emitter import emit_contract as emit_contract
from runtime.contract_emitter import emit_contracts as emit_contracts
from runtime.cost_attribution import CostAnomaly as CostAnomaly
from runtime.cost_attribution import CostAnomalyType as CostAnomalyType
from runtime.cost_attribution import CostAttribution as CostAttribution
from runtime.cost_attribution import CostRecord as CostRecord
from runtime.cross_tool_taint import CrossToolTaintTracker as CrossToolTaintTracker
from runtime.cross_tool_taint import DataClassification as DataClassification
from runtime.cross_tool_taint import ToolCall as ToolCall
from runtime.cross_tool_taint import ToolSensitivity as ToolSensitivity
from runtime.cross_tool_taint import ToxicFlow as ToxicFlow
from runtime.db_migration_safety import MigrationFinding as MigrationFinding
from runtime.db_migration_safety import MigrationSafetyChecker as MigrationSafetyChecker
from runtime.db_migration_safety import MigrationSeverity as MigrationSeverity
from runtime.defensive_injection import DefenseResult as DefenseResult
from runtime.defensive_injection import DefenseStrategy as DefenseStrategy
from runtime.defensive_injection import DefensiveInjector as DefensiveInjector
from runtime.design_library import BrandDesignSystem as BrandDesignSystem
from runtime.design_library import DesignLibrary as DesignLibrary
from runtime.design_library import DesignLibraryError as DesignLibraryError
from runtime.design_library import DesignSection as DesignSection
from runtime.design_library import FusionResult as FusionResult
from runtime.design_library import ProjectType as ProjectType
from runtime.design_slop_verifier import DesignSlopError as DesignSlopError
from runtime.design_slop_verifier import DesignSlopVerifier as DesignSlopVerifier
from runtime.design_slop_verifier import SlopCategory as SlopCategory
from runtime.design_slop_verifier import SlopFinding as SlopFinding
from runtime.design_slop_verifier import SlopSeverity as SlopSeverity
from runtime.design_slop_verifier import SlopVerdict as SlopVerdict
from runtime.dual_llm import DualLLMError as DualLLMError
from runtime.dual_llm import DualLLMOrchestrator as DualLLMOrchestrator
from runtime.dual_llm import DualLLMResult as DualLLMResult
from runtime.dual_llm import LLMRole as LLMRole
from runtime.durable import DurableExecutor as DurableExecutor
from runtime.durable import DurableStep as DurableStep
from runtime.durable import DurableWorkflow as DurableWorkflow
from runtime.durable import StepStatus as StepStatus
from runtime.fairness_detector import FairnessDetector as FairnessDetector
from runtime.fairness_detector import FairnessFinding as FairnessFinding
from runtime.fairness_detector import FairnessReport as FairnessReport
from runtime.fairness_detector import FairnessStrategy as FairnessStrategy
from runtime.fairness_detector import ProtectedAttribute as ProtectedAttribute
from runtime.filament_access_auditor import AccessFinding as AccessFinding
from runtime.filament_access_auditor import AccessSeverity as AccessSeverity
from runtime.filament_access_auditor import FilamentAccessAuditor as FilamentAccessAuditor
from runtime.hallucination_detector import HallucinationDetector as HallucinationDetector
from runtime.hallucination_detector import HallucinationFinding as HallucinationFinding
from runtime.hallucination_detector import HallucinationSeverity as HallucinationSeverity
from runtime.hook_lifecycle import HookContext as HookContext
from runtime.hook_lifecycle import HookPhase as HookPhase
from runtime.hook_lifecycle import HookRegistry as HookRegistry
from runtime.injection_detector import InjectionDetector as InjectionDetector
from runtime.injection_detector import InjectionSeverity as InjectionSeverity
from runtime.injection_detector import InjectionSignal as InjectionSignal
from runtime.injection_detector import InjectionTechnique as InjectionTechnique
from runtime.injection_detector import InjectionVerdict as InjectionVerdict
from runtime.kernel import Kernel as Kernel
from runtime.kernel import KernelBuilder as KernelBuilder

# Laravel/Filament/UI governance modules (v5.14).
from runtime.laravel_policy_linter import LaravelFinding as LaravelFinding
from runtime.laravel_policy_linter import LaravelLintSeverity as LaravelLintSeverity
from runtime.laravel_policy_linter import LaravelPolicyLinter as LaravelPolicyLinter
from runtime.layers import Layer as Layer
from runtime.layers import LayerManifest as LayerManifest
from runtime.learning_loop import LearningLoop as LearningLoop
from runtime.llm_attestation import AttestationEnvelope as AttestationEnvelope
from runtime.llm_attestation import AttestationStatement as AttestationStatement
from runtime.llm_attestation import AttestationType as AttestationType
from runtime.llm_attestation import LlmAttestor as LlmAttestor
from runtime.llm_attestation import PrivacyMode as PrivacyMode
from runtime.loop_detector import LoopDetector as LoopDetector
from runtime.mcp_auditor import Finding as McpAuditorFinding
from runtime.mcp_auditor import FindingSeverity as FindingSeverity
from runtime.mcp_auditor import McpAuditor as McpAuditor
from runtime.mcp_firewall import McpFirewall as McpFirewall
from runtime.mcp_manifest_lock import ManifestFingerprint as ManifestFingerprint
from runtime.mcp_manifest_lock import ManifestLock as ManifestLock
from runtime.mcp_securable import Grant as Grant
from runtime.mcp_securable import McpPermission as McpPermission
from runtime.mcp_securable import McpSecurableRegistry as McpSecurableRegistry
from runtime.mcp_securable import McpServer as McpServer
from runtime.middleware import ActionContext as ActionContext
from runtime.middleware import MiddlewarePipeline as MiddlewarePipeline
from runtime.middleware import MiddlewareResult as MiddlewareResult
from runtime.mobile_patterns import MobileAuditConfig as MobileAuditConfig
from runtime.mobile_patterns import MobilePattern as MobilePattern
from runtime.mobile_patterns import MobilePatternAuditor as MobilePatternAuditor
from runtime.mobile_patterns import MobilePlatform as MobilePlatform
from runtime.mobile_patterns import PatternResult as PatternResult
from runtime.mobile_patterns import PatternSeverity as PatternSeverity
from runtime.model_router import ModelCapability as ModelCapability
from runtime.model_router import ModelInfo as ModelInfo
from runtime.model_router import ModelRouter as ModelRouter
from runtime.model_router import RouteDecision as RouteDecision
from runtime.model_router import RouteTier as RouteTier
from runtime.plan_diff_validator import Finding as Finding
from runtime.plan_diff_validator import PlanDiffValidator as PlanDiffValidator
from runtime.plan_diff_validator import ValidationLevel as ValidationLevel
from runtime.plan_diff_validator import ValidationResult as ValidationResult
from runtime.plugin_system import Plugin as Plugin
from runtime.plugin_system import PluginError as PluginError
from runtime.plugin_system import PluginManifest as PluginManifest
from runtime.plugin_system import PluginRegistry as PluginRegistry
from runtime.plugin_system import PluginStatus as PluginStatus
from runtime.plugin_system import PluginType as PluginType
from runtime.policy_lint import LintFinding as LintFinding
from runtime.policy_lint import LintSeverity as LintSeverity
from runtime.policy_lint import PolicyLinter as PolicyLinter
from runtime.prompt_gate import PromptGate as PromptGate
from runtime.prompt_injection_detector import DetectionLevel as DetectionLevel
from runtime.prompt_injection_detector import PromptInjectionDetector as PromptInjectionDetector
from runtime.prompt_injection_detector import SemanticDetectionResult as SemanticDetectionResult
from runtime.quality import Bounder as Bounder
from runtime.quality import CostProvider as CostProvider
from runtime.quality import FixedRateCostProvider as FixedRateCostProvider
from runtime.quality import LazyImport as LazyImport
from runtime.quality import OutputEnvelope as OutputEnvelope
from runtime.quality import ReflexionEntry as ReflexionEntry
from runtime.quality import ReflexionLog as ReflexionLog
from runtime.quality import Witness as Witness
from runtime.quality import WitnessRecorder as WitnessRecorder
from runtime.reasoning_graph import ReasoningGraph as ReasoningGraph
from runtime.rules_materializer import MaterializationResult as MaterializationResult
from runtime.rules_materializer import RuleEntry as RuleEntry
from runtime.rules_materializer import RulesMaterializer as RulesMaterializer
from runtime.rules_materializer import ScopeLevel as ScopeLevel
from runtime.rules_materializer import ToolTarget as ToolTarget
from runtime.scoped_manager import ScopedManager as ScopedManager
from runtime.scoped_manager import ScopedRegistry as ScopedRegistry
from runtime.scoped_manager import scoped_factory as scoped_factory
from runtime.skill_routing import PersonaDetectionResult as PersonaDetectionResult
from runtime.skill_routing import PersonaDetectorV2 as PersonaDetectorV2
from runtime.skill_routing import SkillRouter as SkillRouter
from runtime.skill_scanner import Baseline as Baseline
from runtime.skill_scanner import Finding as SkillFinding
from runtime.skill_scanner import PatternSeverity as ScanPatternSeverity
from runtime.skill_scanner import ScanResult as ScanResult
from runtime.skill_scanner import ScanRiskLevel as ScanRiskLevel
from runtime.skill_scanner import SkillScanner as SkillScanner
from runtime.stale_api_detector import StaleApiDetector as StaleApiDetector
from runtime.stale_api_detector import StaleApiFinding as StaleApiFinding
from runtime.stale_api_detector import StaleApiSeverity as StaleApiSeverity
from runtime.supply_chain_guard import DeclaredDependency as DeclaredDependency
from runtime.supply_chain_guard import DependencyEcosystem as DependencyEcosystem
from runtime.supply_chain_guard import OsvDevClient as OsvDevClient
from runtime.supply_chain_guard import SupplyChainGuard as SupplyChainGuard
from runtime.supply_chain_guard import TyposquatDetector as TyposquatDetector
from runtime.supply_chain_guard import TyposquatFinding as TyposquatFinding
from runtime.supply_chain_guard import UndeclaredImport as UndeclaredImport
from runtime.supply_chain_guard import VulnerabilityAdvisory as VulnerabilityAdvisory
from runtime.taint import TaintError as TaintError
from runtime.taint import TaintLabel as TaintLabel
from runtime.taint import TaintTracker as TaintTracker
from runtime.taint import classify_source as classify_taint_source
from runtime.tool_output_sanitizer import ToolOutputSanitizer as ToolOutputSanitizer
from runtime.tool_output_sanitizer import ToolSanitizeResult as ToolSanitizeResult
from runtime.trajectory import FailureCategory as FailureCategory
from runtime.trajectory import TrajectoryTracker as TrajectoryTracker
from runtime.ui_a11y_checker import A11yChecker as A11yChecker
from runtime.ui_a11y_checker import A11yFinding as A11yFinding
from runtime.ui_a11y_checker import A11ySeverity as A11ySeverity

__all__ = [
    "ActionContext",
    "AgentAction",
    "AgentBaseline",
    "AgentCatalog",
    "AgentDiscovery",
    "AgentGateway",
    "AgentSliCollector",
    "AnomalyAlert",
    "AnomalyType",
    "ApprovalService",
    "ApprovalSlaManager",
    "AttestationEnvelope",
    "AttestationStatement",
    "AttestationType",
    "AuditSigner",
    "Baseline",
    "BaselineRegistry",
    "BlastEdge",
    "BlastNode",
    "BlastPath",
    "BlastRadiusGraph",
    "Bounder",
    "BrandDesignSystem",
    "BurnForecast",
    "BurnForecaster",
    "CatalogAgent",
    "CatalogFlow",
    "CatalogModel",
    "CbConfig",
    "CbState",
    "ClosureEvaluator",
    "Command",
    "CommandBus",
    "CommandResult",
    "CommandStatus",
    "CompositeIdentity",
    "CompositeIdentityRegistry",
    "ConfidenceGate",
    "ConfidenceLevel",
    "ConfidenceVerdict",
    "ContextManager",
    "ContractArtifact",
    "CostAnomaly",
    "CostAnomalyType",
    "CostAttribution",
    "CostProvider",
    "CostRecord",
    "CrossToolTaintTracker",
    "CrossToolTaintTracker",
    "DataClassification",
    "DecisionDelta",
    "DeclaredDependency",
    "DefenseResult",
    "DefenseStrategy",
    "DefensiveInjector",
    "DependencyEcosystem",
    "DesignLibrary",
    "DesignLibraryError",
    "DesignSection",
    "DesignSlopError",
    "DesignSlopVerifier",
    "DetectionLevel",
    "DiscordChannel",
    "DualLLMError",
    "DualLLMOrchestrator",
    "DualLLMResult",
    "DurableExecutor",
    "DurableStep",
    "DurableWorkflow",
    "EmailChannel",
    "Evidence",
    "FailureCategory",
    "FairnessDetector",
    "FairnessFinding",
    "FairnessReport",
    "FairnessStrategy",
    "Finding",
    "FixedRateCostProvider",
    "FusionResult",
    "Grant",
    "GuardianClosureEvaluator",
    "GuardrailContext",
    "GuardrailPhase",
    "GuardrailResult",
    "HallucinationDetector",
    "HallucinationFinding",
    "HallucinationSeverity",
    "HookContext",
    "HookPhase",
    "HookRegistry",
    "ImpactLevel",
    "InjectionDetector",
    "InjectionSeverity",
    "InjectionSignal",
    "InjectionTechnique",
    "InjectionVerdict",
    "Kernel",
    "KernelBuilder",
    "LLMRole",
    "Layer",
    "LayerManifest",
    "LazyImport",
    "LearningLoop",
    "LintFinding",
    "LintSeverity",
    "LlmAttestor",
    "LoopDetector",
    "ManifestFingerprint",
    "ManifestLock",
    "MaterializationResult",
    "McpAuditor",
    "McpAuditorFinding",
    "McpFirewall",
    "McpPermission",
    "McpSecurableRegistry",
    "McpServer",
    "MiddlewarePipeline",
    "MiddlewareResult",
    "MobileAuditConfig",
    "MobilePattern",
    "MobilePatternAuditor",
    "MobilePlatform",
    "ModelCapability",
    "ModelCostOptimizer",
    "ModelInfo",
    "ModelRouter",
    "OsvDevClient",
    "OutputEnvelope",
    "PatternResult",
    "PatternSeverity",
    "PersonaDetectionResult",
    "PersonaDetectorV2",
    "PlanDiffValidator",
    "Plugin",
    "PluginError",
    "PluginManifest",
    "PluginRegistry",
    "PluginStatus",
    "PluginType",
    "PolicyLinter",
    "Principal",
    "PrincipalRole",
    "PrivacyMode",
    "ProjectType",
    "PromptGate",
    "PromptInjectionDetector",
    "ProtectedAttribute",
    "ReasoningGraph",
    "ReflexionEntry",
    "ReflexionLog",
    "ReserveHold",
    "ReserveSettleProtocol",
    "RouteDecision",
    "RouteTier",
    "RuleEntry",
    "RulesMaterializer",
    "ScanPatternSeverity",
    "ScanResult",
    "ScanRiskLevel",
    "ScopeLevel",
    "ScopedManager",
    "ScopedRegistry",
    "SemanticCircuitBreaker",
    "SemanticDetectionResult",
    "ShadowModeTracker",
    "SignatureResult",
    "SignatureScheme",
    "SkillFinding",
    "SkillRouter",
    "SkillScanner",
    "SlaAction",
    "SlaPolicy",
    "SlackChannel",
    "SliResult",
    "SliStatus",
    "SlopCategory",
    "SlopFinding",
    "SlopSeverity",
    "SlopVerdict",
    "SpendAnomaly",
    "SpendAnomalyDetector",
    "StaleApiDetector",
    "StaleApiFinding",
    "StaleApiSeverity",
    "StepStatus",
    "SupplyChainGuard",
    "TaintError",
    "TaintLabel",
    "TaintTracker",
    "TaskRecord",
    "ThrottleConfig",
    "ThrottleTier",
    "ToolCall",
    "ToolOutputSanitizer",
    "ToolSanitizeResult",
    "ToolSensitivity",
    "ToolTarget",
    "ToxicFlow",
    "TrajectoryTracker",
    "TyposquatDetector",
    "TyposquatFinding",
    "UndeclaredImport",
    "ValidationLevel",
    "ValidationResult",
    "Verdict",
    "VulnerabilityAdvisory",
    "Witness",
    "WitnessRecorder",
    "classify_taint_source",
    "emit_contract",
    "emit_contracts",
    "scoped_factory",
]

# Freelance + Marketing/E-marketing runtime modules (Phase 1) - re-exported.
__all__ += [
    "attribution_model",
    "billing_ledger",
    "crm_manager",
    "drip_engine",
    "experiment_tracker",
    "feature_flags",
    "funnel_tracker",
    "lead_scorer",
    "marketing_compliance",
    "pipeline_analytics",
    "post_queue",
    "pricing_calculator",
]
