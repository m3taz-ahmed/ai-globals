"""aiZee runtime kernel."""

from __future__ import annotations

import config

__version__ = config.VERSION

# Re-export new governance modules for convenient access.
from runtime.agent_discovery import AgentDiscovery as AgentDiscovery
from runtime.approval_service import ApprovalService as ApprovalService
from runtime.closure_evaluator import ClosureEvaluator as ClosureEvaluator
from runtime.closure_evaluator import GuardianClosureEvaluator as GuardianClosureEvaluator
from runtime.commands import Command as Command
from runtime.commands import CommandBus as CommandBus
from runtime.commands import CommandResult as CommandResult
from runtime.commands import CommandStatus as CommandStatus
from runtime.context_manager import ContextManager as ContextManager
from runtime.contract_emitter import ContractArtifact as ContractArtifact
from runtime.contract_emitter import emit_contract as emit_contract
from runtime.contract_emitter import emit_contracts as emit_contracts
from runtime.hook_lifecycle import HookContext as HookContext
from runtime.hook_lifecycle import HookPhase as HookPhase
from runtime.hook_lifecycle import HookRegistry as HookRegistry
from runtime.layers import Layer as Layer
from runtime.layers import LayerManifest as LayerManifest
from runtime.loop_detector import LoopDetector as LoopDetector
from runtime.mcp_firewall import McpFirewall as McpFirewall
from runtime.prompt_gate import PromptGate as PromptGate
from runtime.reasoning_graph import ReasoningGraph as ReasoningGraph
from runtime.scoped_manager import ScopedManager as ScopedManager
from runtime.scoped_manager import ScopedRegistry as ScopedRegistry
from runtime.scoped_manager import scoped_factory as scoped_factory
from runtime.trajectory import TrajectoryTracker as TrajectoryTracker

__all__ = [
    "AgentDiscovery",
    "ApprovalService",
    "ClosureEvaluator",
    "Command",
    "CommandBus",
    "CommandResult",
    "CommandStatus",
    "ContextManager",
    "ContractArtifact",
    "GuardianClosureEvaluator",
    "HookContext",
    "HookPhase",
    "HookRegistry",
    "Layer",
    "LayerManifest",
    "LoopDetector",
    "McpFirewall",
    "PromptGate",
    "ReasoningGraph",
    "ScopedManager",
    "ScopedRegistry",
    "TrajectoryTracker",
    "emit_contract",
    "emit_contracts",
    "scoped_factory",
]
