Feature: Behavioral trait detection by /spec.specify Step 5.7

  # True positives — traits correctly detected

  Scenario: Form with submit and validation → 2 traits detected
    Given a feature description: "formulaire d'inscription avec validation email et bouton submit"
    When /spec.specify Step 5.7 analyses behavioral signals
    Then detected traits = ["is_submittable", "has_validation"]
    And ## Behavioral AC section contains Gherkin for is_submittable
    And ## Behavioral AC section contains Gherkin for has_validation
    And ## Acceptance Criteria section contains no behavioral boilerplate

  Scenario: Modal with form → transversal pattern form-in-modal detected
    Given a feature description: "modal de création contenant un formulaire avec close button"
    When /spec.specify Step 5.7 analyses behavioral signals
    Then transversal pattern detected = "form-in-modal"
    And detected traits = ["is_submittable", "has_overlay", "dismissible_layer"]
    And ## Behavioral AC section contains combined form-in-modal Gherkin

  Scenario: Async button with loading state → async_action detected
    Given a feature description: "bouton de recherche avec spinner pendant l'appel API"
    When /spec.specify Step 5.7 analyses behavioral signals
    Then detected traits = ["async_action"]
    And generated Gherkin includes: loading state scenario
    And generated Gherkin includes: double-click prevention scenario
    And generated Gherkin includes: error and retry scenario

  Scenario: Drawer with dismiss → has_overlay + dismissible_layer detected
    Given a feature description: "drawer de configuration qui s'ouvre depuis le côté droit avec bouton fermer"
    When /spec.specify Step 5.7 analyses behavioral signals
    Then detected traits include "has_overlay"
    And detected traits include "dismissible_layer"

  # True negatives — EC-001 compliance

  Scenario: "Submit" in backend context → no injection (EC-001)
    Given a feature description: "API endpoint qui submit un rapport au serveur analytics"
    When /spec.specify Step 5.7 analyses behavioral signals
    Then detected traits = []
    And no ## Behavioral AC section is created
    And spec.md structure is identical to current behavior (AC-005)

  Scenario: "Save" alone without UI context → no injection (EC-001)
    Given a feature description: "fonction qui save les données en base de données"
    When /spec.specify Step 5.7 analyses behavioral signals
    Then detected traits = []
    And no ## Behavioral AC section is created

  # Detection threshold — ≥2 signals required for ambiguous keywords

  Scenario: 1 ambiguous signal alone → no injection (below threshold)
    Given a feature description: "feature qui permet de save les préférences utilisateur"
    When /spec.specify Step 5.7 analyses behavioral signals
    Then detected traits = []
    And the reason is: "save alone without UI context (< 2 signals)"

  Scenario: 2 UI signals for ambiguous keyword → injection triggered
    Given a feature description: "page de préférences avec bouton save et validation des champs"
    When /spec.specify Step 5.7 analyses behavioral signals
    Then detected traits = ["is_submittable", "has_validation"]
    And ## Behavioral AC section is created with matching Gherkin
