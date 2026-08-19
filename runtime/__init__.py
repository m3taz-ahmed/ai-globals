"""aiZee runtime kernel."""

import config

__version__ = config.VERSION

# Re-export new governance modules for convenient access.
from runtime.agent_discovery import AgentDiscovery as AgentDiscovery
from runtime.approval_service import ApprovalService as ApprovalService
from runtime.closure_evaluator import ClosureEvaluator as ClosureEvaluator
from runtime.closure_evaluator import GuardianClosureEvaluator as GuardianClosureEvaluator
from runtime.context_manager import ContextManager as ContextManager
from runtime.loop_detector import LoopDetector as LoopDetector
from runtime.mcp_firewall import McpFirewall as McpFirewall
from runtime.prompt_gate import PromptGate as PromptGate
from runtime.reasoning_graph import ReasoningGraph as ReasoningGraph
from runtime.trajectory import TrajectoryTracker as TrajectoryTracker

__all__ = [
    "AgentDiscovery",
    "ApprovalService",
    "ClosureEvaluator",
    "ContextManager",
    "GuardianClosureEvaluator",
    "LoopDetector",
    "McpFirewall",
    "PromptGate",
    "ReasoningGraph",
    "TrajectoryTracker",
]
