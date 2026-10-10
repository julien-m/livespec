"""Translate independent measured form facts into C12/C51 runtime evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# Only these finite scenarios are implemented; expected predicates are never read.
SCENARIOS = {
    "action:edit_name:allowed": ("before", "edited", "item-name"),
    "action:submit_item:allowed": ("edited", "valid", "submit-item"),
    "validation:required_name:submit_item:allowed": ("edited", "valid", "submit-item"),
    "validation:required_name:submit_item:invalid": ("before", "invalid", "submit-item"),
    "transition:show_success": ("edited", "valid", "submit-item"),
}


def reference(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    return path


def ui(snapshot: dict[str, Any], semantic: str) -> dict[str, Any]:
    """Project actual node and screen values without supplying missing identities."""
    node = next(node for node in snapshot["nodes"] if node["semantic_id"] == semantic)
    return {
        "screen_id": snapshot["screen_id"],
        "state": snapshot["state"],
        **{
            key: node[key]
            for key in ("semantic_id", "role", "visible", "enabled", "text", "value", "bbox")
        },
        "properties": snapshot["properties"],
    }


def _observation(raw: dict[str, Any], identifier: str) -> tuple[dict, dict, dict]:
    before_key, after_key, semantic = SCENARIOS[identifier]
    before, after = raw[before_key], raw[after_key]
    node = next(node for node in before["nodes"] if node["semantic_id"] == semantic)
    action = node["context"].get("action")
    events = after["events"][len(before["events"]) :]
    if not action or not any(event["trusted"] and event["action_id"] == action for event in events):
        raise ValueError(f"No actual trusted action for {identifier}")
    if identifier.startswith("validation:"):
        outcome = "allowed" if before["properties"]["name_validity"] == "valid" else "invalid"
    elif identifier.startswith("transition:"):
        outcome = "success" if after["properties"]["success_visible"] else "error"
    else:
        changed = ui(before, semantic)["value"] != ui(after, semantic)["value"]
        submitted = after["submissions"] > before["submissions"]
        outcome = "allowed" if changed or submitted else "error"
    return (
        ui(before, semantic),
        ui(after, semantic),
        {
            "actor_id": before["actor_id"],
            "action_id": action,
            "outcome": outcome,
        },
    )


def _outcomes(raw: dict, contract: Path, runner: Path, identity: dict) -> list[Path]:
    paths: list[Path] = []
    for slot in json.loads(contract.read_text())["outcome_expectations"]:
        if slot["category"] == "structure":
            continue
        identifier = slot["obligation_id"]
        if identifier not in SCENARIOS:
            raise ValueError(f"Unsupported captured scenario: {identifier}")
        before, after, result = _observation(raw, identifier)
        common = {
            "version": 1,
            **identity,
            "scenario_id": raw["scenario_id"],
            "session_id": raw["session_id"],
            "screen_id": before["screen_id"],
            "semantic_id": before["semantic_id"],
            "instance_key": None,
            "capability": "ui",
            "before": before,
            "after": after,
            "result": result,
        }
        name = identifier.replace(":", "--")
        facts = write(
            runner / f"{name}.facts.json",
            {
                "kind": "penflow-runtime-facts",
                **common,
                "raw_evidence": [reference(runner / "browser.json")],
            },
        )
        observation = write(
            contract.parent.parent / "outcome-observations" / f"{name}.json",
            {
                "kind": "penflow-outcome-observation",
                **common,
                "obligation_id": identifier,
                "category": slot["category"],
                "evidence": reference(facts),
            },
        )
        paths.extend((facts, observation))
    return paths


def _screen(snapshot: dict) -> dict:
    nodes = {}
    for node in snapshot["nodes"]:
        semantic = node["semantic_id"]
        if semantic in nodes:
            raise ValueError("Duplicate actual semantic identity")
        nodes[semantic] = {
            key: node[key]
            for key in ("id", "semantic_id", "role", "bbox", "text", "visual", "context")
        }
        nodes[semantic]["children"] = []
    roots = []
    for node in snapshot["nodes"]:
        parent = node["parent_semantic_id"]
        if parent is None:
            roots.append(nodes[node["semantic_id"]])
        else:
            nodes[parent]["children"].append(nodes[node["semantic_id"]])
    if len(roots) != 1 or roots[0]["role"] != "screen":
        raise ValueError("Actual DOM must identify exactly one screen root")
    return {"screen_id": snapshot["screen_id"], "viewport": snapshot["viewport"], "root": roots[0]}


def _state_index(raw: dict, runner: Path, identity: dict) -> tuple[list[dict], list[Path]]:
    paths: list[Path] = []
    states = []
    for key in ("before", "valid"):
        snapshot = raw[key]
        witness = write(
            runner / f"{key}.ui-snapshot.json",
            {
                "kind": "penflow-runtime-ui-snapshot",
                "version": 1,
                **identity,
                "scenario_id": raw["scenario_id"],
                "session_id": raw["session_id"],
                "facts": ui(snapshot, snapshot["screen_id"]),
                "raw_evidence": [reference(runner / "browser.json")],
            },
        )
        paths.append(witness)
        states.append(
            {
                "screen_id": snapshot["screen_id"],
                "state": snapshot["state"],
                "scenario_id": raw["scenario_id"],
                "session_id": raw["session_id"],
                "evidence": reference(witness),
            }
        )
    return states, paths


# @spec FR-012: typed observations bind actual UI behavior to independent raw evidence.
def convert_runtime(candidate: Path, runner: Path, build_id: str) -> list[Path]:
    """Generate runtime artifacts; malformed/missing DOM authority remains explicit."""
    raw = json.loads((runner / "browser.json").read_text())
    for key in ("before", "invalid", "edited", "valid"):
        snapshot = raw[key]
        if snapshot["unmapped"] or not all(
            snapshot[key] for key in ("screen_id", "state", "actor_id")
        ):
            raise ValueError("Actual DOM lacks screen/state/actor or contains unmapped controls")
    contract = candidate / "penflow/flow-ui-contract/contract.json"
    identity = {
        "contract_sha256": reference(contract)["sha256"],
        "build_id": build_id,
        "producer_invocation_id": runner.name,
    }
    paths = _outcomes(raw, contract, runner, identity)
    states, state_paths = _state_index(raw, runner, identity)
    paths.extend(state_paths)
    tree = write(
        candidate / "penflow/actual-ui-tree.json",
        {
            "version": 1,
            "screens": [_screen(raw["valid"])],
            "observed_states": states,
        },
    )
    provenance = write(
        candidate / "penflow/actual-ui-tree.provenance.json",
        {
            "kind": "penflow-actual-provenance",
            "version": 1,
            "sourceKind": "runtime-capture",
            "producer": {"name": "livespec-witness-browser", "version": "1"},
            "capturedAt": raw["captured_at"],
            "target": {"surface": raw["surface"]},
            "content": {"path": tree.name, "sha256": reference(tree)["sha256"]},
        },
    )
    return [*paths, tree, provenance]
