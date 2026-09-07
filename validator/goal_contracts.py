# LiveSpec traceability anchors
# @spec(FR-001)
# @spec(FR-002)
# @spec(FR-003)
# @spec(FR-004)
# @spec(FR-005)
# @spec(FR-006)
# @spec(FR-007)
# @spec(FR-009)
# @spec(FR-010)
# @spec(FR-012)
# @spec(FR-013)
# @spec(FR-014)
# @spec(FR-015)
# @spec(FR-016)
# @spec(FR-017)
# @spec(FR-018)
# @spec(FR-019)

"""Compatibility facade for deterministic goal compilation, proof, and rendering.

Helpers resolve replaceable dependencies through this module so existing API
consumers and runtime monkeypatches retain their original authority."""

from __future__ import annotations

import hashlib as hashlib
import json as json
import re as re
import shlex as shlex
from collections.abc import Mapping as Mapping
from dataclasses import dataclass as dataclass
from pathlib import Path as Path
from typing import Any as Any
from typing import TypeAlias as TypeAlias
from typing import TypedDict as TypedDict
from typing import cast as cast

from .command_registry import normalize_command_name as normalize_command_name
from .command_registry import short_command_name as short_command_name
from .conventions_gates import gates_path as gates_path
from .conventions_receipt import ConventionsReceiptError as ConventionsReceiptError
from .conventions_receipt import verify_conventions_receipt as verify_conventions_receipt
from .evidence_policy import EVIDENCE_POLICY_VERSION as EVIDENCE_POLICY_VERSION
from .evidence_policy import apply_evidence_policy as apply_evidence_policy
from .evidence_policy import contract_evidence_policy as contract_evidence_policy
from .evidence_policy import current_contract_integrity_error as current_contract_integrity_error
from .evidence_policy import strip_evidence_marker as strip_evidence_marker
from .evidence_policy import typed_evidence_missing as typed_evidence_missing
from .exceptions import ArtifactMalformed as ArtifactMalformed
from .exceptions import ExpectationsInvalid as ExpectationsInvalid
from .expectations import ExpectationsFile as ExpectationsFile
from .expectations import Rule as Rule
from .expectations import load_expectations as load_expectations
from .finalize import FinalizeReceiptError as FinalizeReceiptError
from .finalize import verify_finalize_receipt as verify_finalize_receipt
from .goal_archive_evidence import (
    _archive_run_artifact_mismatches as _archive_run_artifact_mismatches,
)
from .goal_archive_evidence import (
    _offers_tmpdir_contract_state_paths as _offers_tmpdir_contract_state_paths,
)
from .goal_archive_evidence import _validate_archive_run_evidence as _validate_archive_run_evidence
from .goal_archive_evidence import (
    _validate_finalize_receipt_evidence as _validate_finalize_receipt_evidence,
)
from .goal_compile import _compile_command_goal as _compile_command_goal
from .goal_compile import compile_command_goal as compile_command_goal
from .goal_compile import normalize_goal_flags as normalize_goal_flags
from .goal_contract_model import _CONVENTIONS_GATED_COMMANDS as _CONVENTIONS_GATED_COMMANDS
from .goal_contract_model import (
    ALLOWED_INTERNAL_INVOCATION_MODES as ALLOWED_INTERNAL_INVOCATION_MODES,
)
from .goal_contract_model import ARCHIVE_INVALID_SUBSTITUTES as ARCHIVE_INVALID_SUBSTITUTES
from .goal_contract_model import ARCHIVE_REPAIR_ACTIONS as ARCHIVE_REPAIR_ACTIONS
from .goal_contract_model import ARCHIVE_REQUIRED_EVIDENCE as ARCHIVE_REQUIRED_EVIDENCE
from .goal_contract_model import ARCHIVE_RUN_TASK_DESCRIPTION as ARCHIVE_RUN_TASK_DESCRIPTION
from .goal_contract_model import CHILD_GOAL_ARTIFACT_ROOT_MARKER as CHILD_GOAL_ARTIFACT_ROOT_MARKER
from .goal_contract_model import CONVENTION_SIGNAL_FILES as CONVENTION_SIGNAL_FILES
from .goal_contract_model import CONVENTIONS_REQUIRED_EVIDENCE as CONVENTIONS_REQUIRED_EVIDENCE
from .goal_contract_model import CONVENTIONS_VERIFY_COMMAND as CONVENTIONS_VERIFY_COMMAND
from .goal_contract_model import DESIGN_SIGNAL_WORDS as DESIGN_SIGNAL_WORDS
from .goal_contract_model import EXECUTION_TASK_BRANCHES as EXECUTION_TASK_BRANCHES
from .goal_contract_model import FINALIZE_INVALID_SUBSTITUTES as FINALIZE_INVALID_SUBSTITUTES
from .goal_contract_model import FINALIZE_REPAIR_ACTIONS as FINALIZE_REPAIR_ACTIONS
from .goal_contract_model import FINALIZE_REQUIRED_EVIDENCE as FINALIZE_REQUIRED_EVIDENCE
from .goal_contract_model import GENERIC_REPAIR_ACTIONS as GENERIC_REPAIR_ACTIONS
from .goal_contract_model import GENERIC_REQUIRED_EVIDENCE as GENERIC_REQUIRED_EVIDENCE
from .goal_contract_model import GOAL_CONTRACT_VERSION as GOAL_CONTRACT_VERSION
from .goal_contract_model import (
    HOOKS_BEFORE_INVALID_SUBSTITUTES as HOOKS_BEFORE_INVALID_SUBSTITUTES,
)
from .goal_contract_model import HOOKS_BEFORE_REPAIR_ACTIONS as HOOKS_BEFORE_REPAIR_ACTIONS
from .goal_contract_model import HOOKS_BEFORE_REQUIRED_EVIDENCE as HOOKS_BEFORE_REQUIRED_EVIDENCE
from .goal_contract_model import HOOKS_BEFORE_TASK_ID as HOOKS_BEFORE_TASK_ID
from .goal_contract_model import (
    INTERNAL_SUBAGENT_GUARD_REQUIREMENTS as INTERNAL_SUBAGENT_GUARD_REQUIREMENTS,
)
from .goal_contract_model import MARKDOWN_HORIZONTAL_RULES as MARKDOWN_HORIZONTAL_RULES
from .goal_contract_model import QE_ANALYSIS_INVALID_SUBSTITUTES as QE_ANALYSIS_INVALID_SUBSTITUTES
from .goal_contract_model import QE_ANALYSIS_MODULE_PATH as QE_ANALYSIS_MODULE_PATH
from .goal_contract_model import QE_ANALYSIS_REPAIR_ACTIONS as QE_ANALYSIS_REPAIR_ACTIONS
from .goal_contract_model import QE_ANALYSIS_REQUIRED_EVIDENCE as QE_ANALYSIS_REQUIRED_EVIDENCE
from .goal_contract_model import QE_ANALYSIS_TASK_ID as QE_ANALYSIS_TASK_ID
from .goal_contract_model import QE_NATIVE_COMMANDS as QE_NATIVE_COMMANDS
from .goal_contract_model import SPEC_CHECK_ALL_FEATURE_FLAGS as SPEC_CHECK_ALL_FEATURE_FLAGS
from .goal_contract_model import (
    VISUAL_DESIGN_INVALID_SUBSTITUTES as VISUAL_DESIGN_INVALID_SUBSTITUTES,
)
from .goal_contract_model import VISUAL_DESIGN_REPAIR_ACTIONS as VISUAL_DESIGN_REPAIR_ACTIONS
from .goal_contract_model import VISUAL_DESIGN_REQUIRED_EVIDENCE as VISUAL_DESIGN_REQUIRED_EVIDENCE
from .goal_contract_model import VISUAL_FEATURE_HEADING_RE as VISUAL_FEATURE_HEADING_RE
from .goal_contract_model import GoalContract as GoalContract
from .goal_contract_model import RequiredConventions as RequiredConventions
from .goal_contract_model import _TaskEvidenceValidation as _TaskEvidenceValidation
from .goal_conventions import _build_convention_signal_text as _build_convention_signal_text
from .goal_conventions import _canonical_json as _canonical_json
from .goal_conventions import _canonical_rules as _canonical_rules
from .goal_conventions import _compile_conventions_payload as _compile_conventions_payload
from .goal_conventions import _extract_airesources_root as _extract_airesources_root
from .goal_conventions import _normalize_section_lines as _normalize_section_lines
from .goal_conventions import _parse_convention_domains as _parse_convention_domains
from .goal_conventions import _parse_convention_refs as _parse_convention_refs
from .goal_conventions import _parse_keyword_list as _parse_keyword_list
from .goal_conventions import _render_convention_domain as _render_convention_domain
from .goal_conventions import _render_convention_file as _render_convention_file
from .goal_conventions import _resolve_convention_ref as _resolve_convention_ref
from .goal_conventions import _should_select_convention_domain as _should_select_convention_domain
from .goal_conventions import _stable_path as _stable_path
from .goal_evidence_files import _any_evidence_path_exists as _any_evidence_path_exists
from .goal_evidence_files import _child_goal_artifact_exists as _child_goal_artifact_exists
from .goal_evidence_files import _nonempty_str as _nonempty_str
from .goal_evidence_files import _path_exists as _path_exists
from .goal_evidence_files import _valid_child_goal_artifact as _valid_child_goal_artifact
from .goal_evidence_paths import confine_bootstrap_evidence as confine_bootstrap_evidence
from .goal_generic_evidence import _convention_evidence_satisfied as _convention_evidence_satisfied
from .goal_generic_evidence import (
    _conventions_receipt_missing_items as _conventions_receipt_missing_items,
)
from .goal_generic_evidence import _manifest_or_boolean_evidence as _manifest_or_boolean_evidence
from .goal_generic_evidence import _required_evidence_satisfied as _required_evidence_satisfied
from .goal_generic_evidence import _string_set_evidence as _string_set_evidence
from .goal_generic_evidence import _validate_generic_evidence as _validate_generic_evidence
from .goal_hooks import _archive_run_task as _archive_run_task
from .goal_hooks import _compile_hooks_payload as _compile_hooks_payload
from .goal_hooks import _compile_qe_analysis_payload as _compile_qe_analysis_payload
from .goal_hooks import _hooks_before_task as _hooks_before_task
from .goal_hooks import _qe_analysis_task as _qe_analysis_task
from .goal_inventory import _active_execution_task_branches as _active_execution_task_branches
from .goal_inventory import _detect_any_visual_feature as _detect_any_visual_feature
from .goal_inventory import _detect_penflow as _detect_penflow
from .goal_inventory import _detect_visual_feature as _detect_visual_feature
from .goal_inventory import _detect_visual_feature_slugs as _detect_visual_feature_slugs
from .goal_inventory import _execution_section_tasks as _execution_section_tasks
from .goal_inventory import _extract_definition_of_done as _extract_definition_of_done
from .goal_inventory import _extract_execution_tasks as _extract_execution_tasks
from .goal_inventory import _flag_names as _flag_names
from .goal_inventory import _is_all_feature_spec_check as _is_all_feature_spec_check
from .goal_inventory import _spec_has_visual_work as _spec_has_visual_work
from .goal_invocations import (
    _extract_internal_command_invocations as _extract_internal_command_invocations,
)
from .goal_invocations import (
    _is_documentary_internal_invocation_reference as _is_documentary_internal_invocation_reference,
)
from .goal_invocations import (
    _looks_like_executable_internal_invocation as _looks_like_executable_internal_invocation,
)
from .goal_invocations import _parse_internal_invocation_line as _parse_internal_invocation_line
from .goal_invocations import (
    _reject_undocumented_internal_spec_invocation as _reject_undocumented_internal_spec_invocation,
)
from .goal_invocations import (
    _validate_internal_subagent_context_guard as _validate_internal_subagent_context_guard,
)
from .goal_invocations import (
    validate_internal_command_invocation_guards as validate_internal_command_invocation_guards,
)
from .goal_json import JsonObject as JsonObject
from .goal_json import JsonValue as JsonValue
from .goal_json import copy_json_object as copy_json_object
from .goal_pairing import claims_spec_init as claims_spec_init
from .goal_pairing import validate_goal_pair as validate_goal_pair
from .goal_payload import _bind_task_review_identity as _bind_task_review_identity
from .goal_payload import _goal_expectation_payload as _goal_expectation_payload
from .goal_payload import _goal_payload as _goal_payload
from .goal_payload import _goal_rules as _goal_rules
from .goal_payload import _goal_runtime as _goal_runtime
from .goal_proof import _ensure_state_task as _ensure_state_task
from .goal_proof import _goal_proof_result as _goal_proof_result
from .goal_proof import _goal_tasks_by_id as _goal_tasks_by_id
from .goal_proof import _prove_validated_goal_task as _prove_validated_goal_task
from .goal_proof import _record_task_proof as _record_task_proof
from .goal_proof import _refresh_state_status as _refresh_state_status
from .goal_proof import _unknown_task_proof as _unknown_task_proof
from .goal_proof import _validate_task_proof as _validate_task_proof
from .goal_proof import prove_goal_task as prove_goal_task
from .goal_receipt_evidence import _nonempty_string_list as _nonempty_string_list
from .goal_receipt_evidence import _valid_qe_boundary_note as _valid_qe_boundary_note
from .goal_receipt_evidence import (
    _validate_hooks_before_evidence as _validate_hooks_before_evidence,
)
from .goal_receipt_evidence import _validate_qe_analysis_evidence as _validate_qe_analysis_evidence
from .goal_receipt_evidence import _validate_task_evidence as _validate_task_evidence
from .goal_receipt_evidence import (
    _validate_visual_receipt_evidence as _validate_visual_receipt_evidence,
)
from .goal_render import _goal_objective_context as _goal_objective_context
from .goal_render import render_goal_contract_file as render_goal_contract_file
from .goal_render import render_goal_objective as render_goal_objective
from .goal_render import render_goal_state_file as render_goal_state_file
from .goal_render import render_goal_status as render_goal_status
from .goal_task_rules import _invalid_substitutes_for_task as _invalid_substitutes_for_task
from .goal_task_rules import _repair_actions_for_task as _repair_actions_for_task
from .goal_task_rules import _required_evidence_for_task as _required_evidence_for_task
from .goal_task_rules import _slugify_task_id as _slugify_task_id
from .goal_task_rules import _task_id_for_description as _task_id_for_description
from .goal_tasks import _build_goal_tasks as _build_goal_tasks
from .goal_tasks import _goal_row_tasks as _goal_row_tasks
from .goal_tasks import _task_proof_requirements as _task_proof_requirements
from .goal_tasks import _task_required_conventions as _task_required_conventions
from .goal_tasks import _unique_task_id as _unique_task_id
from .hook_resolver import render_chain_for_stdout as render_chain_for_stdout
from .integrations import resolve_for as resolve_for
from .run_artifacts import ARCHIVE_RUN_TASK_ID as ARCHIVE_RUN_TASK_ID
from .run_artifacts import load_run_artifact as load_run_artifact
from .visual_evidence import VisualReceiptError as VisualReceiptError
from .visual_evidence import verify_visual_receipt as verify_visual_receipt
from .visual_gate import spec_declares_visual_false as spec_declares_visual_false

# Stable compatibility API retained for CLI consumers, tests and runtime monkeypatches.
__all__ = [
    "GoalContract",
    "compile_command_goal",
    "normalize_goal_flags",
    "prove_goal_task",
    "render_goal_contract_file",
    "render_goal_objective",
    "render_goal_state_file",
    "render_goal_status",
    "validate_internal_command_invocation_guards",
]
