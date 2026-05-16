# LiveSpec Commands — Référence

> **Chargé à la demande par [`livespec-routing.md`](livespec-routing.md).** Ne pas charger ce fichier par défaut.

## Table — Intention → Commande

| Intention utilisateur | Commande à proposer |
|---|---|
| "Ajoute / implémente / rajoute X" (une feature) | `/spec.feature "<description>"` |
| "Ajoute plusieurs features" / "ship N features" | `/spec.ship` (interactif) ou `/spec.ship --count N` |
| "Corrige X" / "fix the UI" / écart mockup ↔ code | `/spec.fix <feature>` |
| "Teste l'interface" / "vérifie le rendu" | `/spec.test <feature>` (avec flags device/target) |
| "Vérifie que tout est aligné" / spec ↔ code | `/spec.check` |
| "Explique comment marche X" / "pourquoi a-t-on choisi Y" | `/spec.explain "<question ou feature>"` |
| "Spécifie une feature" (sans coder) | `/spec.specify "<description>"` |
| "Plan technique pour X" | `/spec.plan <feature>` |
| "Implémente depuis le plan" | `/spec.implement <feature>` |
| "Qu'est-ce qu'on devrait faire ensuite ?" | `/spec.propose` |
| "Statut du projet" / "où en est-on" | `/spec.status` |
| "Change la stack" / "ADR" | `/spec.stack change "..."` |
| "Raffine la spec / le plan" | `/spec.refine <feature> [plan]` |
| "Vérifie l'outillage / les credentials" | `/spec.preflight` |
| "Lance le projet LiveSpec" (first-time setup) | `/spec.init` |
| "Mets à jour LiveSpec" | `/spec.migrate` |
| Lifecycle hooks (before/after une commande) | `/spec.hooks <command> --create before\|after` |
| Coverage playground | `/spec.play-coverage` |
| Vérifier la sortie d'une commande | `/spec.verify-output <command>` |
| Refresh des conventions projet | `/spec.refresh-conventions` |

## Commandes — détail

### /spec.check
Vérifie l'alignement spec ↔ code et produit un rapport d'écarts.
**Usage** :
- `/spec.check` — toutes les features
- `/spec.check feature-name` — une feature ciblée
- `/spec.check --tree-only` — structure seule
- `/spec.check --quality feature` — qualité tests/code uniquement
- `/spec.check --visual-status` — dashboard gouvernance visuelle
- `/spec.check --surfaces` — détection de surface drift

### /spec.explain
Documentation vivante — comprend comment une feature marche, ou répond à une question naturelle sur l'historique du projet.
**Usage** :
- `/spec.explain notifications` — par nom de feature
- `/spec.explain 004-notifications` — par identifiant
- `/spec.explain "how do notifications work?"` — question naturelle
- `/spec.explain "why did we choose Supabase over Firebase?"` — historique de décisions
- `/spec.explain "what changed in the auth feature last month?"` — diff temporel

### /spec.feature
Pipeline complet : specify → plan → review → implement → test → commit.
**Usage** :
- `/spec.feature "User can filter search results by date range"` — pipeline interactif
- `/spec.feature "Add CSV export" --auto` — pipeline auto, zéro pause
- `/spec.feature --resume csv-export` — reprend un pipeline interrompu
- `/spec.feature "Real-time notifications" --mono` — implémentation mono-agent
- `/spec.feature "Payment" --branch --priority P1` — flags specify

### /spec.fix
Corrige les écarts détectés par `/spec.check` — corrections fonctionnelles et visuelles.
**Usage** :
- `/spec.fix` — auto-détecte feature, fixe tous les gaps
- `/spec.fix feature-name` — fixe tous les gaps d'une feature
- `/spec.fix feature-name --visual` — uniquement écarts visuels/design
- `/spec.fix feature-name --fr FR-003` — un FR ciblé
- `/spec.fix feature-name --ac AC-002` — un AC ciblé
- `/spec.fix feature-name --dry-run` — montre sans modifier
- `/spec.fix feature-name --resume` — reprend une session
- `/spec.fix --all` — toutes les features avec gaps

### /spec.hooks
Affiche, crée ou édite les lifecycle hooks d'une commande.
**Usage** :
- `/spec.hooks` — liste globale
- `/spec.hooks command-name` — hooks actifs d'une commande
- `/spec.hooks command-name --create before` — crée un hook before
- `/spec.hooks command-name --create after --global` — hook global après
- `/spec.hooks command-name --edit before --local` — édite hook local

### /spec.implement
Auto-implémente depuis un plan existant — analyze, code, test, map.
**Usage** :
- `/spec.implement` — auto-sélection depuis la roadmap
- `/spec.implement feature-name` — feature ciblée

### /spec.init
Initialise LiveSpec dans un projet via un brainstorm conversationnel 3 phases.
**Usage** :
- `/spec.init` — projet vierge
- `/spec.init --from-code` — reverse-engineering depuis un codebase existant

### /spec.migrate
Met à jour LiveSpec — compare la version projet vs repo et applique les migrations en attente.
**Usage** :
- `/spec.migrate`

### /spec.plan
Génère un plan technique avec diagrammes (sequence, state, ER).
**Usage** :
- `/spec.plan` — auto-détecte la feature courante
- `/spec.plan feature-name` — feature ciblée

### /spec.play-coverage
Ouvre le playground de coverage avec données grep live.
**Usage** :
- `/spec.play-coverage`

### /spec.preflight
Vérifie outillage, auth, credentials avant exécution autonome.
**Usage** :
- `/spec.preflight` — read-only
- `/spec.preflight --fix` — auto-install / réparation

### /spec.propose
Analyse le contexte et propose la/les prochaine(s) feature(s) à construire.
**Usage** :
- `/spec.propose` — une proposition
- `/spec.propose --count 3` — 3 features rankées par priorité
- `/spec.propose --role admin` — focus rôle admin
- `/spec.propose --mvp` — uniquement MVP-critical
- `/spec.propose --auto` — sans prompt d'action

### /spec.refine
Raffine des artefacts spec existants via conversation guidée.
**Usage** :
- `/spec.refine` — menu interactif
- `/spec.refine project` — artefacts projet
- `/spec.refine NNN` — spec d'une feature par numéro
- `/spec.refine feature-name` — spec d'une feature par nom
- `/spec.refine NNN plan` — plan d'une feature
- `/spec.refine feature-name plan` — plan d'une feature par nom

### /spec.refresh-conventions
Initialise ou rafraîchit les conventions projet depuis la stack LiveSpec (mode verbeux).
**Usage** :
- `/spec.refresh-conventions`

### /spec.ship
Autopilot batch : ship plusieurs features depuis la roadmap, bout-en-bout.
**Usage** :
- `/spec.ship` — sélection interactive (tier ou count)
- `/spec.ship --tier mvp` — toutes les features MVP
- `/spec.ship --count 3` — les 3 prochaines de la roadmap
- `/spec.ship --resume` — reprend après une feature bloquée
- `/spec.ship --tier mvp --mono` — mode mono-agent (ressources légères)

### /spec.specify
Crée une nouvelle feature spec (user stories, Mermaid, AC, FR).
**Usage** :
- `/spec.specify "User can receive real-time notifications"` — depuis idée libre
- `/spec.specify "..." --priority P1` — avec priorité
- `/spec.specify "As a designer, I want to bid on jobs"` — user story format

### /spec.stack
Affiche la stack courante, analyse l'impact d'un changement, crée des ADR.
**Usage** :
- `/spec.stack` — stack courante
- `/spec.stack change "we need Edge deployment now"` — change un composant
- `/spec.stack change "switch database to Firebase"`
- `/spec.stack decisions` — toutes les ADR
- `/spec.stack impact "switch from Supabase to Planetscale"` — dry run d'impact

### /spec.status
Vue factuelle de la roadmap et des features.
**Usage** :
- `/spec.status` — vue complète
- `/spec.status --roadmap` — roadmap uniquement
- `/spec.status --features` — table features
- `/spec.status --json` — sortie machine
- `/spec.status --json --roadmap` — combinaisons

### /spec.test
Audit coverage, génère les tests manquants, exécute la suite, vérifie la fidélité visuelle.
**Usage** :
- `/spec.test` — sélection interactive
- `/spec.test feature-name` — phases 0-5 pour une feature
- `/spec.test --all` — toutes les features implémentées
- `/spec.test --audit-only` — coverage matrix uniquement (pas de génération/exécution)
- `/spec.test --no-generate` — exécute les tests existants sans en générer
- Devices/targets pertinents — passer via la sélection interactive ou les flags surface (web, iphone, etc.)

### /spec.verify-output
Vérifie la sortie d'une commande contre ses expectations.
**Usage** :
- `/spec.verify-output <command>` — vérif basique
- `/spec.verify-output <command> --scenario "<flags>"` — un scénario précis
- `/spec.verify-output <command> --run <path>` — depuis un run existant
- `/spec.verify-output <command> --json` — sortie machine
- `/spec.verify-output <command> --feature <name>` — scopé feature
- `/spec.verify-output <command> --preview --save` — preview + sauvegarde
