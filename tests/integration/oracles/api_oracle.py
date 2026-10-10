"""External HTTP/state oracle; generated code executes only in a child process."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def send(port: int, authorized: bool, item: dict[str, str]) -> int:
    headers = {"Content-Type": "application/json"}
    if authorized:
        headers["Authorization"] = "Bearer witness"
    request = Request(
        f"http://127.0.0.1:{port}/items", json.dumps(item).encode(), headers=headers, method="POST"
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status
    except HTTPError as exc:
        return exc.code


scenario = sys.argv[2] if len(sys.argv) > 2 else "full"
assert scenario in ("full", "unauthorized"), "unknown oracle scenario"
with tempfile.TemporaryDirectory(prefix="api_oracle_") as directory:
    store = Path(directory) / "items.json"
    store.write_text("[]")
    node = shutil.which("node")
    assert node, "node unavailable"
    process = subprocess.Popen(
        [node, str(Path(__file__).with_name("api-server.mjs")), sys.argv[1], str(store)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        port = None
        # Import-time application logs are not acceptance outcomes or a readiness protocol.
        for _ in range(100):
            line = process.stdout.readline(65536)
            if not line:
                break
            try:
                ready = json.loads(line)
            except ValueError:
                continue
            candidate_port = ready.get("port") if isinstance(ready, dict) else None
            if type(candidate_port) is int and 0 < candidate_port < 65536:
                port = candidate_port
                break
        assert port is not None, "candidate did not expose HTTP server"
        assert send(port, False, {"name": "forbidden"}) == 403, "authorization bypassed"
        assert store.read_text() == "[]", "unauthorized mutation"
        if scenario == "full":
            assert send(port, True, {"name": ""}) == 400, "invalid item accepted"
            assert store.read_text() == "[]", "invalid input mutation"
            item = {"name": "Atelier du jeudi"}
            assert send(port, True, item) == 201, "authorized creation rejected"
            assert json.loads(store.read_text()) == [item], "item not persisted"
    finally:
        process.kill()
        process.wait(timeout=5)
print(json.dumps({"passed": True, "assertions": 6 if scenario == "full" else 2}))
