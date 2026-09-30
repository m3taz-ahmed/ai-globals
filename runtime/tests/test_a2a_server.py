"""Tests for runtime/a2a_server.py — A2A server-side exposure (P2.2)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from runtime.a2a_server import A2AServer, A2ATaskStore, TaskState


def _rpc(url: str, method: str, params: dict, token: str) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def test_task_store_lifecycle(tmp_path: Path) -> None:
    store = A2ATaskStore(tmp_path)
    t = store.create("do thing")
    assert t.state == TaskState.SUBMITTED
    store.update(t.id, TaskState.WORKING)
    store.update(t.id, TaskState.COMPLETED, result="done")
    got = store.get(t.id)
    assert got is not None and got.result == "done"
    # terminal states immutable
    upd = store.update(t.id, TaskState.WORKING)
    assert upd is not None and upd.state == TaskState.COMPLETED


def test_agent_card_and_task_roundtrip(tmp_path: Path) -> None:
    server = A2AServer(tmp_path, task_handler=lambda m: f"echo:{m}")
    server.serve_forever()
    try:
        base = f"http://127.0.0.1:{server.port}"
        card_req = urllib.request.Request(
            f"{base}/.well-known/agent-card.json",
            headers={"Authorization": f"Bearer {server.token}"},
        )
        card = json.loads(urllib.request.urlopen(card_req, timeout=10).read())
        assert card["name"] == "aiZee" and "bearer" in card["authentication"]["schemes"]

        res = _rpc(base, "tasks/send", {"message": "ping"}, server.token)
        task_id = res["result"]["id"]
        for _ in range(50):
            got = _rpc(base, "tasks/get", {"id": task_id}, server.token)["result"]
            if got["state"] in {"completed", "failed", "canceled"}:
                break
            time.sleep(0.05)
        assert got["state"] == "completed" and got["result"] == "echo:ping"
    finally:
        server.shutdown()


def test_auth_required(tmp_path: Path) -> None:
    server = A2AServer(tmp_path, task_handler=lambda m: m)
    server.serve_forever()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{server.port}/.well-known/agent-card.json")
        try:
            urllib.request.urlopen(req, timeout=10)
            raise AssertionError("expected 401")
        except urllib.error.HTTPError as e:
            assert e.code == 401
    finally:
        server.shutdown()


def test_cancel(tmp_path: Path) -> None:
    server = A2AServer(tmp_path, task_handler=lambda m: m)
    server.serve_forever()
    try:
        base = f"http://127.0.0.1:{server.port}"
        res = _rpc(base, "tasks/send", {"message": "x"}, server.token)
        tid = res["result"]["id"]
        out = _rpc(base, "tasks/cancel", {"id": tid}, server.token)["result"]
        # may have already completed — cancel is only rejected for unknown ids
        assert out["id"] == tid
        bad = _rpc(base, "tasks/cancel", {"id": "nope"}, server.token)
        assert "error" in bad
    finally:
        server.shutdown()


def test_handler_failure_marks_failed(tmp_path: Path) -> None:
    def boom(msg: str) -> str:
        raise RuntimeError("kaput")

    server = A2AServer(tmp_path, task_handler=boom)
    server.serve_forever()
    try:
        base = f"http://127.0.0.1:{server.port}"
        res = _rpc(base, "tasks/send", {"message": "x"}, server.token)
        tid = res["result"]["id"]
        for _ in range(50):
            got = _rpc(base, "tasks/get", {"id": tid}, server.token)["result"]
            if got["state"] == "failed":
                break
            time.sleep(0.05)
        assert got["state"] == "failed" and "kaput" in got["error"]
    finally:
        server.shutdown()


def test_persist_oserror_swallowed(tmp_path: Path, monkeypatch) -> None:
    store = A2ATaskStore(tmp_path)
    monkeypatch.setattr(Path, "open", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    t = store.create("do thing")
    assert t.state == TaskState.SUBMITTED


def test_tokenless_server_allows(tmp_path: Path) -> None:
    server = A2AServer(tmp_path, task_handler=lambda m: m, token="")
    server.serve_forever()
    try:
        card = json.loads(
            urllib.request.urlopen(
                f"http://127.0.0.1:{server.port}/.well-known/agent-card.json", timeout=10
            ).read()
        )
        assert card["name"] == "aiZee"
    finally:
        server.shutdown()


def test_get_unknown_path_404(tmp_path: Path) -> None:
    server = A2AServer(tmp_path, task_handler=lambda m: m)
    server.serve_forever()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.port}/nope",
            headers={"Authorization": f"Bearer {server.token}"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            raise AssertionError("expected 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()


def test_post_unauthorized(tmp_path: Path) -> None:
    server = A2AServer(tmp_path, task_handler=lambda m: m)
    server.serve_forever()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.port}/",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            raise AssertionError("expected 401")
        except urllib.error.HTTPError as e:
            assert e.code == 401
    finally:
        server.shutdown()


def test_post_bad_json_400(tmp_path: Path) -> None:
    server = A2AServer(tmp_path, task_handler=lambda m: m)
    server.serve_forever()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.port}/",
            data=b"{invalid json",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {server.token}",
            },
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            raise AssertionError("expected 400")
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        server.shutdown()


def test_dispatch_error_paths(tmp_path: Path) -> None:
    server = A2AServer(tmp_path, task_handler=lambda m: m)
    # tasks/send without a message
    res = server._dispatch({"id": 1, "method": "tasks/send", "params": {}})
    assert res["error"]["code"] == -32602
    # tasks/get unknown id
    res = server._dispatch({"id": 2, "method": "tasks/get", "params": {"id": "zzz"}})
    assert res["error"]["code"] == -32602
    # tasks/cancel unknown id
    res = server._dispatch({"id": 3, "method": "tasks/cancel", "params": {"id": "zzz"}})
    assert res["error"]["code"] == -32602
    # unknown method
    res = server._dispatch({"id": 4, "method": "bogus/method", "params": {}})
    assert res["error"]["code"] == -32601


def test_default_task_handler(tmp_path: Path) -> None:
    from runtime.a2a_server import default_task_handler

    class _K:
        def chat_message(self, msg: str) -> dict:
            return {"ok": True, "echo": msg}

    out = default_task_handler(_K())("hello")
    assert json.loads(out)["echo"] == "hello"
