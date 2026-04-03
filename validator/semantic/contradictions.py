"""Contradiction detection between spec artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field

from validator.coherence.graph_builder import SpecGraph
from validator.coherence.violation import Severity


@dataclass
class Assertion:
    """A single extracted assertion from a spec artifact.

    Attributes:
        id: Unique identifier for the assertion.
        theme: Topic or area the assertion addresses.
        assertion_text: The actual assertion statement.
        polarity: Assertion type (must, must-not, or may).
        source_file: Path to the file containing the assertion.
        source_line: Line number where the assertion appears.
    """

    id: str
    theme: str
    assertion_text: str
    polarity: str  # "must" | "must-not" | "may"
    source_file: str
    source_line: int


@dataclass
class ContradictionResult:
    """Result of comparing two assertions.

    Attributes:
        contradicts: Whether the assertions contradict each other.
        confidence: Confidence level (0.0 to 1.0) of the contradiction determination.
        explanation: Human-readable explanation of the contradiction.
        severity: Impact level (ERROR, WARNING, or INFO).
    """

    contradicts: bool
    confidence: float
    explanation: str
    severity: Severity  # ERROR (blocking), WARNING, INFO


@dataclass
class ContradictionReport:
    """Summary of contradiction analysis across a spec tree.

    Attributes:
        pairs_checked: Total number of assertion pairs compared.
        contradictions: List of confirmed contradictions (confidence >= threshold).
        suspicions: List of potential contradictions (confidence < threshold).
    """

    pairs_checked: int
    contradictions: list[ContradictionResult] = field(default_factory=list)
    suspicions: list[ContradictionResult] = field(default_factory=list)


_EXTRACT_PROMPT = """\
You are a technical spec auditor.
Extract normative assertions from this document.
Return JSON: {{"assertions": [{{
  "id": "A1", "theme": "...", "assertion": "...",
  "polarity": "must|must-not|may", "source_line": N
}}]}}

Only extract assertions that state what MUST be,
MUST NOT be, IS required, or IS forbidden.
Skip descriptive or informational text.

Document ({source_file}):
{content}"""

_COMPARE_PROMPT = """\
These two assertions on the theme "{theme}"
come from different documents.
Are they contradictory? Answer with strict JSON:
{{"contradicts": true/false, "confidence": 0.0-1.0,
"explanation": "...", "severity": "blocking|warning|info"}}

Assertion A (from {source_a}): {text_a}
Assertion B (from {source_b}): {text_b}"""


def extract_assertions(
    content: str, source_file: str, model: str | None = None
) -> list[Assertion]:
    """Extract semantic assertions from spec content via LLM.

    Args:
        content: Raw markdown content of the spec artifact.
        source_file: Relative path used to tag each assertion's origin.
        model: Optional LLM model override.

    Returns:
        Parsed assertions with theme, polarity, and source location.

    Raises:
        json.JSONDecodeError: If the LLM response is not valid JSON.
    """
    from validator.llm_provider import call_llm

    prompt = _EXTRACT_PROMPT.format(source_file=source_file, content=content[:8000])
    schema = {
        "name": "assertions",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "assertions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "theme": {"type": "string"},
                            "assertion": {"type": "string"},
                            "polarity": {"type": "string", "enum": ["must", "must-not", "may"]},
                            "source_line": {"type": "integer"},
                        },
                        "required": ["id", "theme", "assertion", "polarity", "source_line"],
                    },
                }
            },
            "required": ["assertions"],
        },
    }

    import json
    raw = call_llm(prompt, json_schema=schema, model=model)
    data = json.loads(raw)

    return [
        Assertion(
            id=a["id"],
            theme=a["theme"],
            assertion_text=a["assertion"],
            polarity=a["polarity"],
            source_file=source_file,
            source_line=a.get("source_line", 0),
        )
        for a in data.get("assertions", [])
    ]


def compare_assertions(
    a: Assertion, b: Assertion, model: str | None = None
) -> ContradictionResult:
    """Compare two assertions for semantic contradiction via LLM.

    Args:
        a: First assertion to compare.
        b: Second assertion to compare.
        model: Optional LLM model override.

    Returns:
        Contradiction result with confidence score and severity.
    """
    from validator.llm_provider import call_llm

    prompt = _COMPARE_PROMPT.format(
        theme=a.theme,
        source_a=a.source_file,
        text_a=a.assertion_text,
        source_b=b.source_file,
        text_b=b.assertion_text,
    )
    schema = {
        "name": "contradiction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "contradicts": {"type": "boolean"},
                "confidence": {"type": "number"},
                "explanation": {"type": "string"},
                "severity": {"type": "string", "enum": ["blocking", "warning", "info"]},
            },
            "required": ["contradicts", "confidence", "explanation", "severity"],
        },
    }

    import json
    raw = call_llm(prompt, json_schema=schema, model=model)
    data = json.loads(raw)

    severity_map = {"blocking": Severity.ERROR, "warning": Severity.WARNING, "info": Severity.INFO}

    return ContradictionResult(
        contradicts=data["contradicts"],
        confidence=data["confidence"],
        explanation=data["explanation"],
        severity=severity_map.get(data["severity"], Severity.WARNING),
    )


def get_comparison_pairs(graph: SpecGraph) -> list[tuple[str, str]]:
    """Determine which file pairs need contradiction checking.

    Comparison rules:
    - constitution x every spec and plan
    - stack x every spec and plan
    - spec x plan for the same feature
    - spec x spec when features share themes (adjacent numbering as proxy)

    Args:
        graph: Parsed spec graph with feature metadata.

    Returns:
        De-duplicated list of (file_a, file_b) pairs to compare.
    """
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def _add(a: str, b: str) -> None:
        key = (min(a, b), max(a, b))
        if key not in seen and a != b:
            seen.add(key)
            pairs.append(key)

    # Global files to compare against all features
    global_files = ["constitution.md", "stacks/_default.md"]

    feature_specs: list[str] = []
    feature_plans: list[str] = []

    for feat in graph.features:
        spec_path = f"features/{feat.dir_name}/spec.md"
        plan_path = f"features/{feat.dir_name}/plan.md"

        has_spec = feat.files.get("spec", False)
        has_plan = feat.files.get("plan", False)

        if has_spec:
            feature_specs.append(spec_path)
        if has_plan:
            feature_plans.append(plan_path)

        # Rule: constitution and stack x every spec and plan
        for gf in global_files:
            if has_spec:
                _add(gf, spec_path)
            if has_plan:
                _add(gf, plan_path)

        # Rule: spec x plan for the same feature
        if has_spec and has_plan:
            _add(spec_path, plan_path)

    # Rule: spec x spec for adjacent features (shared themes proxy)
    sorted_features = sorted(graph.features, key=lambda f: f.num)
    for i in range(len(sorted_features) - 1):
        curr = sorted_features[i]
        next_feat = sorted_features[i + 1]
        if curr.files.get("spec", False) and next_feat.files.get("spec", False):
            _add(
                f"features/{curr.dir_name}/spec.md",
                f"features/{next_feat.dir_name}/spec.md",
            )

    return pairs
