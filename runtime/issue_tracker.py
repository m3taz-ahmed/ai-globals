"""Issue tracker integration (Linear / Jira / Notion) for AI Global OS.

Provides automated task management by syncing issues from external trackers and
pushing OS-generated tasks back to them. Uses stdlib only (urllib, json,
dataclasses, abc). API keys are read from environment variables — never
hardcoded.
"""

from __future__ import annotations

import contextlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

#: Valid tracker types supported by the integration.
SUPPORTED_TRACKERS: tuple[str, ...] = ("linear", "jira", "notion")

#: Default HTTP timeout (seconds) for all outbound requests.
_DEFAULT_TIMEOUT = 30.0


@dataclass
class IssueTrackerConfig:
    """Configuration for a single tracker connection.

    ``api_key_env`` names the environment variable that holds the API key. The
    key itself is resolved lazily via :meth:`resolve_api_key` so that it is
    never stored on the dataclass and never logged.
    """

    tracker_type: str
    project_id: str
    api_key_env: str
    base_url: str | None = None
    # Optional explicit key — mainly for tests. When set it overrides the env
    # var lookup. Production code should leave this ``None``.
    api_key: str | None = None

    def __post_init__(self) -> None:
        if self.tracker_type not in SUPPORTED_TRACKERS:
            raise ValueError(
                f"Unsupported tracker type: {self.tracker_type!r}. "
                f"Must be one of {SUPPORTED_TRACKERS}."
            )
        if not self.project_id:
            raise ValueError("project_id is required")
        if not self.api_key_env:
            raise ValueError("api_key_env is required")

    def resolve_api_key(self) -> str | None:
        """Return the API key from the configured env var or explicit override."""
        if self.api_key is not None:
            return self.api_key
        return os.environ.get(self.api_key_env)


@dataclass
class Issue:
    """Normalized representation of an issue across all trackers."""

    id: str
    title: str
    description: str = ""
    status: str = "open"
    priority: str = "medium"
    assignee: str | None = None
    labels: list[str] = field(default_factory=list)
    created_at: str = ""
    tracker_type: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assignee": self.assignee,
            "labels": list(self.labels),
            "created_at": self.created_at,
            "tracker_type": self.tracker_type,
            "url": self.url,
        }


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


class IssueTrackerError(Exception):
    """Raised when a tracker API call fails."""


def _http_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Perform an HTTP request and return parsed JSON.

    Raises :class:`IssueTrackerError` on network or HTTP failures.
    """
    data: bytes | None = None
    req_headers: dict[str, str] = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        with contextlib.suppress(Exception):
            detail = exc.read().decode("utf-8", errors="replace")
        raise IssueTrackerError(
            f"HTTP {exc.code} {exc.reason} from {url}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise IssueTrackerError(f"Network error calling {url}: {exc.reason}") from exc
    if not raw:
        return {}
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise IssueTrackerError(f"Invalid JSON response from {url}") from exc
    if not isinstance(parsed, dict):
        raise IssueTrackerError(f"Expected JSON object from {url}, got {type(parsed).__name__}")
    return parsed


# ---------------------------------------------------------------------------
# Abstract base client
# ---------------------------------------------------------------------------


class IssueTrackerClient(ABC):
    """Abstract base class for issue tracker clients."""

    #: Subclasses set this to their tracker type (linear/jira/notion).
    tracker_type: ClassVar[str] = ""

    def __init__(self, config: IssueTrackerConfig) -> None:
        if config.tracker_type != self.tracker_type:
            raise ValueError(
                f"Config tracker_type {config.tracker_type!r} does not match "
                f"client {self.tracker_type!r}"
            )
        self.config = config

    def _require_api_key(self) -> str:
        key = self.config.resolve_api_key()
        if not key:
            raise IssueTrackerError(
                f"Missing API key: env var {self.config.api_key_env!r} is not set"
            )
        return key

    @abstractmethod
    def list_issues(self) -> list[Issue]:
        """Return all issues for the configured project."""

    @abstractmethod
    def get_issue(self, issue_id: str) -> Issue:
        """Return a single issue by id."""

    @abstractmethod
    def create_issue(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> Issue:
        """Create a new issue and return it."""

    @abstractmethod
    def update_issue(
        self,
        issue_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> Issue:
        """Update an existing issue and return the updated version."""

    @abstractmethod
    def close_issue(self, issue_id: str) -> Issue:
        """Close an issue and return it."""


# ---------------------------------------------------------------------------
# Linear client
# ---------------------------------------------------------------------------


class LinearClient(IssueTrackerClient):
    """Linear integration via the HTTP GraphQL API."""

    tracker_type: ClassVar[str] = "linear"
    _default_base_url: ClassVar[str] = "https://api.linear.app/graphql"

    def __init__(self, config: IssueTrackerConfig) -> None:
        super().__init__(config)
        self.base_url = config.base_url or self._default_base_url

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self._require_api_key()}

    def _gql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        resp = _http_request(self.base_url, method="POST", headers=self._headers(), body=payload)
        if resp.get("errors"):
            raise IssueTrackerError(f"Linear GraphQL errors: {resp['errors']}")
        data: dict[str, Any] = resp.get("data", {})
        return data

    @staticmethod
    def _parse_issue(node: dict[str, Any]) -> Issue:
        state = node.get("state", {}) or {}
        assignee = node.get("assignee", {}) or {}
        return Issue(
            id=node.get("id", ""),
            title=node.get("title", ""),
            description=node.get("description", "") or "",
            status=state.get("name", "open"),
            priority=str(node.get("priority", 2)),
            assignee=assignee.get("name") or assignee.get("email"),
            labels=[label.get("name", "") for label in node.get("labels", {}).get("nodes", []) if label.get("name")],
            created_at=node.get("createdAt", ""),
            tracker_type="linear",
            url=node.get("url", ""),
        )

    def list_issues(self) -> list[Issue]:
        data = self._gql(
            """
            query($projectId: String!) {
              project(id: $projectId) {
                issues { nodes { id title description state { name } priority
                  assignee { name email } labels { nodes { name } } createdAt url } }
              }
            }
            """,
            {"projectId": self.config.project_id},
        )
        project = data.get("project", {}) or {}
        nodes = project.get("issues", {}).get("nodes", [])
        return [self._parse_issue(n) for n in nodes]

    def get_issue(self, issue_id: str) -> Issue:
        data = self._gql(
            """
            query($id: String!) {
              issue(id: $id) {
                id title description state { name } priority
                assignee { name email } labels { nodes { name } } createdAt url
              }
            }
            """,
            {"id": issue_id},
        )
        node = data.get("issue")
        if not node:
            raise IssueTrackerError(f"Linear issue not found: {issue_id}")
        return self._parse_issue(node)

    def create_issue(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> Issue:
        variables: dict[str, Any] = {
            "projectId": self.config.project_id,
            "title": title,
            "description": description,
        }
        if assignee:
            variables["assigneeId"] = assignee
        data = self._gql(
            """
            mutation($projectId: String!, $title: String!, $description: String!, $assigneeId: String) {
              issueCreate(input: { projectId: $projectId, title: $title,
                description: $description, assigneeId: $assigneeId }) {
                issue { id title description state { name } priority
                  assignee { name email } labels { nodes { name } } createdAt url }
              }
            }
            """,
            variables,
        )
        node = data.get("issueCreate", {}).get("issue")
        if not node:
            raise IssueTrackerError("Linear create_issue returned no issue")
        return self._parse_issue(node)

    def update_issue(
        self,
        issue_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> Issue:
        input_fields: dict[str, Any] = {}
        if title is not None:
            input_fields["title"] = title
        if description is not None:
            input_fields["description"] = description
        if assignee is not None:
            input_fields["assigneeId"] = assignee
        variables = {"id": issue_id, "input": input_fields}
        data = self._gql(
            """
            mutation($id: String!, $input: IssueUpdateInput!) {
              issueUpdate(id: $id, input: $input) {
                issue { id title description state { name } priority
                  assignee { name email } labels { nodes { name } } createdAt url }
              }
            }
            """,
            variables,
        )
        node = data.get("issueUpdate", {}).get("issue")
        if not node:
            raise IssueTrackerError(f"Linear update_issue failed for {issue_id}")
        return self._parse_issue(node)

    def close_issue(self, issue_id: str) -> Issue:
        data = self._gql(
            """
            mutation($id: String!) {
              issueUpdate(id: $id, input: { stateId: "canceled" }) {
                issue { id title description state { name } priority
                  assignee { name email } labels { nodes { name } } createdAt url }
              }
            }
            """,
            {"id": issue_id},
        )
        node = data.get("issueUpdate", {}).get("issue")
        if not node:
            raise IssueTrackerError(f"Linear close_issue failed for {issue_id}")
        return self._parse_issue(node)


# ---------------------------------------------------------------------------
# Jira client
# ---------------------------------------------------------------------------


class JiraClient(IssueTrackerClient):
    """Jira integration via the REST API (v3)."""

    tracker_type: ClassVar[str] = "jira"
    _default_base_url: ClassVar[str] = "https://api.atlassian.com"

    def __init__(self, config: IssueTrackerConfig) -> None:
        super().__init__(config)
        if not config.base_url:
            raise ValueError("JiraClient requires base_url in config (e.g. https://<domain>.atlassian.net)")
        self.base_url = config.base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._require_api_key()}",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @staticmethod
    def _parse_issue(fields: dict[str, Any], key: str, self_url: str = "") -> Issue:
        status = fields.get("status", {}) or {}
        priority = fields.get("priority", {}) or {}
        assignee = fields.get("assignee", {}) or {}
        return Issue(
            id=key,
            title=fields.get("summary", ""),
            description=(fields.get("description") or ""),
            status=status.get("name", "open"),
            priority=priority.get("name", "medium"),
            assignee=assignee.get("displayName") or assignee.get("emailAddress"),
            labels=list(fields.get("labels", []) or []),
            created_at=fields.get("created", ""),
            tracker_type="jira",
            url=self_url,
        )

    def list_issues(self) -> list[Issue]:
        jql = f"project={self.config.project_id} ORDER BY created DESC"
        params = urllib.parse.urlencode({"jql": jql, "maxResults": 100})
        resp = _http_request(
            self._url(f"/rest/api/3/search?{params}"),
            headers=self._headers(),
        )
        issues: list[Issue] = []
        for item in resp.get("issues", []):
            issues.append(self._parse_issue(item.get("fields", {}), item.get("key", ""), item.get("self", "")))
        return issues

    def get_issue(self, issue_id: str) -> Issue:
        resp = _http_request(
            self._url(f"/rest/api/3/issue/{urllib.parse.quote(issue_id)}"),
            headers=self._headers(),
        )
        return self._parse_issue(resp.get("fields", {}), resp.get("key", issue_id), resp.get("self", ""))

    def create_issue(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> Issue:
        fields: dict[str, Any] = {
            "project": {"key": self.config.project_id},
            "summary": title,
            "description": description,
            "issuetype": {"name": "Task"},
        }
        if labels:
            fields["labels"] = labels
        if assignee:
            fields["assignee"] = {"accountId": assignee}
        resp = _http_request(
            self._url("/rest/api/3/issue"),
            method="POST",
            headers=self._headers(),
            body={"fields": fields},
        )
        return self.get_issue(resp.get("key", ""))

    def update_issue(
        self,
        issue_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> Issue:
        fields: dict[str, Any] = {}
        if title is not None:
            fields["summary"] = title
        if description is not None:
            fields["description"] = description
        if priority is not None:
            fields["priority"] = {"name": priority}
        if assignee is not None:
            fields["assignee"] = {"accountId": assignee}
        if labels is not None:
            fields["labels"] = labels
        _http_request(
            self._url(f"/rest/api/3/issue/{urllib.parse.quote(issue_id)}"),
            method="PUT",
            headers=self._headers(),
            body={"fields": fields},
        )
        return self.get_issue(issue_id)

    def close_issue(self, issue_id: str) -> Issue:
        _http_request(
            self._url(f"/rest/api/3/issue/{urllib.parse.quote(issue_id)}/transitions"),
            method="POST",
            headers=self._headers(),
            body={"transition": {"id": "31"}},  # 31 is commonly "Closed" — varies per instance
        )
        return self.get_issue(issue_id)


# ---------------------------------------------------------------------------
# Notion client
# ---------------------------------------------------------------------------


class NotionClient(IssueTrackerClient):
    """Notion integration via the API (database-backed issue board)."""

    tracker_type: ClassVar[str] = "notion"
    _default_base_url: ClassVar[str] = "https://api.notion.com/v1"

    def __init__(self, config: IssueTrackerConfig) -> None:
        super().__init__(config)
        self.base_url = (config.base_url or self._default_base_url).rstrip("/")
        # project_id is the Notion database id.

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._require_api_key()}",
            "Notion-Version": "2022-06-28",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @staticmethod
    def _prop(props: dict[str, Any], name: str, key: str = "name") -> str:
        p = props.get(name, {}) or {}
        t = p.get("type", "")
        if t == "title":
            return "".join(rt.get("plain_text", "") for rt in p.get("title", []))
        if t == "rich_text":
            return "".join(rt.get("plain_text", "") for rt in p.get("rich_text", []))
        if t == "select":
            sel = p.get("select") or {}
            return sel.get(key, "") or ""
        if t == "status":
            sel = p.get("status") or {}
            return sel.get(key, "") or ""
        if t == "people":
            people = p.get("people", [])
            return people[0].get(key, "") if people else ""
        if t == "multi_select":
            return ",".join(ms.get("name", "") for ms in p.get("multi_select", []))
        return ""

    @classmethod
    def _parse_issue(cls, page: dict[str, Any]) -> Issue:
        props = page.get("properties", {}) or {}
        labels_raw = cls._prop(props, "Labels")
        return Issue(
            id=page.get("id", ""),
            title=cls._prop(props, "Name"),
            description=cls._prop(props, "Description"),
            status=cls._prop(props, "Status") or "open",
            priority=cls._prop(props, "Priority") or "medium",
            assignee=cls._prop(props, "Assignee") or None,
            labels=[label for label in labels_raw.split(",") if label] if labels_raw else [],
            created_at=page.get("created_time", ""),
            tracker_type="notion",
            url=page.get("url", ""),
        )

    def list_issues(self) -> list[Issue]:
        resp = _http_request(
            self._url(f"/databases/{self.config.project_id}/query"),
            method="POST",
            headers=self._headers(),
            body={},
        )
        return [self._parse_issue(p) for p in resp.get("results", [])]

    def get_issue(self, issue_id: str) -> Issue:
        resp = _http_request(
            self._url(f"/pages/{urllib.parse.quote(issue_id)}"),
            headers=self._headers(),
        )
        return self._parse_issue(resp)

    def create_issue(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> Issue:
        properties: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": title}}]},
            "Description": {"rich_text": [{"text": {"content": description}}]},
            "Priority": {"select": {"name": priority}},
        }
        if labels:
            properties["Labels"] = {"multi_select": [{"name": label} for label in labels]}
        if assignee:
            properties["Assignee"] = {"people": [{"id": assignee}]}
        resp = _http_request(
            self._url("/pages"),
            method="POST",
            headers=self._headers(),
            body={"parent": {"database_id": self.config.project_id}, "properties": properties},
        )
        return self._parse_issue(resp)

    def update_issue(
        self,
        issue_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> Issue:
        properties: dict[str, Any] = {}
        if title is not None:
            properties["Name"] = {"title": [{"text": {"content": title}}]}
        if description is not None:
            properties["Description"] = {"rich_text": [{"text": {"content": description}}]}
        if priority is not None:
            properties["Priority"] = {"select": {"name": priority}}
        if status is not None:
            properties["Status"] = {"status": {"name": status}}
        if assignee is not None:
            properties["Assignee"] = {"people": [{"id": assignee}]}
        if labels is not None:
            properties["Labels"] = {"multi_select": [{"name": label} for label in labels]}
        _http_request(
            self._url(f"/pages/{urllib.parse.quote(issue_id)}"),
            method="PATCH",
            headers=self._headers(),
            body={"properties": properties},
        )
        return self.get_issue(issue_id)

    def close_issue(self, issue_id: str) -> Issue:
        _http_request(
            self._url(f"/pages/{urllib.parse.quote(issue_id)}"),
            method="PATCH",
            headers=self._headers(),
            body={"archived": True},
        )
        return self.get_issue(issue_id)


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


_CLIENT_REGISTRY: dict[str, type[IssueTrackerClient]] = {
    "linear": LinearClient,
    "jira": JiraClient,
    "notion": NotionClient,
}


class IssueTrackerManager:
    """Manages all configured issue trackers and OS-workflow linking."""

    def __init__(self) -> None:
        self._trackers: dict[str, IssueTrackerClient] = {}
        self._links: dict[str, str] = {}  # issue_id -> workflow_id
        self._synced: list[Issue] = []

    # -- registration ------------------------------------------------------

    def add_tracker(self, config: IssueTrackerConfig) -> IssueTrackerClient:
        """Register a tracker and return its instantiated client."""
        client_cls = _CLIENT_REGISTRY.get(config.tracker_type)
        if client_cls is None:
            raise ValueError(f"No client registered for tracker type {config.tracker_type!r}")
        client = client_cls(config)
        self._trackers[config.tracker_type] = client
        return client

    @property
    def trackers(self) -> dict[str, IssueTrackerClient]:
        return dict(self._trackers)

    def get_tracker(self, tracker_type: str) -> IssueTrackerClient:
        if tracker_type not in self._trackers:
            raise KeyError(f"No tracker registered for type {tracker_type!r}")
        return self._trackers[tracker_type]

    # -- sync / push -------------------------------------------------------

    def sync_issues(self) -> list[Issue]:
        """Pull issues from all registered trackers and cache them."""
        all_issues: list[Issue] = []
        for client in self._trackers.values():
            all_issues.extend(client.list_issues())
        self._synced = all_issues
        return all_issues

    @property
    def synced_issues(self) -> list[Issue]:
        return list(self._synced)

    def push_task(
        self,
        task: dict[str, Any],
        tracker_type: str | None = None,
    ) -> Issue:
        """Push a task dict to a tracker and return the created issue.

        ``task`` keys: title, description, priority, labels, assignee.
        If ``tracker_type`` is omitted, the first registered tracker is used.
        """
        if tracker_type is None:
            if not self._trackers:
                raise IssueTrackerError("No trackers registered")
            tracker_type = next(iter(self._trackers))
        client = self.get_tracker(tracker_type)
        return client.create_issue(
            title=task.get("title", "Untitled task"),
            description=task.get("description", ""),
            priority=task.get("priority", "medium"),
            labels=task.get("labels"),
            assignee=task.get("assignee"),
        )

    # -- linking -----------------------------------------------------------

    def link_issue_to_workflow(self, issue_id: str, workflow_id: str) -> None:
        """Link an issue to an OS workflow id."""
        if not issue_id:
            raise ValueError("issue_id is required")
        if not workflow_id:
            raise ValueError("workflow_id is required")
        self._links[issue_id] = workflow_id

    def unlink_issue(self, issue_id: str) -> None:
        self._links.pop(issue_id, None)

    def get_workflow_for_issue(self, issue_id: str) -> str | None:
        return self._links.get(issue_id)

    def get_issues_for_workflow(self, workflow_id: str) -> list[str]:
        return [iid for iid, wid in self._links.items() if wid == workflow_id]

    @property
    def links(self) -> dict[str, str]:
        return dict(self._links)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_client(config: IssueTrackerConfig) -> IssueTrackerClient:
    """Factory: build the correct client for a config."""
    client_cls = _CLIENT_REGISTRY.get(config.tracker_type)
    if client_cls is None:
        raise ValueError(f"Unsupported tracker type: {config.tracker_type!r}")
    return client_cls(config)


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string (helper for callers)."""
    return datetime.now(timezone.utc).isoformat()
