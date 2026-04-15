Feature: EC-002 — Deduplication of overlapping AC and Behavioral AC

  Background:
    Given the taxonomy document exists at system/testing/ui-behavioral-taxonomy.md
    And /spec.implement is invoked on the feature

  Scenario: Overlap between manual AC and Behavioral AC — single merged test
    Given a spec.md with:
      """
      ## Acceptance Criteria
      - AC-003: Le formulaire affiche une erreur si submit sans remplir les champs requis

      ## Behavioral AC
      - is_submittable: Submit avec champs vides doit être bloqué
      """
    When /spec.implement generates tests
    Then exactly 1 test is created covering this behavior
    And the test reference includes both IDs: "AC-003 / Behavioral-is_submittable"
    And no duplicate test exists for the same behavior

  Scenario: No overlap — distinct AC and Behavioral AC produce separate tests
    Given a spec.md with:
      """
      ## Acceptance Criteria
      - AC-001: Le bouton de submit est vert

      ## Behavioral AC
      - is_submittable: Submit avec données valides persiste les données
      """
    When /spec.implement generates tests
    Then 2 distinct tests are created
    And one test covers AC-001 (visual — button color)
    And one test covers Behavioral-is_submittable (persistence)

  Scenario: Multiple overlapping traits — each overlap merges independently
    Given a spec.md with:
      """
      ## Acceptance Criteria
      - AC-001: Le bouton affiche un spinner pendant le chargement
      - AC-002: Le formulaire bloque la soumission si les champs sont vides

      ## Behavioral AC
      - async_action: Loading state pendant l'opération asynchrone
      - is_submittable: Submit avec champs vides doit être bloqué
      """
    When /spec.implement generates tests
    Then exactly 2 tests are created (one merged per overlapping pair)
    And test 1 reference includes "AC-001 / Behavioral-async_action"
    And test 2 reference includes "AC-002 / Behavioral-is_submittable"
    And no additional duplicate tests exist

  Scenario: EC-004 — Multiple transversal patterns deduplicate shared traits
    Given a spec.md with:
      """
      ## Behavioral AC
      - form-in-modal: formulaire dans un modal avec submit et dismiss
      - async_action: le submit déclenche un appel API
      """
    When /spec.implement processes transversal pattern form-in-modal and async_action
    Then is_submittable Gherkin is injected exactly once
    And has_overlay Gherkin is injected exactly once
    And dismissible_layer Gherkin is injected exactly once
    And async_action Gherkin is injected exactly once
    And no trait appears in more than one generated test block
