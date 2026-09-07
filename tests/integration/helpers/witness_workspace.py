# @spec(FR-013)
# .specs/features/078-requirement-evidence-integrity/spec.md#fr-013
"""Retain a candidate when execution control is incomplete."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WitnessWorkspace:
    """Disposable by default; incomplete execution explicitly preserves original bytes."""

    prefix: str
    preserve: bool = False
    root: Path = field(init=False)

    def __enter__(self) -> WitnessWorkspace:
        self.root = Path(tempfile.mkdtemp(prefix=self.prefix))
        return self

    def __exit__(self, *_args: object) -> None:
        if not self.preserve:
            shutil.rmtree(self.root)
