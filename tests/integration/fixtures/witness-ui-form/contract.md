# UI form witness

Implement index.html with a form, required text input `[data-semantic-id="item-name"]`,
submit button `[data-semantic-id="submit-item"]`, and success state
`[data-semantic-id="success"]`. Empty input must prevent submission and keep
success hidden. A valid input followed by submission reveals success containing
the submitted name. Preserve those semantic identifiers.
Full certification additionally requires the existing Penflow implementation
profile for feature 001-form, with current design and independent build proof.
Browser success alone is insufficient. Never fabricate Penflow reports.
