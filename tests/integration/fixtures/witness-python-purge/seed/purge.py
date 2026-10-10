"""Reference candidate for the isolated purge witness; not generated output."""

import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("directory", type=Path)
parser.add_argument("--now", type=float, required=True)
args = parser.parse_args()
for path in args.directory.iterdir():
    if path.is_file() and not path.is_symlink() and args.now - path.stat().st_mtime >= 86400:
        path.unlink()
