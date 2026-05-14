# @spec FR-003: Flow question templates
# .specs/features/045-native-behavioral-specs/spec.md#fr-003
# @spec FR-004: Screen question templates
# .specs/features/045-native-behavioral-specs/spec.md#fr-004
# @spec FR-006: Mockup-derived non-visual subset
# .specs/features/045-native-behavioral-specs/spec.md#fr-006
"""Hard-coded interview templates for F045 native behavioral generators.

Each template maps 1-to-1 to a F044 mandatory section and is used in:

- Mode B (native interview)  — full 8-question flow or screen interview.
- Mode C (mockup-derived)   — 5-question non-visual subset for screens.

No LLM open-ended prompt is used; question wording is frozen here so that
F045 outputs remain reproducible and traceable to a fixed surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from validator.behavioral_grammar import (
    MANDATORY_FLOW_SECTIONS,
    MANDATORY_SCREEN_SECTIONS,
)


@dataclass(frozen=True)
class InterviewQuestion:
    """A single fixed-template question used by Mode B / Mode C interviews.

    Attributes:
        section_id: Canonical F044 section name (matches a heading in the
            generated artefact verbatim).
        prompt_template: Frozen, hard-coded prompt shown to the user. No
            placeholder substitution — it is a literal string.
        kind: Either ``"flow"`` or ``"screen"`` — disambiguates which
            section family the question belongs to.
    """

    section_id: str
    prompt_template: str
    kind: Literal["flow", "screen"]


# ─── Flow question templates (8, canonical order) ────────────────────────────

FLOW_QUESTIONS: tuple[InterviewQuestion, ...] = (
    InterviewQuestion(
        section_id="Acteur",
        prompt_template=(
            "Acteur — Qui déclenche ce flow ? "
            "(rôle utilisateur, système amont, cron, webhook…)"
        ),
        kind="flow",
    ),
    InterviewQuestion(
        section_id="Préconditions",
        prompt_template=(
            "Préconditions — Quel état du système doit être vrai AVANT "
            "que ce flow puisse démarrer ?"
        ),
        kind="flow",
    ),
    InterviewQuestion(
        section_id="Déclencheur",
        prompt_template=(
            "Déclencheur — Quel évènement précis lance ce flow ? "
            "(clic bouton, requête HTTP, message queue…)"
        ),
        kind="flow",
    ),
    InterviewQuestion(
        section_id="Étapes nominales",
        prompt_template=(
            "Étapes nominales — Liste numérotée des étapes du chemin "
            "heureux, sans erreurs."
        ),
        kind="flow",
    ),
    InterviewQuestion(
        section_id="Règles métier",
        prompt_template=(
            "Règles métier — Contraintes, invariants, formules ou "
            "politiques à appliquer pendant les étapes."
        ),
        kind="flow",
    ),
    InterviewQuestion(
        section_id="Erreurs & exceptions",
        prompt_template=(
            "Erreurs & exceptions — Quels échecs sont attendus et "
            "comment le flow réagit ?"
        ),
        kind="flow",
    ),
    InterviewQuestion(
        section_id="Side-effects",
        prompt_template=(
            "Side-effects — Quels effets observables hors du flow "
            "(emails, écritures DB, événements émis) ?"
        ),
        kind="flow",
    ),
    InterviewQuestion(
        section_id="Postconditions",
        prompt_template=(
            "Postconditions — Quel état du système est vrai APRÈS la "
            "réussite du flow ?"
        ),
        kind="flow",
    ),
)

# ─── Screen question templates (8, canonical order) ──────────────────────────

SCREEN_QUESTIONS: tuple[InterviewQuestion, ...] = (
    InterviewQuestion(
        section_id="Acteur",
        prompt_template=(
            "Acteur — Quel rôle voit cet écran ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Source d'entrée",
        prompt_template=(
            "Source d'entrée — D'où arrive l'utilisateur sur cet écran ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Sortie principale",
        prompt_template=(
            "Sortie principale — Quel écran ou état suit en cas de "
            "succès ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Données affichées",
        prompt_template=(
            "Données affichées — Quels champs / blocs / listes sont "
            "rendus à l'écran ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Actions",
        prompt_template=(
            "Actions — Quels boutons / interactions / raccourcis sont "
            "offerts ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Validations",
        prompt_template=(
            "Validations — Quelles règles de saisie / contraintes "
            "synchrones sont appliquées ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="États UI",
        prompt_template=(
            "États UI — Quels états visuels existent ? "
            "(loading, empty, error, populated…)"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Erreurs",
        prompt_template=(
            "Erreurs — Quels messages d'erreur peuvent s'afficher et "
            "dans quels cas ?"
        ),
        kind="screen",
    ),
)

# ─── Mode C non-visual subset (5 max) ────────────────────────────────────────

# Mode C populates visual sections from mockup analysis (or placeholder),
# and asks ONLY the canonical screen headings that still need human input:
# Acteur, Source d'entrée, Sortie principale, Validations, and Erreurs.
# `Validations` carries business rules that are not visible in the mockup,
# while `Erreurs` carries operational side-effects and failure handling. This
# preserves F044 compatibility and keeps the interview <= 5 questions.

MOCKUP_DERIVED_QUESTIONS: tuple[InterviewQuestion, ...] = (
    InterviewQuestion(
        section_id="Acteur",
        prompt_template=(
            "Acteur — Quel rôle voit cet écran ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Source d'entrée",
        prompt_template=(
            "Source d'entrée — D'où arrive l'utilisateur sur cet écran ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Sortie principale",
        prompt_template=(
            "Sortie principale — Quel écran ou état suit en cas de "
            "succès ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Validations",
        prompt_template=(
            "Validations — Quelles règles métier, contraintes ou garde-fous "
            "ne sont pas visibles dans le mockup ?"
        ),
        kind="screen",
    ),
    InterviewQuestion(
        section_id="Erreurs",
        prompt_template=(
            "Erreurs — Quels messages d'erreur, exceptions visibles ou "
            "side-effects opérationnels faut-il documenter ?"
        ),
        kind="screen",
    ),
)


# Sanity assertions — keep templates aligned with F044 v1.0 section names.
assert tuple(q.section_id for q in FLOW_QUESTIONS) == MANDATORY_FLOW_SECTIONS
assert tuple(q.section_id for q in SCREEN_QUESTIONS) == MANDATORY_SCREEN_SECTIONS
assert len(MOCKUP_DERIVED_QUESTIONS) <= 5


__all__ = [
    "FLOW_QUESTIONS",
    "MOCKUP_DERIVED_QUESTIONS",
    "SCREEN_QUESTIONS",
    "InterviewQuestion",
]
