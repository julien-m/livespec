/* ARS-RULE-02508: ai-ressources/design/components/modals.md:120 #checklist */
export const DeleteProjectDialog = () => (
	<Dialog role="alertdialog" data-testid="delete-project-modal">
		<p>Delete project permanently?</p>
		<button>Cancel</button>
		<button>Confirm</button>
	</Dialog>
);
