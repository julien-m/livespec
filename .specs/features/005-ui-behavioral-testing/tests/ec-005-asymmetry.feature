Feature: EC-005 — Asymmetric behavior when taxonomy is missing

  # /spec.specify — fail fast (injection point, must have correct data)

  Scenario: /spec.specify fails fast when taxonomy is missing
    Given system/testing/ui-behavioral-taxonomy.md does not exist
    And the --no-behavioral flag is not used
    When /spec.specify detects UI signals in the feature description
    Then the command fails with error:
      """
      Behavioral taxonomy not found at system/testing/ui-behavioral-taxonomy.md.
      Run /spec.specify --no-behavioral or create the taxonomy first.
      """
    And no spec.md file is created or modified

  Scenario: /spec.specify with --no-behavioral skips injection when taxonomy is missing
    Given system/testing/ui-behavioral-taxonomy.md does not exist
    And the --no-behavioral flag is used
    When /spec.specify detects UI signals in the feature description
    Then Step 5.7 is skipped entirely
    And no ## Behavioral AC section is created
    And spec.md is generated normally with standard sections only

  # /spec.implement — degrade gracefully (consumer, can proceed without behavioral data)

  Scenario: /spec.implement degrades gracefully when taxonomy is missing
    Given spec.md contains a ## Behavioral AC section
    And system/testing/ui-behavioral-taxonomy.md does not exist
    When /spec.implement Phase 1 analyses the spec
    Then a WARNING is displayed:
      """
      Behavioral AC declared but taxonomy not found.
      Behavioral TDD step will be skipped.
      """
    And behavioral Step 0a is skipped
    And implementation continues normally for all other steps
    And no error is thrown

  # /spec.test — degrade gracefully (audit is additive, not blocking)

  Scenario: /spec.test degrades gracefully when taxonomy is missing
    Given spec.md contains a ## Behavioral AC section
    And system/testing/ui-behavioral-taxonomy.md does not exist
    When /spec.test Phase 1 sub-phase 1.5 runs
    Then a WARNING is displayed: "Behavioral taxonomy not found — behavioral audit skipped"
    And the structural test coverage audit continues normally
    And no behavioral gap report is produced
    And no error is thrown
