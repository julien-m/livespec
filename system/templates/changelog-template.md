# Changelog: [Feature Name]

> Per-feature changelog. An entry is added for EVERY change: implementation, bugfix, refactor, or spec update.
> This is the historical record of what was done, when, and why.

---

## Header

- **Feature:** [Feature Name]
- **Feature Number:** NNN
- **Spec:** `.specs/features/NNN-feature-name/spec.md`

---

## Entry Types

| Type | When to Use |
|---|---|
| `Feature` | New functionality implemented |
| `Bugfix` | Defect corrected |
| `Refactor` | Internal improvement, no behavior change |
| `Spec Update` | Spec document updated (may or may not include code change) |

---

## Entries

---

### 2024-03-15 — Feature: Initial implementation of notification system

- **Type:** Feature
- **Spec modified:** Yes (sections: User Scenarios, Acceptance Criteria, FR)
- **Code modified:**
  - `db/migrations/20240315_create_notifications.sql` (created)
  - `src/data/notifications.ts` (created)
  - `src/api/notifications/route.ts` (created)
  - `src/components/notifications/NotificationBell.tsx` (created)
  - `src/components/notifications/NotificationPanel.tsx` (created)
  - `src/components/notifications/NotificationItem.tsx` (created)
  - `src/hooks/useNotificationSubscription.ts` (created)
  - `src/components/layout/Header.tsx` (modified — added NotificationBell)
- **AC impacted:** AC-001, AC-002
- **Author:** claude-code
- **Notes:** Initial implementation covers P1 stories only. FR-005 (preferences) and FR-006 (mark all read) deferred to next sprint.

---

### 2024-03-18 — Bugfix: Badge count not updating on real-time notification

- **Type:** Bugfix
- **Spec modified:** No
- **Code modified:**
  - `src/hooks/useNotificationSubscription.ts` (lines 34–41)
- **AC impacted:** AC-001
- **Author:** human
- **Notes:** WebSocket event listener was not calling `setState` with updater function, causing stale closure. Fixed to use `setCount(prev => prev + 1)` pattern.

---

### 2024-03-22 — Feature: Notification preferences and mark-all-read

- **Type:** Feature
- **Spec modified:** No (spec was already correct)
- **Code modified:**
  - `src/api/notifications/route.ts` (lines 78–130, added preferences endpoints)
  - `src/data/notifications.ts` (lines 52–89, added preference queries)
  - `src/components/notifications/NotificationPanel.tsx` (added "Mark all read" button)
  - `tests/api/notifications.test.ts` (added preference tests)
  - `tests/e2e/notifications.spec.ts` (added mark-all-read E2E test)
- **AC impacted:** AC-003, AC-004, AC-005
- **Author:** claude-code
- **Notes:** Completes all P2 and P3 stories from spec. All AC now ✅.

---

### 2024-03-25 — Spec Update: Clarified edge case for notification deletion

- **Type:** Spec Update
- **Spec modified:** Yes (sections: Edge Cases — added deleted notification handling)
- **Code modified:**
  - `src/components/notifications/NotificationItem.tsx` (lines 22–31, added 404 handling)
- **AC impacted:** None (edge case, not covered by existing AC)
- **Author:** human
- **Notes:** Discovered in production that deleted notifications caused broken navigation. Spec updated to document expected behavior, code updated to handle gracefully.

---

*Updated by `/spec.implement`, `/spec.check`, or manually — LiveSpec v1.0*
