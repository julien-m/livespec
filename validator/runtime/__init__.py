"""Pinned LiveSpec runtime snapshots, project locks, shim and drift inspection.

Feature 083 isolates consumer projects from the mutable LiveSpec development
checkout: ``livespec runtime install`` builds immutable snapshots under a runtime
home, projects pin one in ``.specs/livespec.lock`` and a generated shim executes
the pinned snapshot. Command wiring lives in ``validator/cli_commands/runtime_cmd.py``.
"""
