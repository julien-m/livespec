<!-- @spec FR-001: Canonical behavioral grammar v1.0 reference doc — .specs/features/044-behavioral-grammar-v1-shared/spec.md#fr-001 -->
<!-- @spec FR-002: VALIDATION_RESULT enum byte-compatible with F041 — .specs/features/044-behavioral-grammar-v1-shared/spec.md#fr-002 -->

# Behavioral Specs Grammar v1.0

> **Grammar version: 1.0**
>
> Canonical, versioned reference for the behavioral specs grammar consumed by
> `/spec.init` (F041 — ingestion), `/spec.specify` (F042 — derivation),
> `/spec.sync-brainstorm` (F043 — sync), and the future native generator (F045).
>
> This file is the single source of truth. Any other file referencing the
> grammar MUST link back here; no other file may re-state or re-derive these
> rules. Changes to this file are versioned per the
> [Versioning Policy](#versioning-policy) below.

---

## Scope

This grammar covers two artefact kinds:

- **Flow** — a behavioral specification of a user-facing flow. File location convention: `.specs/flows/<slug>.md`.
- **Screen** — a behavioral specification of a single screen. File location convention: `.specs/design/screens/<name>.md`.

The validator implementation lives at `validator/behavioral_grammar.py` and exposes:

```python
from validator.behavioral_grammar import (
    validate_behavioral,
    VALIDATION_RESULT,
    ValidationOutcome,
)
```

---

## Mandatory Flow Sections

A valid flow file MUST contain the following 8 H2 sections, in this order. Each
section heading must match exactly (case, accents, spacing). A section heading
present with an empty body is treated as `FAIL` (see [Edge Cases](#edge-cases)).

| # | Section (H2) | One-line description |
|---|--------------|-----------------------|
| 1 | `## Acteur` | The primary actor (role / persona) who triggers and drives the flow. |
| 2 | `## Préconditions` | The world-state assumptions required before the flow can start. |
| 3 | `## Déclencheur` | The event or user action that initiates the flow. |
| 4 | `## Étapes nominales` | The ordered happy-path steps the actor and system perform. |
| 5 | `## Règles métier` | The domain rules and invariants enforced during the flow. |
| 6 | `## Erreurs & exceptions` | The error and exception branches and their user-facing handling. |
| 7 | `## Side-effects` | The persistent or external effects produced by the flow (DB writes, API calls, events). |
| 8 | `## Postconditions` | The world-state guaranteed after the flow ends successfully. |

**Optional flow sections** (presence is non-fatal; absence is reported as
`WARNING` if all 8 mandatory sections are present and well-formed):

- `## Notes` — free-form clarifications, open questions, follow-ups.

---

## Mandatory Screen Sections

A valid screen file MUST contain the following 8 H2 sections, in this order.

| # | Section (H2) | One-line description |
|---|--------------|-----------------------|
| 1 | `## Acteur` | The role / persona using the screen. |
| 2 | `## Source d'entrée` | How the actor arrives on this screen (entry point, navigation source). |
| 3 | `## Sortie principale` | The primary outcome the actor pursues on this screen. |
| 4 | `## Données affichées` | The data elements visible on the screen (fields, blocks, lists). |
| 5 | `## Actions` | The interactive elements (buttons, links, inputs) and their effects. |
| 6 | `## Validations` | The client-side validation rules applied on the screen's inputs. |
| 7 | `## États UI` | The discrete UI states the screen can be in (loading, empty, error, success, …). |
| 8 | `## Erreurs` | The error conditions surfaced on the screen and their user-facing messages. |

**Optional screen sections**:

- `## Side effects locaux` — local (client-side) state changes triggered by interactions.
- `## Notes` — free-form clarifications.

---

## LiveSpec Frontmatter Contract

Every imported flow or screen file under `.specs/` carries a YAML frontmatter
block prepended by `/spec.init` (F041). The contract defines exactly **3
fields**, all required.

| Field | Type | Allowed values | One-line semantics |
|-------|------|----------------|---------------------|
| `brainstormSource` | string (relative path) | any path under `.brainstorm/specs/flows/` or `.brainstorm/specs/screens/` | The brainstorm source file this LiveSpec artefact was imported from. |
| `brainstormGeneratedAt` | string (ISO-8601 datetime) | any valid ISO-8601 timestamp | The brainstorm-side generation timestamp at the moment of import (sourced verbatim from the brainstorm manifest). |
| `specStatus` | string (enum) | `fresh` \| `stale` \| `orphaned` \| `manual` | The LiveSpec lifecycle status of this artefact (see F041 / F043 for transition logic — out of scope for this doc). |

Minimal valid frontmatter block:

```yaml
---
brainstormSource: .brainstorm/specs/flows/booking.md
brainstormGeneratedAt: "2026-04-29T10:00:00Z"
specStatus: fresh
---
```

When the brainstorm source file itself starts with its own YAML frontmatter,
the LiveSpec frontmatter is prepended above it as a SEPARATE YAML block; the
source frontmatter is preserved unchanged (no field merge). This is governed
by F041 and is not enforced by `validate_behavioral` in v1.0.

---

## VALIDATION_RESULT Enum

The validator returns exactly one of three values, with the semantics below.
These semantics are **byte-compatible** with the values referenced by F041
(see `.specs/features/041-spec-init-flow-specs-ingestion/spec.md` FR-003 and
the `VALIDATION_RESULT` row in Key Entities).

| Value | Semantics |
|-------|-----------|
| `PASS` | All mandatory sections (8 for the detected kind) are present and well-formed. No documented deviation is detected. The diagnostics list is empty. The file is eligible for import. |
| `WARNING` | All mandatory sections are present and parseable, but at least one documented non-fatal deviation is detected: an optional section is missing, an extra unknown section is present, or the mandatory sections appear in the wrong order. The file remains eligible for import; deviations are surfaced for author awareness. |
| `FAIL` | At least one mandatory section is absent or unparseable, OR the file is missing/empty/unreadable, OR the frontmatter is malformed, OR the file kind cannot be detected. The file is rejected for import. The diagnostics list names every cause and cites the file path. |

No additional value is permitted in v1.0. Adding a value is a MAJOR-bump
change per the [Versioning Policy](#versioning-policy).

---

## Minimal Flow Fixture

The block below is a minimal valid flow file (frontmatter + all 8 mandatory
sections, no deviation). Copy-pasted as-is into a `.md` file under
`.specs/flows/`, it returns `VALIDATION_RESULT.PASS`.

```markdown
---
brainstormSource: .brainstorm/specs/flows/booking.md
brainstormGeneratedAt: "2026-04-29T10:00:00Z"
specStatus: fresh
---

# Flow — Réservation

## Acteur

Praticienne connectée.

## Préconditions

Compte praticienne créé et vérifié; au moins un créneau de disponibilité publié.

## Déclencheur

La praticienne clique sur "Confirmer la réservation" depuis la page créneau.

## Étapes nominales

1. Le système valide les inputs.
2. Le système enregistre la réservation.
3. Le système envoie une confirmation à l'actrice.

## Règles métier

Une réservation ne peut pas chevaucher une autre réservation existante.

## Erreurs & exceptions

Si le créneau est déjà pris, afficher "Ce créneau n'est plus disponible".

## Side-effects

Insertion d'une ligne dans `bookings`; envoi d'un email de confirmation.

## Postconditions

La réservation est visible dans le tableau de bord de la praticienne.

## Notes

Vérifier le wording exact du CTA si le produit renomme le bouton de confirmation.
```

---

## Minimal Screen Fixture

The block below is a minimal valid screen file (frontmatter + all 8 mandatory
sections, no deviation). Copy-pasted as-is into a `.md` file under
`.specs/design/screens/`, it returns `VALIDATION_RESULT.PASS`.

```markdown
---
brainstormSource: .brainstorm/specs/screens/booking_confirm.md
brainstormGeneratedAt: "2026-04-29T10:00:00Z"
specStatus: fresh
---

# Écran — Confirmation de réservation

## Acteur

Praticienne connectée.

## Source d'entrée

Clic sur "Réserver" depuis la page créneau.

## Sortie principale

Réservation confirmée et visible dans le tableau de bord.

## Données affichées

- Date et heure du créneau choisi.
- Nom du client associé.
- Bouton "Confirmer la réservation".

## Actions

| Élément | Type | Effet |
|---------|------|-------|
| Confirmer la réservation | button | POST /bookings → redirect vers le tableau de bord. |

## Validations

Le créneau doit être dans le futur.

## États UI

chargement · prêt · erreur réseau · confirmé

## Erreurs

Créneau déjà pris → "Ce créneau n'est plus disponible".

## Side effects locaux

Mise en cache locale du dernier créneau confirmé pour pré-remplir le prochain retour écran.

## Notes

Le texte d'erreur doit rester identique à celui du flow de réservation.
```

---

## Versioning Policy

The current grammar version is **v1.0**. The version is encoded in two places:

1. **Filename suffix** — this document is `system/grammar/behavioral-specs-v1.md`. A future v2 ships as a sibling file `system/grammar/behavioral-specs-v2.md`; the v1 file is left untouched so existing consumers (F041, F042, F043, F045) keep their contract intact.
2. **In-file declaration** — the line `Grammar version: 1.0` near the top of this file is the runtime check (the validator does not gate on this line in v1.0; it is the human / cross-reference anchor).

**Bump rules:**

- **MAJOR bump (v2.0):** any change that adds, removes, or renames a mandatory section; any change to the `VALIDATION_RESULT` enum (adding/removing a value, or changing the semantics of an existing value); any change to the LiveSpec frontmatter contract (adding/removing/renaming a field). MAJOR bumps ship as a sibling `-v2` file and a sibling validator module (`validator/behavioral_grammar_v2.py`). The v1 file and module are frozen.
- **MINOR bump (v1.1):** addition of a documented optional section, clarification of wording, addition of an example fixture. MINOR bumps edit the v1 file in place and bump the `Grammar version:` line.

Consumers pin the import path explicitly (`from validator.behavioral_grammar import …` for v1) and migrate to the v2 module on their own schedule.

---

## Out of Scope (v1.0)

This grammar v1.0 deliberately does NOT cover:

- Native generation of behavioral specs from interview, mockups, or brainstorm scripts (owned by F045).
- Slash commands beyond the optional thin wrapper `/spec.validate-behavioral` (deferred).
- Wiring into the `livespec validate` core dispatch (consumers call `validate_behavioral` directly).
- `specStatus` lifecycle transitions (owned by F041 / F043).

---

*Maintained under `system/grammar/`. Linked from `.specs/features/044-behavioral-grammar-v1-shared/`.*
