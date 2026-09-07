"""External purge acceptance assertions; candidate may not edit this oracle."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

candidate = Path(sys.argv[1])
with tempfile.TemporaryDirectory(prefix="purge_oracle_") as directory:
    root = Path(directory)
    now = 2_000_000_000
    for name, age in {"expired": 86401, "boundary": 86400, "fresh": 86399}.items():
        path = root / name
        path.write_text(name)
        os.utime(path, (now - age, now - age))
    (root / "directory").mkdir()
    subprocess.run(
        [sys.executable, str(candidate / "purge.py"), str(root), "--now", str(now)],
        check=True,
        timeout=10,
    )
    assert not (root / "expired").exists(), "expired file retained"
    assert not (root / "boundary").exists(), "24h boundary file retained"
    assert (root / "fresh").read_text() == "fresh", "new file changed"
    assert (root / "directory").is_dir(), "directory changed"
print('{"passed": true, "assertions": 4}')
