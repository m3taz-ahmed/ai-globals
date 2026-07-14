import json
import tempfile
import threading
import time
from pathlib import Path
from urllib.request import urlopen

from dashboard.server import DashboardHandler, ThreadingHTTPServer


def _serve(tmp_root):
    DashboardHandler.root = tmp_root
    DashboardHandler.kernel = None  # will be recreated
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_root / sub).mkdir(parents=True, exist_ok=True)
    (tmp_root / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    DashboardHandler.kernel = __import__("runtime.kernel", fromlist=["Kernel"]).Kernel(tmp_root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


def test_dashboard_status():
    tmp = Path(tempfile.mkdtemp(prefix="aios_dash_"))
    server, port = _serve(tmp)
    try:
        time.sleep(0.1)
        with urlopen(f"http://127.0.0.1:{port}/api/status") as resp:
            body = resp.read().decode()
            data = json.loads(body)
            assert data["version"] == "4.21.0"
    finally:
        server.shutdown()
