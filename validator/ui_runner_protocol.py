# LiveSpec traceability anchors
# @spec(FR-001)

"""Public facade for the uniform UI runner protocol."""

from __future__ import annotations

from validator.runner_protocol_impl import (
    RunnerHandler,
    RuntimeOutputMisplacedError,
    UICapabilityResult,
    assert_output_not_in_design_screens,
)

__all__ = [
    "RunnerHandler",
    "RuntimeOutputMisplacedError",
    "UICapabilityResult",
    "assert_output_not_in_design_screens",
]
