"""Tests for runtime/issue_tracker.py — Linear/Jira/Notion integration."""

from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import patch

import pytest

from runtime.issue_tracker import (
    SUPPORTED_TRACKERS,
    Issue,
    IssueTrackerClient,
    IssueTrackerConfig,
    IssueTrackerError,
    IssueTrackerManager,
    JiraClient,
    LinearClient,
    NotionClient,
    _http_request,
    create_client,
)

# ---------------------------------------------------------------------------
# Helpers — fake HTTP
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload: Any, status: int = 200, reason: str = "OK") -> None:
        self._payload = payload
        self.status = status
        self.reason = reason

    def read(self) -> bytes:
        if isinstance(self._payload, (bytes, bytearray)):
            return bytes(self._payload)
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


def _fake_urlopen(payload: Any, status: int = 200, reason: str = "OK"):
    """Return a patcher for urllib.request.urlopen that yields ``payload``."""
    return patch(
        "runtime.issue_tracker.urllib.request.urlopen",
        return_value=_FakeResponse(payload, status, reason),
    )


# Sample API payloads -------------------------------------------------------

_LINEAR_LIST = {
    "data": {
        "project": {
            "issues": {
                "nodes": [
                    {
                        "id": "LIN-1",
                        "title": "Fix bug",
                        "description": "desc",
                        "state": {"name": "In Progress"},
                        "priority": 3,
                        "assignee": {"name": "Alice"},
                        "labels": {"nodes": [{"name": "bug"}, {"name": "urgent"}]},
                        "createdAt": "2024-01-01T00:00:00Z",
                        "url": "https://linear.app/issue/LIN-1",
                    }
                ]
            }
        }
    }
}

_LINEAR_GET = {
    "data": {
        "issue": {
            "id": "LIN-1",
            "title": "Fix bug",
            "description": "desc",
            "state": {"name": "In Progress"},
            "priority": 3,
            "assignee": {"name": "Alice"},
            "labels": {"nodes": [{"name": "bug"}]},
            "createdAt": "2024-01-01T00:00:00Z",
            "url": "https://linear.app/issue/LIN-1",
        }
    }
}

_LINEAR_CREATE = {
    "data": {
        "issueCreate": {
            "issue": {
                "id": "LIN-2",
                "title": "New issue",
                "description": "",
                "state": {"name": "Backlog"},
                "priority": 2,
                "assignee": {},
                "labels": {"nodes": []},
                "createdAt": "2024-01-02T00:00:00Z",
                "url": "https://linear.app/issue/LIN-2",
            }
        }
    }
}

_LINEAR_UPDATE = {
    "data": {
        "issueUpdate": {
            "issue": {
                "id": "LIN-1",
                "title": "Updated",
                "description": "desc",
                "state": {"name": "In Progress"},
                "priority": 3,
                "assignee": {"name": "Alice"},
                "labels": {"nodes": [{"name": "bug"}]},
                "createdAt": "2024-01-01T00:00:00Z",
                "url": "https://linear.app/issue/LIN-1",
            }
        }
    }
}

_JIRA_LIST = {
    "issues": [
        {
            "key": "JIRA-1",
            "self": "https://jira/issue/JIRA-1",
            "fields": {
                "summary": "Fix bug",
                "description": "desc",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "assignee": {"displayName": "Bob"},
                "labels": ["bug"],
                "created": "2024-01-01T00:00:00.000+0000",
            },
        }
    ]
}

_JIRA_GET = {
    "key": "JIRA-1",
    "self": "https://jira/issue/JIRA-1",
    "fields": {
        "summary": "Fix bug",
        "description": "desc",
        "status": {"name": "In Progress"},
        "priority": {"name": "High"},
        "assignee": {"displayName": "Bob"},
        "labels": ["bug"],
        "created": "2024-01-01T00:00:00.000+0000",
    },
}

_JIRA_CREATE = {"key": "JIRA-2", "self": "https://jira/issue/JIRA-2"}

_NOTION_LIST = {
    "results": [
        {
            "id": "ntn-page-1",
            "url": "https://notion.so/ntn-page-1",
            "created_time": "2024-01-01T00:00:00.000Z",
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Fix bug"}]},
                "Description": {"type": "rich_text", "rich_text": [{"plain_text": "desc"}]},
                "Status": {"type": "status", "status": {"name": "In Progress"}},
                "Priority": {"type": "select", "select": {"name": "High"}},
                "Assignee": {"type": "people", "people": [{"name": "Carol"}]},
                "Labels": {"type": "multi_select", "multi_select": [{"name": "bug"}, {"name": "ui"}]},
            },
        }
    ]
}

_NOTION_GET = {
    "id": "ntn-page-1",
    "url": "https://notion.so/ntn-page-1",
    "created_time": "2024-01-01T00:00:00.000Z",
    "properties": {
        "Name": {"type": "title", "title": [{"plain_text": "Fix bug"}]},
        "Description": {"type": "rich_text", "rich_text": [{"plain_text": "desc"}]},
        "Status": {"type": "status", "status": {"name": "In Progress"}},
        "Priority": {"type": "select", "select": {"name": "High"}},
        "Assignee": {"type": "people", "people": [{"name": "Carol"}]},
        "Labels": {"type": "multi_select", "multi_select": [{"name": "bug"}]},
    },
}

_NOTION_CREATE = {
    "id": "ntn-page-2",
    "url": "https://notion.so/ntn-page-2",
    "created_time": "2024-01-02T00:00:00.000Z",
    "properties": {
        "Name": {"type": "title", "title": [{"plain_text": "New issue"}]},
        "Description": {"type": "rich_text", "rich_text": []},
        "Status": {"type": "status", "status": {"name": "Not started"}},
        "Priority": {"type": "select", "select": {"name": "medium"}},
        "Assignee": {"type": "people", "people": []},
        "Labels": {"type": "multi_select", "multi_select": []},
    },
}


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


class TestIssueTrackerConfig:
    def test_valid_linear_config(self) -> None:
        cfg = IssueTrackerConfig(tracker_type="linear", project_id="proj-1", api_key_env="LINEAR_API_KEY")
        assert cfg.tracker_type == "linear"
        assert cfg.base_url is None

    def test_invalid_tracker_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported tracker type"):
            IssueTrackerConfig(tracker_type="github", project_id="p", api_key_env="X")

    def test_missing_project_id_raises(self) -> None:
        with pytest.raises(ValueError, match="project_id is required"):
            IssueTrackerConfig(tracker_type="linear", project_id="", api_key_env="X")

    def test_missing_api_key_env_raises(self) -> None:
        with pytest.raises(ValueError, match="api_key_env is required"):
            IssueTrackerConfig(tracker_type="linear", project_id="p", api_key_env="")

    def test_resolve_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_LINEAR_KEY", "secret123")
        cfg = IssueTrackerConfig(tracker_type="linear", project_id="p", api_key_env="MY_LINEAR_KEY")
        assert cfg.resolve_api_key() == "secret123"

    def test_resolve_api_key_missing_env_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_KEY_ENV", raising=False)
        cfg = IssueTrackerConfig(tracker_type="linear", project_id="p", api_key_env="MISSING_KEY_ENV")
        assert cfg.resolve_api_key() is None

    def test_explicit_api_key_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ENV_KEY", "envval")
        cfg = IssueTrackerConfig(
            tracker_type="linear", project_id="p", api_key_env="ENV_KEY", api_key="explicit"
        )
        assert cfg.resolve_api_key() == "explicit"


# ---------------------------------------------------------------------------
# Issue dataclass
# ---------------------------------------------------------------------------


class TestIssue:
    def test_defaults(self) -> None:
        i = Issue(id="1", title="t")
        assert i.status == "open"
        assert i.priority == "medium"
        assert i.labels == []
        assert i.assignee is None

    def test_to_dict_roundtrip(self) -> None:
        i = Issue(id="1", title="t", labels=["a", "b"], assignee="x")
        d = i.to_dict()
        assert d["id"] == "1"
        assert d["labels"] == ["a", "b"]
        assert d["assignee"] == "x"
        assert d["tracker_type"] == ""


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


class TestHttpRequest:
    def test_success_json(self) -> None:
        with _fake_urlopen({"ok": True}):
            assert _http_request("https://x") == {"ok": True}

    def test_http_error_raises(self) -> None:
        err = urllib.error.HTTPError(
            "https://x", 500, "Server Error", {}, None  # type: ignore[arg-type]
        )
        with patch("runtime.issue_tracker.urllib.request.urlopen", side_effect=err), pytest.raises(IssueTrackerError, match="HTTP 500"):
                _http_request("https://x")

    def test_url_error_raises(self) -> None:
        err = urllib.error.URLError("conn refused")
        with patch("runtime.issue_tracker.urllib.request.urlopen", side_effect=err), pytest.raises(IssueTrackerError, match="Network error"):
                _http_request("https://x")

    def test_invalid_json_raises(self) -> None:
        with _fake_urlopen(b"not-json"), pytest.raises(IssueTrackerError, match="Invalid JSON"):
                _http_request("https://x")

    def test_empty_response_returns_empty_dict(self) -> None:
        with _fake_urlopen(b""):
            assert _http_request("https://x") == {}

    def test_non_object_json_raises(self) -> None:
        with _fake_urlopen(b"[1,2,3]"), pytest.raises(IssueTrackerError, match="Expected JSON object"):
                _http_request("https://x")


# ---------------------------------------------------------------------------
# LinearClient
# ---------------------------------------------------------------------------


class TestLinearClient:
    def _cfg(self, api_key: str = "lin-key") -> IssueTrackerConfig:
        return IssueTrackerConfig(
            tracker_type="linear", project_id="proj-1", api_key_env="LINEAR_API_KEY", api_key=api_key
        )

    def test_type_mismatch_raises(self) -> None:
        cfg = IssueTrackerConfig(
            tracker_type="jira", project_id="p", api_key_env="X", api_key="k", base_url="https://j"
        )
        with pytest.raises(ValueError, match="does not match"):
            LinearClient(cfg)

    def test_missing_api_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NO_KEY", raising=False)
        cfg = IssueTrackerConfig(tracker_type="linear", project_id="p", api_key_env="NO_KEY")
        client = LinearClient(cfg)
        with pytest.raises(IssueTrackerError, match="Missing API key"):
            client.list_issues()

    def test_list_issues(self) -> None:
        with _fake_urlopen(_LINEAR_LIST):
            issues = LinearClient(self._cfg()).list_issues()
        assert len(issues) == 1
        assert issues[0].id == "LIN-1"
        assert issues[0].title == "Fix bug"
        assert issues[0].status == "In Progress"
        assert issues[0].labels == ["bug", "urgent"]
        assert issues[0].tracker_type == "linear"

    def test_get_issue(self) -> None:
        with _fake_urlopen(_LINEAR_GET):
            issue = LinearClient(self._cfg()).get_issue("LIN-1")
        assert issue.id == "LIN-1"
        assert issue.assignee == "Alice"

    def test_get_issue_not_found(self) -> None:
        with _fake_urlopen({"data": {"issue": None}}), pytest.raises(IssueTrackerError, match="not found"):
            LinearClient(self._cfg()).get_issue("missing")

    def test_create_issue(self) -> None:
        with _fake_urlopen(_LINEAR_CREATE):
            issue = LinearClient(self._cfg()).create_issue(title="New issue")
        assert issue.id == "LIN-2"
        assert issue.title == "New issue"

    def test_create_issue_no_issue_returned(self) -> None:
        with _fake_urlopen({"data": {"issueCreate": {"issue": None}}}), pytest.raises(IssueTrackerError, match="no issue"):
            LinearClient(self._cfg()).create_issue(title="x")

    def test_update_issue(self) -> None:
        with _fake_urlopen(_LINEAR_UPDATE):
            issue = LinearClient(self._cfg()).update_issue("LIN-1", title="Updated")
        assert issue.id == "LIN-1"
        assert issue.title == "Updated"

    def test_close_issue(self) -> None:
        with _fake_urlopen(_LINEAR_UPDATE):
            issue = LinearClient(self._cfg()).close_issue("LIN-1")
        assert issue.id == "LIN-1"

    def test_graphql_errors_raise(self) -> None:
        with _fake_urlopen({"errors": [{"message": "bad query"}]}), pytest.raises(IssueTrackerError, match="GraphQL errors"):
            LinearClient(self._cfg()).list_issues()


# ---------------------------------------------------------------------------
# JiraClient
# ---------------------------------------------------------------------------


class TestJiraClient:
    def _cfg(self, api_key: str = "jira-key") -> IssueTrackerConfig:
        return IssueTrackerConfig(
            tracker_type="jira",
            project_id="PROJ",
            api_key_env="JIRA_API_KEY",
            api_key=api_key,
            base_url="https://test.atlassian.net",
        )

    def test_requires_base_url(self) -> None:
        cfg = IssueTrackerConfig(
            tracker_type="jira", project_id="p", api_key_env="X", api_key="k"
        )
        with pytest.raises(ValueError, match="base_url"):
            JiraClient(cfg)

    def test_list_issues(self) -> None:
        with _fake_urlopen(_JIRA_LIST):
            issues = JiraClient(self._cfg()).list_issues()
        assert len(issues) == 1
        assert issues[0].id == "JIRA-1"
        assert issues[0].priority == "High"
        assert issues[0].labels == ["bug"]
        assert issues[0].tracker_type == "jira"

    def test_get_issue(self) -> None:
        with _fake_urlopen(_JIRA_GET):
            issue = JiraClient(self._cfg()).get_issue("JIRA-1")
        assert issue.id == "JIRA-1"
        assert issue.assignee == "Bob"

    def test_create_issue(self) -> None:
        # create returns key, then get_issue is called — fake both calls
        with _fake_urlopen(_JIRA_GET), patch(
            "runtime.issue_tracker._http_request",
            side_effect=[_JIRA_CREATE, _JIRA_GET],
        ):
            issue = JiraClient(self._cfg()).create_issue(title="New")
        assert issue.id == "JIRA-1"

    def test_update_issue(self) -> None:
        with patch(
            "runtime.issue_tracker._http_request",
            side_effect=[{}, _JIRA_GET],
        ):
            issue = JiraClient(self._cfg()).update_issue("JIRA-1", title="Updated")
        assert issue.id == "JIRA-1"

    def test_close_issue(self) -> None:
        with patch(
            "runtime.issue_tracker._http_request",
            side_effect=[{}, _JIRA_GET],
        ):
            issue = JiraClient(self._cfg()).close_issue("JIRA-1")
        assert issue.id == "JIRA-1"


# ---------------------------------------------------------------------------
# NotionClient
# ---------------------------------------------------------------------------


class TestNotionClient:
    def _cfg(self, api_key: str = "ntn-key") -> IssueTrackerConfig:
        return IssueTrackerConfig(
            tracker_type="notion",
            project_id="db-1",
            api_key_env="NOTION_API_KEY",
            api_key=api_key,
        )

    def test_list_issues(self) -> None:
        with _fake_urlopen(_NOTION_LIST):
            issues = NotionClient(self._cfg()).list_issues()
        assert len(issues) == 1
        assert issues[0].id == "ntn-page-1"
        assert issues[0].title == "Fix bug"
        assert issues[0].status == "In Progress"
        assert issues[0].labels == ["bug", "ui"]
        assert issues[0].tracker_type == "notion"

    def test_get_issue(self) -> None:
        with _fake_urlopen(_NOTION_GET):
            issue = NotionClient(self._cfg()).get_issue("ntn-page-1")
        assert issue.id == "ntn-page-1"
        assert issue.assignee == "Carol"

    def test_create_issue(self) -> None:
        with _fake_urlopen(_NOTION_CREATE):
            issue = NotionClient(self._cfg()).create_issue(title="New issue")
        assert issue.id == "ntn-page-2"
        assert issue.title == "New issue"

    def test_update_issue(self) -> None:
        with patch(
            "runtime.issue_tracker._http_request",
            side_effect=[{}, _NOTION_GET],
        ):
            issue = NotionClient(self._cfg()).update_issue("ntn-page-1", title="Updated")
        assert issue.id == "ntn-page-1"

    def test_close_issue(self) -> None:
        with patch(
            "runtime.issue_tracker._http_request",
            side_effect=[{}, _NOTION_GET],
        ):
            issue = NotionClient(self._cfg()).close_issue("ntn-page-1")
        assert issue.id == "ntn-page-1"


# ---------------------------------------------------------------------------
# IssueTrackerManager
# ---------------------------------------------------------------------------


class TestIssueTrackerManager:
    def test_add_tracker_linear(self) -> None:
        mgr = IssueTrackerManager()
        cfg = IssueTrackerConfig(
            tracker_type="linear", project_id="p", api_key_env="X", api_key="k"
        )
        client = mgr.add_tracker(cfg)
        assert isinstance(client, LinearClient)
        assert "linear" in mgr.trackers

    def test_add_tracker_jira(self) -> None:
        mgr = IssueTrackerManager()
        cfg = IssueTrackerConfig(
            tracker_type="jira",
            project_id="p",
            api_key_env="X",
            api_key="k",
            base_url="https://j",
        )
        client = mgr.add_tracker(cfg)
        assert isinstance(client, JiraClient)

    def test_add_tracker_notion(self) -> None:
        mgr = IssueTrackerManager()
        cfg = IssueTrackerConfig(
            tracker_type="notion", project_id="p", api_key_env="X", api_key="k"
        )
        client = mgr.add_tracker(cfg)
        assert isinstance(client, NotionClient)

    def test_get_tracker_missing_raises(self) -> None:
        mgr = IssueTrackerManager()
        with pytest.raises(KeyError):
            mgr.get_tracker("linear")

    def test_sync_issues_all_trackers(self) -> None:
        mgr = IssueTrackerManager()
        lin = IssueTrackerConfig(
            tracker_type="linear", project_id="p", api_key_env="X", api_key="k"
        )
        ntn = IssueTrackerConfig(
            tracker_type="notion", project_id="p", api_key_env="X", api_key="k"
        )
        mgr.add_tracker(lin)
        mgr.add_tracker(ntn)
        with patch.object(LinearClient, "list_issues", return_value=[Issue(id="L1", title="l")]), patch.object(NotionClient, "list_issues", return_value=[Issue(id="N1", title="n")]):
                issues = mgr.sync_issues()
        assert {i.id for i in issues} == {"L1", "N1"}
        assert mgr.synced_issues == issues

    def test_push_task_first_tracker(self) -> None:
        mgr = IssueTrackerManager()
        cfg = IssueTrackerConfig(
            tracker_type="linear", project_id="p", api_key_env="X", api_key="k"
        )
        mgr.add_tracker(cfg)
        created = Issue(id="L9", title="pushed")
        with patch.object(LinearClient, "create_issue", return_value=created) as m:
            result = mgr.push_task({"title": "pushed", "description": "d", "priority": "high"})
        assert result.id == "L9"
        m.assert_called_once_with(title="pushed", description="d", priority="high", labels=None, assignee=None)

    def test_push_task_specific_tracker(self) -> None:
        mgr = IssueTrackerManager()
        lin = IssueTrackerConfig(
            tracker_type="linear", project_id="p", api_key_env="X", api_key="k"
        )
        ntn = IssueTrackerConfig(
            tracker_type="notion", project_id="p", api_key_env="X", api_key="k"
        )
        mgr.add_tracker(lin)
        mgr.add_tracker(ntn)
        created = Issue(id="N9", title="pushed")
        with patch.object(NotionClient, "create_issue", return_value=created) as m:
            result = mgr.push_task({"title": "x"}, tracker_type="notion")
        assert result.id == "N9"
        m.assert_called_once()

    def test_push_task_no_trackers_raises(self) -> None:
        mgr = IssueTrackerManager()
        with pytest.raises(IssueTrackerError, match="No trackers registered"):
            mgr.push_task({"title": "x"})

    def test_link_issue_to_workflow(self) -> None:
        mgr = IssueTrackerManager()
        mgr.link_issue_to_workflow("ISS-1", "wf-abc")
        assert mgr.get_workflow_for_issue("ISS-1") == "wf-abc"
        assert mgr.get_issues_for_workflow("wf-abc") == ["ISS-1"]

    def test_link_invalid_ids_raise(self) -> None:
        mgr = IssueTrackerManager()
        with pytest.raises(ValueError, match="issue_id is required"):
            mgr.link_issue_to_workflow("", "wf")
        with pytest.raises(ValueError, match="workflow_id is required"):
            mgr.link_issue_to_workflow("i", "")

    def test_unlink_issue(self) -> None:
        mgr = IssueTrackerManager()
        mgr.link_issue_to_workflow("I1", "W1")
        mgr.unlink_issue("I1")
        assert mgr.get_workflow_for_issue("I1") is None

    def test_unlink_missing_is_noop(self) -> None:
        mgr = IssueTrackerManager()
        mgr.unlink_issue("nope")  # should not raise


# ---------------------------------------------------------------------------
# Factory & abstract base
# ---------------------------------------------------------------------------


class TestFactoryAndBase:
    def test_create_client_linear(self) -> None:
        cfg = IssueTrackerConfig(
            tracker_type="linear", project_id="p", api_key_env="X", api_key="k"
        )
        assert isinstance(create_client(cfg), LinearClient)

    def test_create_client_jira(self) -> None:
        cfg = IssueTrackerConfig(
            tracker_type="jira", project_id="p", api_key_env="X", api_key="k", base_url="https://j"
        )
        assert isinstance(create_client(cfg), JiraClient)

    def test_create_client_notion(self) -> None:
        cfg = IssueTrackerConfig(
            tracker_type="notion", project_id="p", api_key_env="X", api_key="k"
        )
        assert isinstance(create_client(cfg), NotionClient)

    def test_create_client_invalid_raises(self) -> None:
        # bypass config validation by constructing then mutating
        cfg = IssueTrackerConfig(
            tracker_type="linear", project_id="p", api_key_env="X", api_key="k"
        )
        cfg.tracker_type = "unknown"
        with pytest.raises(ValueError, match="Unsupported tracker type"):
            create_client(cfg)

    def test_abstract_base_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            IssueTrackerClient(  # type: ignore[abstract]
                IssueTrackerConfig(tracker_type="linear", project_id="p", api_key_env="X", api_key="k")
            )

    def test_supported_trackers_constant(self) -> None:
        assert SUPPORTED_TRACKERS == ("linear", "jira", "notion")
