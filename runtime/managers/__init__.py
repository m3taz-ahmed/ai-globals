"""Manager submodules for the AI Global OS kernel.

Each manager encapsulates a single responsibility cluster:
- PolicyManager: policy + guardian + approval cache
- WorkflowManager: workflow + saga orchestration
- AgentManager: agent pool + spawn + delegate
- ChatManager: chat session management
"""

from .agent_manager import AgentManager
from .chat_manager import ChatManager
from .policy_manager import PolicyManager
from .workflow_manager import WorkflowManager

__all__ = ["AgentManager", "ChatManager", "PolicyManager", "WorkflowManager"]
