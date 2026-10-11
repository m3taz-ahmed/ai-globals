"""aiZee runtime kernel.

This package re-exports ~250 symbols for convenient access. The exports are
resolved lazily via PEP 562 (``__getattr__``): ``from runtime import X`` and
``runtime.X`` attribute access import the backing submodule on first use and
cache it in ``globals()``. ``import runtime`` alone therefore stays cheap;
previously it eagerly imported every governance module (~0.5 s + 120
submodules) for every CLI invocation and test worker.

Type checkers still see the full import set under ``if TYPE_CHECKING:`` so
``from runtime import Kernel`` resolves to the real type. ``dir(runtime)``
advertises the full export table; ``hasattr``/``getattr`` semantics are
unchanged. Submodules are also reachable as attributes (``runtime.budget``)
via the same lazy path. ``importlib.reload(runtime)`` resets the cache.

Not all exports are wired into the production kernel pipeline - see the
doctor wiring table (``aizee doctor``) for call-site truth.
"""

from __future__ import annotations

import importlib
import importlib.util
from typing import TYPE_CHECKING, Any

import config

__version__ = config.VERSION

if TYPE_CHECKING:
    # Static export surface for type checkers only - zero runtime cost.
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
    from runtime.c4_docs import C4Generator as C4Generator
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
    from runtime.harness_exporter import InstallResult as InstallResult
    from runtime.harness_exporter import harnesses as harnesses
    from runtime.harness_exporter import install_skill as install_skill
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
    from runtime.policy_lint import LintFinding as LintFinding
    from runtime.policy_lint import LintSeverity as LintSeverity
    from runtime.policy_lint import PolicyLinter as PolicyLinter
    from runtime.post_queue import PostQueue as PostQueue
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
    from runtime.security_scanner import ScanFinding as ScanFinding
    from runtime.security_scanner import ScanReport as ScanReport
    from runtime.security_scanner import ScanSeverity as ScanSeverity
    from runtime.security_scanner import SecurityScanner as SecurityScanner
    from runtime.security_scanner import scan_project as scan_project
    from runtime.skill_lifecycle import LedgerEvent as LedgerEvent
    from runtime.skill_lifecycle import SkillLifecycleManager as SkillLifecycleManager
    from runtime.skill_lifecycle import SkillMember as SkillMember
    from runtime.skill_lifecycle import evaluate as evaluate_skill_lifecycle
    from runtime.skill_routing import PersonaDetectionResult as PersonaDetectionResult
    from runtime.skill_routing import PersonaDetectorV2 as PersonaDetectorV2
    from runtime.skill_routing import SkillRouter as SkillRouter
    from runtime.skill_scanner import Baseline as Baseline
    from runtime.skill_scanner import Finding as SkillFinding
    from runtime.skill_scanner import PatternSeverity as ScanPatternSeverity
    from runtime.skill_scanner import ScanResult as ScanResult
    from runtime.skill_scanner import ScanRiskLevel as ScanRiskLevel
    from runtime.skill_scanner import SkillScanner as SkillScanner
    from runtime.skill_validator import SkillReport as SkillReport
    from runtime.skill_validator import validate_skills as validate_skills
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
    from runtime.task_contract import ContractTask as ContractTask
    from runtime.task_contract import TaskContractError as TaskContractError
    from runtime.task_contract import TaskContractManager as TaskContractManager
    from runtime.task_contract import TaskPlan as TaskPlan
    from runtime.task_contract import classify_prompt as classify_prompt
    from runtime.tool_output_sanitizer import ToolOutputSanitizer as ToolOutputSanitizer
    from runtime.tool_output_sanitizer import ToolSanitizeResult as ToolSanitizeResult
    from runtime.trajectory import FailureCategory as FailureCategory
    from runtime.trajectory import TrajectoryTracker as TrajectoryTracker
    from runtime.ui_a11y_checker import A11yChecker as A11yChecker
    from runtime.ui_a11y_checker import A11yFinding as A11yFinding
    from runtime.ui_a11y_checker import A11ySeverity as A11ySeverity

# (export name, submodule, real attribute) - mirrors the TYPE_CHECKING block.
_LAZY_TABLE: tuple[tuple[str, str, str], ...] = (
    ("AgentAction", "runtime.agent_baseline", "AgentAction"),
    ("AgentBaseline", "runtime.agent_baseline", "AgentBaseline"),
    ("AnomalyAlert", "runtime.agent_baseline", "AnomalyAlert"),
    ("AnomalyType", "runtime.agent_baseline", "AnomalyType"),
    ("BaselineRegistry", "runtime.agent_baseline", "BaselineRegistry"),
    ("AgentCatalog", "runtime.agent_catalog", "AgentCatalog"),
    ("CatalogAgent", "runtime.agent_catalog", "CatalogAgent"),
    ("CatalogFlow", "runtime.agent_catalog", "CatalogFlow"),
    ("CatalogModel", "runtime.agent_catalog", "CatalogModel"),
    ("CbConfig", "runtime.agent_circuit_breaker", "CbConfig"),
    ("CbState", "runtime.agent_circuit_breaker", "CbState"),
    ("SemanticCircuitBreaker", "runtime.agent_circuit_breaker", "SemanticCircuitBreaker"),
    ("AgentDiscovery", "runtime.agent_discovery", "AgentDiscovery"),
    ("AgentGateway", "runtime.agent_gateway", "AgentGateway"),
    ("GuardrailContext", "runtime.agent_gateway", "GuardrailContext"),
    ("GuardrailPhase", "runtime.agent_gateway", "GuardrailPhase"),
    ("GuardrailResult", "runtime.agent_gateway", "GuardrailResult"),
    ("Verdict", "runtime.agent_gateway", "Verdict"),
    ("AgentSliCollector", "runtime.agent_sli", "AgentSliCollector"),
    ("SliResult", "runtime.agent_sli", "SliResult"),
    ("SliStatus", "runtime.agent_sli", "SliStatus"),
    ("TaskRecord", "runtime.agent_sli", "TaskRecord"),
    ("DiscordChannel", "runtime.approval_channels", "DiscordChannel"),
    ("EmailChannel", "runtime.approval_channels", "EmailChannel"),
    ("SlackChannel", "runtime.approval_channels", "SlackChannel"),
    ("ApprovalService", "runtime.approval_service", "ApprovalService"),
    ("ApprovalSlaManager", "runtime.approval_sla", "ApprovalSlaManager"),
    ("DecisionDelta", "runtime.approval_sla", "DecisionDelta"),
    ("SlaAction", "runtime.approval_sla", "SlaAction"),
    ("SlaPolicy", "runtime.approval_sla", "SlaPolicy"),
    ("AuditSigner", "runtime.audit_signing", "AuditSigner"),
    ("SignatureResult", "runtime.audit_signing", "SignatureResult"),
    ("SignatureScheme", "runtime.audit_signing", "SignatureScheme"),
    ("BladeFinding", "runtime.blade_template_linter", "BladeFinding"),
    ("BladeSeverity", "runtime.blade_template_linter", "BladeSeverity"),
    ("BladeTemplateLinter", "runtime.blade_template_linter", "BladeTemplateLinter"),
    ("BlastEdge", "runtime.blast_radius", "BlastEdge"),
    ("BlastNode", "runtime.blast_radius", "BlastNode"),
    ("BlastPath", "runtime.blast_radius", "BlastPath"),
    ("BlastRadiusGraph", "runtime.blast_radius", "BlastRadiusGraph"),
    ("ImpactLevel", "runtime.blast_radius", "ImpactLevel"),
    ("NodeType", "runtime.blast_radius", "NodeType"),
    ("BurnForecast", "runtime.budget_advanced", "BurnForecast"),
    ("BurnForecaster", "runtime.budget_advanced", "BurnForecaster"),
    ("ModelCostOptimizer", "runtime.budget_advanced", "ModelCostOptimizer"),
    ("ReserveHold", "runtime.budget_advanced", "ReserveHold"),
    ("ReserveSettleProtocol", "runtime.budget_advanced", "ReserveSettleProtocol"),
    ("ShadowModeTracker", "runtime.budget_advanced", "ShadowModeTracker"),
    ("SpendAnomaly", "runtime.budget_advanced", "SpendAnomaly"),
    ("SpendAnomalyDetector", "runtime.budget_advanced", "SpendAnomalyDetector"),
    ("ThrottleConfig", "runtime.budget_advanced", "ThrottleConfig"),
    ("ThrottleTier", "runtime.budget_advanced", "ThrottleTier"),
    ("C4Generator", "runtime.c4_docs", "C4Generator"),
    ("ClosureEvaluator", "runtime.closure_evaluator", "ClosureEvaluator"),
    ("GuardianClosureEvaluator", "runtime.closure_evaluator", "GuardianClosureEvaluator"),
    ("Command", "runtime.commands", "Command"),
    ("CommandBus", "runtime.commands", "CommandBus"),
    ("CommandResult", "runtime.commands", "CommandResult"),
    ("CommandStatus", "runtime.commands", "CommandStatus"),
    ("CompositeIdentity", "runtime.composite_identity", "CompositeIdentity"),
    ("CompositeIdentityRegistry", "runtime.composite_identity", "CompositeIdentityRegistry"),
    ("Principal", "runtime.composite_identity", "Principal"),
    ("PrincipalRole", "runtime.composite_identity", "PrincipalRole"),
    ("ConfidenceGate", "runtime.confidence_gate", "ConfidenceGate"),
    ("ConfidenceLevel", "runtime.confidence_gate", "ConfidenceLevel"),
    ("ConfidenceVerdict", "runtime.confidence_gate", "ConfidenceVerdict"),
    ("Evidence", "runtime.confidence_gate", "Evidence"),
    ("ContextManager", "runtime.context_manager", "ContextManager"),
    ("ContractArtifact", "runtime.contract_emitter", "ContractArtifact"),
    ("emit_contract", "runtime.contract_emitter", "emit_contract"),
    ("emit_contracts", "runtime.contract_emitter", "emit_contracts"),
    ("CostAnomaly", "runtime.cost_attribution", "CostAnomaly"),
    ("CostAnomalyType", "runtime.cost_attribution", "CostAnomalyType"),
    ("CostAttribution", "runtime.cost_attribution", "CostAttribution"),
    ("CostRecord", "runtime.cost_attribution", "CostRecord"),
    ("CrossToolTaintTracker", "runtime.cross_tool_taint", "CrossToolTaintTracker"),
    ("DataClassification", "runtime.cross_tool_taint", "DataClassification"),
    ("ToolCall", "runtime.cross_tool_taint", "ToolCall"),
    ("ToolSensitivity", "runtime.cross_tool_taint", "ToolSensitivity"),
    ("ToxicFlow", "runtime.cross_tool_taint", "ToxicFlow"),
    ("MigrationFinding", "runtime.db_migration_safety", "MigrationFinding"),
    ("MigrationSafetyChecker", "runtime.db_migration_safety", "MigrationSafetyChecker"),
    ("MigrationSeverity", "runtime.db_migration_safety", "MigrationSeverity"),
    ("DefenseResult", "runtime.defensive_injection", "DefenseResult"),
    ("DefenseStrategy", "runtime.defensive_injection", "DefenseStrategy"),
    ("DefensiveInjector", "runtime.defensive_injection", "DefensiveInjector"),
    ("BrandDesignSystem", "runtime.design_library", "BrandDesignSystem"),
    ("DesignLibrary", "runtime.design_library", "DesignLibrary"),
    ("DesignLibraryError", "runtime.design_library", "DesignLibraryError"),
    ("DesignSection", "runtime.design_library", "DesignSection"),
    ("FusionResult", "runtime.design_library", "FusionResult"),
    ("ProjectType", "runtime.design_library", "ProjectType"),
    ("DesignSlopError", "runtime.design_slop_verifier", "DesignSlopError"),
    ("DesignSlopVerifier", "runtime.design_slop_verifier", "DesignSlopVerifier"),
    ("SlopCategory", "runtime.design_slop_verifier", "SlopCategory"),
    ("SlopFinding", "runtime.design_slop_verifier", "SlopFinding"),
    ("SlopSeverity", "runtime.design_slop_verifier", "SlopSeverity"),
    ("SlopVerdict", "runtime.design_slop_verifier", "SlopVerdict"),
    ("DualLLMError", "runtime.dual_llm", "DualLLMError"),
    ("DualLLMOrchestrator", "runtime.dual_llm", "DualLLMOrchestrator"),
    ("DualLLMResult", "runtime.dual_llm", "DualLLMResult"),
    ("LLMRole", "runtime.dual_llm", "LLMRole"),
    ("DurableExecutor", "runtime.durable", "DurableExecutor"),
    ("DurableStep", "runtime.durable", "DurableStep"),
    ("DurableWorkflow", "runtime.durable", "DurableWorkflow"),
    ("StepStatus", "runtime.durable", "StepStatus"),
    ("FairnessDetector", "runtime.fairness_detector", "FairnessDetector"),
    ("FairnessFinding", "runtime.fairness_detector", "FairnessFinding"),
    ("FairnessReport", "runtime.fairness_detector", "FairnessReport"),
    ("FairnessStrategy", "runtime.fairness_detector", "FairnessStrategy"),
    ("ProtectedAttribute", "runtime.fairness_detector", "ProtectedAttribute"),
    ("AccessFinding", "runtime.filament_access_auditor", "AccessFinding"),
    ("AccessSeverity", "runtime.filament_access_auditor", "AccessSeverity"),
    ("FilamentAccessAuditor", "runtime.filament_access_auditor", "FilamentAccessAuditor"),
    ("HallucinationDetector", "runtime.hallucination_detector", "HallucinationDetector"),
    ("HallucinationFinding", "runtime.hallucination_detector", "HallucinationFinding"),
    ("HallucinationSeverity", "runtime.hallucination_detector", "HallucinationSeverity"),
    ("InstallResult", "runtime.harness_exporter", "InstallResult"),
    ("harnesses", "runtime.harness_exporter", "harnesses"),
    ("install_skill", "runtime.harness_exporter", "install_skill"),
    ("HookContext", "runtime.hook_lifecycle", "HookContext"),
    ("HookPhase", "runtime.hook_lifecycle", "HookPhase"),
    ("HookRegistry", "runtime.hook_lifecycle", "HookRegistry"),
    ("InjectionDetector", "runtime.injection_detector", "InjectionDetector"),
    ("InjectionSeverity", "runtime.injection_detector", "InjectionSeverity"),
    ("InjectionSignal", "runtime.injection_detector", "InjectionSignal"),
    ("InjectionTechnique", "runtime.injection_detector", "InjectionTechnique"),
    ("InjectionVerdict", "runtime.injection_detector", "InjectionVerdict"),
    ("Kernel", "runtime.kernel", "Kernel"),
    ("KernelBuilder", "runtime.kernel", "KernelBuilder"),
    ("LaravelFinding", "runtime.laravel_policy_linter", "LaravelFinding"),
    ("LaravelLintSeverity", "runtime.laravel_policy_linter", "LaravelLintSeverity"),
    ("LaravelPolicyLinter", "runtime.laravel_policy_linter", "LaravelPolicyLinter"),
    ("Layer", "runtime.layers", "Layer"),
    ("LayerManifest", "runtime.layers", "LayerManifest"),
    ("LearningLoop", "runtime.learning_loop", "LearningLoop"),
    ("AttestationEnvelope", "runtime.llm_attestation", "AttestationEnvelope"),
    ("AttestationStatement", "runtime.llm_attestation", "AttestationStatement"),
    ("AttestationType", "runtime.llm_attestation", "AttestationType"),
    ("LlmAttestor", "runtime.llm_attestation", "LlmAttestor"),
    ("PrivacyMode", "runtime.llm_attestation", "PrivacyMode"),
    ("LoopDetector", "runtime.loop_detector", "LoopDetector"),
    ("McpAuditorFinding", "runtime.mcp_auditor", "Finding"),
    ("FindingSeverity", "runtime.mcp_auditor", "FindingSeverity"),
    ("McpAuditor", "runtime.mcp_auditor", "McpAuditor"),
    ("McpFirewall", "runtime.mcp_firewall", "McpFirewall"),
    ("ManifestFingerprint", "runtime.mcp_manifest_lock", "ManifestFingerprint"),
    ("ManifestLock", "runtime.mcp_manifest_lock", "ManifestLock"),
    ("Grant", "runtime.mcp_securable", "Grant"),
    ("McpPermission", "runtime.mcp_securable", "McpPermission"),
    ("McpSecurableRegistry", "runtime.mcp_securable", "McpSecurableRegistry"),
    ("McpServer", "runtime.mcp_securable", "McpServer"),
    ("ActionContext", "runtime.middleware", "ActionContext"),
    ("MiddlewarePipeline", "runtime.middleware", "MiddlewarePipeline"),
    ("MiddlewareResult", "runtime.middleware", "MiddlewareResult"),
    ("MobileAuditConfig", "runtime.mobile_patterns", "MobileAuditConfig"),
    ("MobilePattern", "runtime.mobile_patterns", "MobilePattern"),
    ("MobilePatternAuditor", "runtime.mobile_patterns", "MobilePatternAuditor"),
    ("MobilePlatform", "runtime.mobile_patterns", "MobilePlatform"),
    ("PatternResult", "runtime.mobile_patterns", "PatternResult"),
    ("PatternSeverity", "runtime.mobile_patterns", "PatternSeverity"),
    ("ModelCapability", "runtime.model_router", "ModelCapability"),
    ("ModelInfo", "runtime.model_router", "ModelInfo"),
    ("ModelRouter", "runtime.model_router", "ModelRouter"),
    ("RouteDecision", "runtime.model_router", "RouteDecision"),
    ("RouteTier", "runtime.model_router", "RouteTier"),
    ("Finding", "runtime.plan_diff_validator", "Finding"),
    ("PlanDiffValidator", "runtime.plan_diff_validator", "PlanDiffValidator"),
    ("ValidationLevel", "runtime.plan_diff_validator", "ValidationLevel"),
    ("ValidationResult", "runtime.plan_diff_validator", "ValidationResult"),
    ("LintFinding", "runtime.policy_lint", "LintFinding"),
    ("LintSeverity", "runtime.policy_lint", "LintSeverity"),
    ("PolicyLinter", "runtime.policy_lint", "PolicyLinter"),
    ("PostQueue", "runtime.post_queue", "PostQueue"),
    ("PromptGate", "runtime.prompt_gate", "PromptGate"),
    ("DetectionLevel", "runtime.prompt_injection_detector", "DetectionLevel"),
    ("PromptInjectionDetector", "runtime.prompt_injection_detector", "PromptInjectionDetector"),
    ("SemanticDetectionResult", "runtime.prompt_injection_detector", "SemanticDetectionResult"),
    ("Bounder", "runtime.quality", "Bounder"),
    ("CostProvider", "runtime.quality", "CostProvider"),
    ("FixedRateCostProvider", "runtime.quality", "FixedRateCostProvider"),
    ("LazyImport", "runtime.quality", "LazyImport"),
    ("OutputEnvelope", "runtime.quality", "OutputEnvelope"),
    ("ReflexionEntry", "runtime.quality", "ReflexionEntry"),
    ("ReflexionLog", "runtime.quality", "ReflexionLog"),
    ("Witness", "runtime.quality", "Witness"),
    ("WitnessRecorder", "runtime.quality", "WitnessRecorder"),
    ("ReasoningGraph", "runtime.reasoning_graph", "ReasoningGraph"),
    ("MaterializationResult", "runtime.rules_materializer", "MaterializationResult"),
    ("RuleEntry", "runtime.rules_materializer", "RuleEntry"),
    ("RulesMaterializer", "runtime.rules_materializer", "RulesMaterializer"),
    ("ScopeLevel", "runtime.rules_materializer", "ScopeLevel"),
    ("ToolTarget", "runtime.rules_materializer", "ToolTarget"),
    ("ScopedManager", "runtime.scoped_manager", "ScopedManager"),
    ("ScopedRegistry", "runtime.scoped_manager", "ScopedRegistry"),
    ("scoped_factory", "runtime.scoped_manager", "scoped_factory"),
    ("ScanFinding", "runtime.security_scanner", "ScanFinding"),
    ("ScanReport", "runtime.security_scanner", "ScanReport"),
    ("ScanSeverity", "runtime.security_scanner", "ScanSeverity"),
    ("SecurityScanner", "runtime.security_scanner", "SecurityScanner"),
    ("scan_project", "runtime.security_scanner", "scan_project"),
    ("LedgerEvent", "runtime.skill_lifecycle", "LedgerEvent"),
    ("SkillLifecycleManager", "runtime.skill_lifecycle", "SkillLifecycleManager"),
    ("SkillMember", "runtime.skill_lifecycle", "SkillMember"),
    ("evaluate_skill_lifecycle", "runtime.skill_lifecycle", "evaluate"),
    ("PersonaDetectionResult", "runtime.skill_routing", "PersonaDetectionResult"),
    ("PersonaDetectorV2", "runtime.skill_routing", "PersonaDetectorV2"),
    ("SkillRouter", "runtime.skill_routing", "SkillRouter"),
    ("Baseline", "runtime.skill_scanner", "Baseline"),
    ("SkillFinding", "runtime.skill_scanner", "Finding"),
    ("ScanPatternSeverity", "runtime.skill_scanner", "PatternSeverity"),
    ("ScanResult", "runtime.skill_scanner", "ScanResult"),
    ("ScanRiskLevel", "runtime.skill_scanner", "ScanRiskLevel"),
    ("SkillScanner", "runtime.skill_scanner", "SkillScanner"),
    ("SkillReport", "runtime.skill_validator", "SkillReport"),
    ("validate_skills", "runtime.skill_validator", "validate_skills"),
    ("StaleApiDetector", "runtime.stale_api_detector", "StaleApiDetector"),
    ("StaleApiFinding", "runtime.stale_api_detector", "StaleApiFinding"),
    ("StaleApiSeverity", "runtime.stale_api_detector", "StaleApiSeverity"),
    ("DeclaredDependency", "runtime.supply_chain_guard", "DeclaredDependency"),
    ("DependencyEcosystem", "runtime.supply_chain_guard", "DependencyEcosystem"),
    ("OsvDevClient", "runtime.supply_chain_guard", "OsvDevClient"),
    ("SupplyChainGuard", "runtime.supply_chain_guard", "SupplyChainGuard"),
    ("TyposquatDetector", "runtime.supply_chain_guard", "TyposquatDetector"),
    ("TyposquatFinding", "runtime.supply_chain_guard", "TyposquatFinding"),
    ("UndeclaredImport", "runtime.supply_chain_guard", "UndeclaredImport"),
    ("VulnerabilityAdvisory", "runtime.supply_chain_guard", "VulnerabilityAdvisory"),
    ("TaintError", "runtime.taint", "TaintError"),
    ("TaintLabel", "runtime.taint", "TaintLabel"),
    ("TaintTracker", "runtime.taint", "TaintTracker"),
    ("classify_taint_source", "runtime.taint", "classify_source"),
    ("ContractTask", "runtime.task_contract", "ContractTask"),
    ("TaskContractError", "runtime.task_contract", "TaskContractError"),
    ("TaskContractManager", "runtime.task_contract", "TaskContractManager"),
    ("TaskPlan", "runtime.task_contract", "TaskPlan"),
    ("classify_prompt", "runtime.task_contract", "classify_prompt"),
    ("ToolOutputSanitizer", "runtime.tool_output_sanitizer", "ToolOutputSanitizer"),
    ("ToolSanitizeResult", "runtime.tool_output_sanitizer", "ToolSanitizeResult"),
    ("FailureCategory", "runtime.trajectory", "FailureCategory"),
    ("TrajectoryTracker", "runtime.trajectory", "TrajectoryTracker"),
    ("A11yChecker", "runtime.ui_a11y_checker", "A11yChecker"),
    ("A11yFinding", "runtime.ui_a11y_checker", "A11yFinding"),
    ("A11ySeverity", "runtime.ui_a11y_checker", "A11ySeverity")
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {e: (m, a) for e, m, a in _LAZY_TABLE}


def __getattr__(name: str) -> Any:
    """Resolve a lazy export, or fall back to a ``runtime.<name>`` submodule."""
    target = _LAZY_EXPORTS.get(name)
    if target is not None:
        mod_name, attr = target
        mod = importlib.import_module(mod_name)
        value = getattr(mod, attr)
    else:
        fqn = f"{__name__}.{name}"
        if importlib.util.find_spec(fqn) is None:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
        value = importlib.import_module(fqn)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))


__all__ = [
    "A11yChecker",
    "A11yFinding",
    "A11ySeverity",
    "AccessFinding",
    "AccessSeverity",
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
    "BladeFinding",
    "BladeSeverity",
    "BladeTemplateLinter",
    "BlastEdge",
    "BlastNode",
    "BlastPath",
    "BlastRadiusGraph",
    "Bounder",
    "BrandDesignSystem",
    "BurnForecast",
    "BurnForecaster",
    "C4Generator",
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
    "ContractTask",
    "CostAnomaly",
    "CostAnomalyType",
    "CostAttribution",
    "CostProvider",
    "CostRecord",
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
    "FilamentAccessAuditor",
    "Finding",
    "FindingSeverity",
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
    "InstallResult",
    "Kernel",
    "KernelBuilder",
    "LLMRole",
    "LaravelFinding",
    "LaravelLintSeverity",
    "LaravelPolicyLinter",
    "Layer",
    "LayerManifest",
    "LazyImport",
    "LearningLoop",
    "LedgerEvent",
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
    "MigrationFinding",
    "MigrationSafetyChecker",
    "MigrationSeverity",
    "MobileAuditConfig",
    "MobilePattern",
    "MobilePatternAuditor",
    "MobilePlatform",
    "ModelCapability",
    "ModelCostOptimizer",
    "ModelInfo",
    "ModelRouter",
    "NodeType",
    "OsvDevClient",
    "OutputEnvelope",
    "PatternResult",
    "PatternSeverity",
    "PersonaDetectionResult",
    "PersonaDetectorV2",
    "PlanDiffValidator",
    "PolicyLinter",
    "PostQueue",
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
    "ScanFinding",
    "ScanPatternSeverity",
    "ScanReport",
    "ScanResult",
    "ScanRiskLevel",
    "ScanSeverity",
    "ScopeLevel",
    "ScopedManager",
    "ScopedRegistry",
    "SecurityScanner",
    "SemanticCircuitBreaker",
    "SemanticDetectionResult",
    "ShadowModeTracker",
    "SignatureResult",
    "SignatureScheme",
    "SkillFinding",
    "SkillLifecycleManager",
    "SkillMember",
    "SkillReport",
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
    "TaskContractError",
    "TaskContractManager",
    "TaskPlan",
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
    "classify_prompt",
    "classify_taint_source",
    "emit_contract",
    "emit_contracts",
    "evaluate_skill_lifecycle",
    "harnesses",
    "install_skill",
    "scan_project",
    "scoped_factory",
    "validate_skills",
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
