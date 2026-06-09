"""Mutation testing for spec validation resilience."""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Mutation:
    """A single mutation to apply to a spec tree."""

    id: str
    description: str
    category: str  # "structure" | "quality" | "semantic" | "silent"
    expected_killed_by: str  # "L1" | "L2" | "L4"


@dataclass
class MutationResult:
    """Result of applying and testing a single mutation."""

    mutation: Mutation
    killed: bool
    killed_by: str | None = None
    details: str = ""


# Immutable by convention — do not mutate at runtime
MUTATION_CATALOGUE: list[Mutation] = [
    # Structure mutations (L1 killers)
    Mutation(
        id="M-S01",
        description="Remove a required file (spec.md) from a feature directory",
        category="structure",
        expected_killed_by="L1",
    ),
    Mutation(
        id="M-S02",
        description="Rename features/ directory to an invalid name",
        category="structure",
        expected_killed_by="L1",
    ),
    Mutation(
        id="M-S03",
        description="Remove frontmatter from spec.md",
        category="structure",
        expected_killed_by="L1",
    ),
    Mutation(
        id="M-S04",
        description="Add a feature directory with invalid naming (no number prefix)",
        category="structure",
        expected_killed_by="L1",
    ),
    # Quality mutations (L2 killers)
    Mutation(
        id="M-Q01",
        description="Remove all Gherkin scenarios from spec.md",
        category="quality",
        expected_killed_by="L2",
    ),
    Mutation(
        id="M-Q02",
        description="Remove all Mermaid diagrams from plan.md",
        category="quality",
        expected_killed_by="L2",
    ),
    Mutation(
        id="M-Q03",
        description="Remove acceptance criteria section from spec.md",
        category="quality",
        expected_killed_by="L2",
    ),
    Mutation(
        id="M-Q04",
        description="Break FR anchor references in implementation.md",
        category="quality",
        expected_killed_by="L2",
    ),
    # Semantic mutations (L4 killers)
    Mutation(
        id="M-Sem01",
        description="Inject contradictory requirement into spec.md",
        category="semantic",
        expected_killed_by="L4",
    ),
    Mutation(
        id="M-Sem02",
        description="Swap polarity of a must/must-not requirement",
        category="semantic",
        expected_killed_by="L4",
    ),
    Mutation(
        id="M-Sem03",
        description="Replace a technology in stack with an incompatible alternative",
        category="semantic",
        expected_killed_by="L4",
    ),
    Mutation(
        id="M-Sem04",
        description="Duplicate a user story with subtly different acceptance criteria",
        category="semantic",
        expected_killed_by="L4",
    ),
    # Silent / limit mutations
    Mutation(
        id="M-Lim01",
        description="Add an empty section that passes structure checks",
        category="silent",
        expected_killed_by="L2",
    ),
    Mutation(
        id="M-Lim02",
        description="Add a valid-looking but semantically meaningless user story",
        category="silent",
        expected_killed_by="L4",
    ),
    Mutation(
        id="M-Lim03",
        description="Reorder features in roadmap without updating numbering",
        category="silent",
        expected_killed_by="L2",
    ),
]


def apply_mutation(mutation: Mutation, spec_path: Path, work_dir: Path) -> Path:
    """Apply a mutation to a copy of the spec tree.

    Creates a mutated copy in work_dir and returns the path to it.
    Implements real mutations for structure/quality categories.
    Stubs semantic/silent mutations that require LLM understanding.

    Args:
        mutation: Mutation descriptor to apply.
        spec_path: Root of the original spec tree.
        work_dir: Directory where the mutated copy is created.

    Returns:
        Path to the mutated spec tree root.

    Raises:
        NotImplementedError: For semantic mutations that require LLM content generation.
    """
    # Copy spec tree to work_dir
    mutated_root = work_dir / f"mutated-{mutation.id}"
    if mutated_root.exists():
        shutil.rmtree(mutated_root)
    shutil.copytree(spec_path, mutated_root)

    if mutation.id == "M-S01":
        _remove_first_spec_file(mutated_root)
    elif mutation.id == "M-S02":
        _rename_features_dir(mutated_root)
    elif mutation.id == "M-S03":
        _strip_frontmatter(mutated_root)
    elif mutation.id == "M-S04":
        _add_invalid_feature_dir(mutated_root)
    elif mutation.id == "M-Q01":
        _remove_gherkin(mutated_root)
    elif mutation.id == "M-Q02":
        _remove_mermaid(mutated_root)
    elif mutation.id == "M-Q03":
        _remove_acceptance_criteria(mutated_root)
    elif mutation.id == "M-Q04":
        _break_fr_anchors(mutated_root)
    elif mutation.id == "M-Lim01":
        _add_empty_section(mutated_root)
    elif mutation.id == "M-Lim03":
        _reorder_roadmap(mutated_root)
    else:
        # Semantic mutations require LLM — stub
        raise NotImplementedError(
            f"Mutation {mutation.id} ({mutation.category}) requires LLM-based "
            f"content generation. Install required SDKs to enable."
        )

    return mutated_root


def run_mutation_suite(specs_root: Path, work_dir: Path) -> list[MutationResult]:
    """Run all mutations in the catalogue against the spec tree.

    For each mutation: apply it, run validation layers, check if killed.

    Args:
        specs_root: Root of the spec tree to mutate.
        work_dir: Scratch directory for mutated copies (cleaned up after each run).

    Returns:
        Results for all mutations, including skipped ones.
    """
    results: list[MutationResult] = []

    for mutation in MUTATION_CATALOGUE:
        try:
            mutated_path = apply_mutation(mutation, specs_root, work_dir)
        except NotImplementedError as exc:
            results.append(
                MutationResult(
                    mutation=mutation,
                    killed=False,
                    killed_by=None,
                    details=f"Skipped: {exc}",
                )
            )
            continue

        # Run validation layers against mutated tree
        # Layer 1: structure validation
        killed = False
        killed_by = None
        details = ""

        try:
            from validator.engine import validate_all

            validation_results, _excluded = validate_all(mutated_path)
            structure_errors = [
                message for result in validation_results for message in result.errors
            ]
            if structure_errors:
                killed = True
                killed_by = "L1"
                details = f"Killed by L1: {len(structure_errors)} structure error(s)"
        except ImportError as exc:
            details = f"L1 check unavailable: {exc}"
        # Broad catch: validation layer can fail in
        # unexpected ways on mutated specs.
        except Exception as exc:
            logging.warning("L1 check failed for mutation %s: %s", mutation.id, exc)
            details = f"L1 check failed: {exc}"

        if not killed:
            try:
                from validator.coherence.rule_engine import run_coherence

                violations = run_coherence(mutated_path).violations
                if violations:
                    killed = True
                    killed_by = "L2"
                    details = f"Killed by L2: {len(violations)} coherence violation(s)"
            except ImportError as exc:
                details += f"; L2 check unavailable: {exc}"
            # Broad catch: coherence layer can fail in
            # unexpected ways on mutated specs.
            except Exception as exc:
                logging.warning("L2 check failed for mutation %s: %s", mutation.id, exc)
                details += f"; L2 check failed: {exc}"

        results.append(
            MutationResult(
                mutation=mutation,
                killed=killed,
                killed_by=killed_by,
                details=details,
            )
        )

        # Cleanup
        shutil.rmtree(mutated_path, ignore_errors=True)

    return results


def compute_mutation_score(results: list[MutationResult]) -> dict[str, float]:
    """Compute mutation kill score by category.

    Args:
        results: Mutation results from a full suite run.

    Returns:
        Dict with keys (overall, structure, quality, semantic, silent),
        each a float between 0.0 and 1.0.
    """
    by_category: dict[str, list[MutationResult]] = {}
    for r in results:
        cat = r.mutation.category
        by_category.setdefault(cat, []).append(r)

    scores: dict[str, float] = {}

    total = len(results)
    total_killed = sum(1 for r in results if r.killed)
    scores["overall"] = total_killed / total if total > 0 else 0.0

    for cat in ("structure", "quality", "semantic", "silent"):
        cat_results = by_category.get(cat, [])
        cat_total = len(cat_results)
        cat_killed = sum(1 for r in cat_results if r.killed)
        scores[cat] = cat_killed / cat_total if cat_total > 0 else 0.0

    return scores


# --- Mutation implementations ---


def _find_first_spec(root: Path) -> Path | None:
    """Find the first spec.md in features/."""
    features_dir = root / "features"
    if not features_dir.exists():
        return None
    for d in sorted(features_dir.iterdir()):
        spec = d / "spec.md"
        if spec.exists():
            return spec
    return None


def _remove_first_spec_file(root: Path) -> None:
    """M-S01: Remove spec.md from the first feature directory."""
    spec = _find_first_spec(root)
    if spec:
        spec.unlink()


def _rename_features_dir(root: Path) -> None:
    """M-S02: Rename features/ to an invalid name."""
    features_dir = root / "features"
    if features_dir.exists():
        features_dir.rename(root / "featurez")


def _strip_frontmatter(root: Path) -> None:
    """M-S03: Remove YAML frontmatter from the first spec.md."""
    spec = _find_first_spec(root)
    if not spec:
        return
    content = spec.read_text()
    if content.startswith("---"):
        # Remove everything between first and second ---
        parts = content.split("---", 2)
        if len(parts) >= 3:
            spec.write_text(parts[2].lstrip("\n"))


def _add_invalid_feature_dir(root: Path) -> None:
    """M-S04: Add a feature directory without number prefix."""
    features_dir = root / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    invalid_dir = features_dir / "no-number-prefix"
    invalid_dir.mkdir(exist_ok=True)
    (invalid_dir / "spec.md").write_text("# Invalid feature\n")


def _remove_gherkin(root: Path) -> None:
    """M-Q01: Remove all Gherkin blocks from the first spec.md."""
    spec = _find_first_spec(root)
    if not spec:
        return
    content = spec.read_text()
    # Remove ```gherkin ... ``` blocks
    cleaned = re.sub(
        r"```gherkin\s*\n.*?```",
        "<!-- gherkin removed -->",
        content,
        flags=re.DOTALL,
    )
    spec.write_text(cleaned)


def _remove_mermaid(root: Path) -> None:
    """M-Q02: Remove all Mermaid blocks from the first plan.md."""
    features_dir = root / "features"
    if not features_dir.exists():
        return
    for d in sorted(features_dir.iterdir()):
        plan = d / "plan.md"
        if plan.exists():
            content = plan.read_text()
            cleaned = re.sub(
                r"```mermaid\s*\n.*?```",
                "<!-- mermaid removed -->",
                content,
                flags=re.DOTALL,
            )
            plan.write_text(cleaned)
            return


def _remove_acceptance_criteria(root: Path) -> None:
    """M-Q03: Remove acceptance criteria section from the first spec.md."""
    spec = _find_first_spec(root)
    if not spec:
        return
    content = spec.read_text()
    # Remove ## Acceptance Criteria section up to next ## or EOF
    cleaned = re.sub(
        r"^## Acceptance Criteria\s*\n.*?(?=^## |\Z)",
        "",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )
    spec.write_text(cleaned)


def _break_fr_anchors(root: Path) -> None:
    """M-Q04: Break FR/AC anchor references in implementation.md."""
    features_dir = root / "features"
    if not features_dir.exists():
        return
    for d in sorted(features_dir.iterdir()):
        impl = d / "implementation.md"
        if impl.exists():
            content = impl.read_text()
            # Replace FR-xxx with FR-BROKEN-xxx
            broken = re.sub(r"(FR|AC)-(\d+)", r"\1-BROKEN-\2", content)
            impl.write_text(broken)
            return


def _add_empty_section(root: Path) -> None:
    """M-Lim01: Add an empty section that passes structure checks."""
    spec = _find_first_spec(root)
    if not spec:
        return
    content = spec.read_text()
    content += "\n\n## Additional Notes\n\n<!-- intentionally empty -->\n"
    spec.write_text(content)


def _reorder_roadmap(root: Path) -> None:
    """M-Lim03: Reorder features in roadmap without updating numbering."""
    roadmap = root / "roadmap.md"
    if not roadmap.exists():
        return
    content = roadmap.read_text()
    lines = content.splitlines()

    # Find checklist items and reverse their order
    checklist_indices: list[int] = []
    for i, line in enumerate(lines):
        if re.match(r"^- \[[ xX]\]", line.strip()):
            checklist_indices.append(i)

    if len(checklist_indices) >= 2:
        checklist_lines = [lines[i] for i in checklist_indices]
        checklist_lines.reverse()
        for idx, original_idx in enumerate(checklist_indices):
            lines[original_idx] = checklist_lines[idx]

    roadmap.write_text("\n".join(lines) + "\n")
