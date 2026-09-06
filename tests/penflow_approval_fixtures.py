"""Real approval files for consumer tests; reviewer JSON is a protocol fixture, not an LLM review.

The fixture exercises the approval engine without substituting its authority checks.
"""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from validator.locks import acquire_lock
from validator.penflow_review_approval import approve_review_result, require_approved_requirements
from validator.penflow_review_snapshot import create_review_snapshot


def protocol_policy_decisions() -> dict[str, str | int]:
    """Declared synthetic workflow policy, independent of candidate C20 contents."""
    return {
        "version": 1,
        "generated_docs": "required",
        "native_geometry": "required",
        "homologous_references": "not_applicable",
        "native_export": "not_applicable",
    }


def configure_protocol_policy(root: Path) -> None:
    """Generate actual source authority from a workflow explicitly marked as a test fixture."""
    from validator.penflow_policy_source import generate_policy_source

    subprocess.run(["git", "init", "--quiet", str(root)], check=True, capture_output=True)
    (root / ".gitignore").write_text(
        "# >>> Penflow managed temporary artifacts v1 >>>\n"
        ".penflow-tmp/\n.penflow-run/\n.mockup-validation/\n"
        "# <<< Penflow managed temporary artifacts v1 <<<\n"
    )
    pen = root / "penflow/ui.pen"
    pen.parent.mkdir(parents=True, exist_ok=True)
    if not pen.exists():
        pen.write_text(json.dumps({"version": "2.6", "children": []}))
    workflow = root / ".specs/protocol-fixture-workflow.md"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    modes = {"livespec": protocol_policy_decisions()}
    workflow.write_text(
        "---\npenflow_verification_policy: " + json.dumps(modes) + "\n---\n"
        "# Synthetic protocol fixture workflow\n\n"
        "This test procedure declares documentation and geometry checks. It uses synthetic "
        "source and review files, with no native reviewer, renderer, or C51 certification. "
        "Homologous references and native exports are outside this fixture's declared scope.\n"
    )
    generate_policy_source(root, workflow)


def _reference(root: Path, path: Path) -> dict[str, str]:
    return {
        "path": str(path.relative_to(root)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def canonical_approval_contract(
    source_refs: list[dict[str, str]], bindings: list[dict[str, str]], outcome_ids: list[str]
) -> dict[str, Any]:
    """Build independent canonical C20 profile data; only reviewer responses are synthetic.

    Any describes heterogeneous external contract JSON, validated by the real Penflow CLI.
    This is a consumer fixture, with no Python import dependency on the producer checkout.
    """
    return {
        "kind": "penflow-flow-contract",
        "version": 2,
        "contract_id": "profile-contract",
        "actors": [{"id": "editor", "name": "Profile editor"}],
        "entities": [{"id": "profile", "fields": [{"id": "name", "type": "string"}]}],
        "screens": [
            {
                "id": "profile",
                "flow_id": "profile",
                "title": "Profile",
                "surface": "web-desktop",
                "viewport": {"width": 1440, "height": 900},
                "states": [{"id": "default"}, {"id": "success"}, {"id": "error"}],
                "root_node": "profile.root",
            }
        ],
        "nodes": [
            {
                "id": "profile.root",
                "screen_id": "profile",
                "semantic_id": "profile",
                "test_id": "profile-screen",
                "role": "screen",
                "children": ["profile.name", "profile.save"],
            },
            {
                "id": "profile.name",
                "screen_id": "profile",
                "semantic_id": "profile.name",
                "test_id": "profile-name",
                "role": "text",
                "text": "Ada",
                "binding": "profile.name",
            },
            {
                "id": "profile.save",
                "screen_id": "profile",
                "semantic_id": "profile.save",
                "test_id": "profile-save",
                "role": "button",
                "text": "Save",
                "entity": "profile",
                "action": "save_profile",
            },
        ],
        "guards": [
            {
                "id": "name_valid",
                "variable": "profile_input",
                "operator": "equals",
                "value": "valid",
                "source": "user_input",
            },
            {
                "id": "save_succeeded",
                "variable": "profile_result",
                "operator": "equals",
                "value": "success",
                "source": "runtime_result",
            },
            {
                "id": "save_failed",
                "variable": "profile_result",
                "operator": "equals",
                "value": "error",
                "source": "runtime_result",
            },
        ],
        "permissions": [
            {
                "id": "editor_can_save",
                "actor": "editor",
                "action": "save_profile",
                "entity": "profile",
            }
        ],
        "mutations": [
            {
                "id": "save_name",
                "method": "POST",
                "endpoint": "/profiles",
                "entity": "profile",
                "request": {"name": "Ada"},
                "response": {},
                "success_state": "success",
                "error_state": "error",
            }
        ],
        "actions": [
            {
                "id": "save_profile",
                "node": "profile.save",
                "trigger": "click",
                "guard": "name_valid",
                "permission": "editor_can_save",
                "mutation": "save_name",
                "success_transition": "profile_success",
                "error_transition": "profile_error",
            }
        ],
        "flows": [{"id": "profile", "entry_screen": "profile"}],
        "transitions": [
            {
                "id": f"profile_{outcome}",
                "flow": "profile",
                "from_screen": "profile",
                "to_screen": "profile",
                "from_state": "default",
                "to_state": outcome,
                "trigger": "save_profile",
                "action": "save_profile",
                "guard": "save_succeeded" if outcome == "success" else "save_failed",
                "kind": "state",
                "label": f"Profile save {outcome}",
                "causal": {
                    "version": 1,
                    "action_visibility": "user-visible",
                    "outcome": outcome,
                    "fanout": {"group": "profile_result", "policy": "exclusive"},
                },
            }
            for outcome in ["success", "error"]
        ],
        "needs_review": False,
        "needs_clarification": [],
        "verification_policy": protocol_policy_decisions(),
        "requirements": {
            "source_kind": "livespec-fr-ac-v1",
            "source_refs": source_refs,
            "bindings": bindings,
        },
        "outcome_expectations": [
            {
                "obligation_id": identity,
                "source_pointer": "/mutations/0",
                "category": "result",
                "assertions": [
                    {
                        "operator": "equals",
                        "pointer": pointer,
                        "expected": expected,
                        "capability": "ui",
                    }
                    for pointer, expected in [
                        ("/after/text", "Ada"),
                        ("/after/state", "success"),
                        ("/result/actor_id", "editor"),
                        ("/result/action_id", "save_profile"),
                        ("/result/outcome", "success"),
                    ]
                ],
            }
            for identity in outcome_ids
        ],
    }


def approved_feature(root: Path, slug: str = "001-test") -> None:
    """Create and approve real selected FR/AC inputs without mocking approval checks."""
    folder = root / ".specs/features" / slug
    folder.mkdir(parents=True, exist_ok=True)
    spec = folder / "spec.md"
    spec.write_text(
        "---\nvisual: true\nstatus: Approved\n---\n# Save profile\n\n"
        "## Functional Requirements\n\n- **FR-001:** Save the edited name (AC-001).\n\n"
        "## Acceptance Criteria\n\n- **AC-001:** Display the saved name.\n"
    )
    (folder / "plan.md").write_text("# Plan\n\nSave the name through the profile adapter.\n")
    # Replace the transport fixture's unfinished .pen before real contract preflight.
    pen = root / "penflow/ui.pen"
    pen.parent.mkdir(parents=True, exist_ok=True)
    pen.write_text(
        json.dumps(
            {
                "version": "2.6",
                "children": [
                    {
                        "id": "profile",
                        "name": "Protocol profile fixture",
                        "type": "frame",
                        "width": 1440,
                        "height": 900,
                        "children": [],
                    }
                ],
            }
        )
    )
    configure_protocol_policy(root)
    contract = root / "penflow/flow-ui-contract/contract.json"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text(
        json.dumps(
            canonical_approval_contract(
                [_reference(root, spec)],
                [
                    {"requirement_id": f"livespec:{slug}:{identifier}", "obligation_id": "save"}
                    for identifier in ["FR-001", "AC-001"]
                ],
                ["save"],
            )
        )
    )
    snapshot = create_review_snapshot(root, slug)
    output = root / "protocol-fixture-review-output.json"
    review = {
        "invocation_id": "protocol-fixture-review",
        "producer_id": "test-only-reviewer",
        "input_sha256": snapshot["input_sha256"],
        "verdict": "PASS",
        "blocking_count": 0,
        "findings": [],
    }
    output.write_text(json.dumps(review))
    result = root / "protocol-fixture-review-result.json"
    result.write_text(
        json.dumps(
            {
                "kind": "livespec-penflow-review-result",
                "version": 1,
                "snapshot": snapshot["snapshot"],
                "review": {**review, "output": _reference(root, output)},
            }
        )
    )
    with acquire_lock(root / ".specs"):
        approve_review_result(root, slug, result)
    pipeline = folder / "pipeline.md"
    if pipeline.exists():
        pipeline.write_text(
            pipeline.read_text().replace("| Plan Review | Pending |", "| Plan Review | Done |")
        )
    else:
        pipeline.write_text("| Phase | Status |\n| Plan Review | Done |\n")
    require_approved_requirements(root, slug)
