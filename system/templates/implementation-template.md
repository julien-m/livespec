# Implementation Map: [Feature Name]

> This file is the BRIDGE between spec requirements and actual code.
> It is created AFTER implementation, not before.
> **MUST be updated after every implementation or modification.**

---

## Header

- **Feature:** [Feature Name]
- **Feature Number:** NNN
- **Last Updated:** YYYY-MM-DD
- **Feature Spec:** `.specs/features/NNN-feature-name/spec.md`
- **Feature Plan:** `.specs/features/NNN-feature-name/plan.md`

---

## Status Legend

| Status | Meaning |
|---|---|
| ✅ Implemented | Fully implemented and tested |
| ⚠️ Partial | Implementation exists but incomplete or missing tests |
| ❌ Missing | No implementation found |
| 🔄 Modified | Implementation changed after initial spec — check spec conformance |

---

## Requirement Mapping

> Maps each Functional Requirement to the files and `@spec` anchor comments where it is implemented.

| Requirement | File(s) | @spec Anchor | Status | Last Verified |
|---|---|---|---|---|
| [FR-001: Fetch unread count](spec.md#fr-001) | `src/data/notifications.ts` | `@spec FR-001: Fetch unread count` | ✅ Implemented | YYYY-MM-DD |
| [FR-002: Real-time count updates](spec.md#fr-002) | `src/hooks/useNotificationSubscription.ts` | `@spec FR-002: Real-time count updates` | ✅ Implemented | YYYY-MM-DD |
| [FR-003: Mark as read on click](spec.md#fr-003) | `src/data/notifications.ts` | `@spec FR-003: Mark as read on click` | ✅ Implemented | YYYY-MM-DD |
| [FR-004: Navigate to target](spec.md#fr-004) | `src/components/notifications/NotificationItem.tsx` | `@spec FR-004: Navigate to target` | ✅ Implemented | YYYY-MM-DD |
| [FR-005: Update preferences](spec.md#fr-005) | `src/api/notifications/route.ts` | `@spec FR-005: Update preferences` | ⚠️ Partial | YYYY-MM-DD |
| [FR-006: Mark all as read](spec.md#fr-006) | — | — | ❌ Missing | YYYY-MM-DD |

**Notes:**
- FR-005 is partial: endpoint exists but preference validation is incomplete (see issue #42)
- FR-006 is not yet implemented — scheduled for next sprint

> **How `@spec` anchors work:** Place an inline comment in the source file next to the implementing function/class:
> - TypeScript/JavaScript: `// @spec FR-001: Brief description — .specs/features/NNN-feature-name/spec.md#fr-001`
> - Python: `# @spec FR-001: Brief description — .specs/features/NNN-feature-name/spec.md#fr-001`
> - SQL: `-- @spec FR-001: Brief description — .specs/features/NNN-feature-name/spec.md#fr-001`
>
> The description (after `:`) is a short summary (<50 chars) providing inline context. The `#fr-001` fragment enables deep-linking in the Markdown ecosystem. Use `grep -rn "@spec FR-001"` to locate any requirement instantly. Multiple requirements: `// @spec FR-001: Fetch count, FR-003: Mark as read — spec.md#fr-001`.

---

## Acceptance Criteria Mapping

> Maps each Acceptance Criterion to the test(s) that verify it.

| AC | Test File | Test Name | Status |
|---|---|---|---|
| [AC-001: Unread count badge](spec.md#ac-001) | `tests/api/notifications.test.ts` | `"returns unread count for user"` | ✅ Passing |
| [AC-002: Click marks read + navigates](spec.md#ac-002) | `tests/e2e/notifications.spec.ts` | `"marks notification as read on click"` | ✅ Passing |
| [AC-003: Disable email notifications](spec.md#ac-003) | `tests/api/notifications.test.ts` | `"updates email notification preference"` | ⚠️ Partial |
| [AC-004: Immediate preference effect](spec.md#ac-004) | `tests/e2e/notifications.spec.ts` | `"preference change takes effect immediately"` | ❌ Missing |
| [AC-005: Mark all as read](spec.md#ac-005) | `tests/e2e/notifications.spec.ts` | `"marks all notifications as read"` | ❌ Missing |

---

## Visual Baselines

> Playwright screenshot baselines for visual regression testing.

| Scenario | Baseline File | Last Captured | Status |
|---|---|---|---|
| Notification panel — empty state | `baselines/panel-empty.png` | YYYY-MM-DD | ✅ Active |
| Notification panel — with unread items | `baselines/panel-unread.png` | YYYY-MM-DD | ✅ Active |
| Notification bell — badge visible | `baselines/bell-badge.png` | YYYY-MM-DD | ✅ Active |
| Notification bell — no badge | `baselines/bell-no-badge.png` | YYYY-MM-DD | ✅ Active |

---

## Files Created

| File | Type | Description |
|---|---|---|
| `db/migrations/YYYYMMDD_create_notifications.sql` | Migration | Creates notifications and notification_preferences tables |
| `src/data/notifications.ts` | Data Access | Database queries for notifications |
| `src/api/notifications/route.ts` | API | REST endpoints for notification operations |
| `src/components/notifications/NotificationBell.tsx` | Component | Bell icon with unread count badge |
| `src/components/notifications/NotificationPanel.tsx` | Component | Notification list panel |
| `src/components/notifications/NotificationItem.tsx` | Component | Single notification row |
| `src/hooks/useNotificationSubscription.ts` | Hook | Real-time WebSocket subscription |
| `tests/api/notifications.test.ts` | Test | API integration tests |
| `tests/e2e/notifications.spec.ts` | Test | E2E and visual regression tests |

---

## Files Modified

| File | Change | FR/AC Impacted |
|---|---|---|
| `src/components/layout/Header.tsx` | Added NotificationBell to header | FR-001 |
| `src/types/index.ts` | Added Notification and NotificationPreference types | All |

---

## Known Gaps

> Issues discovered during implementation that deviate from spec.

| Gap | Spec Says | Code Does | Impact | Ticket |
|---|---|---|---|---|
| [Description] | [Spec requirement] | [Actual behavior] | [AC-XXX affected] | #42 |

---

*Generated by `/spec.implement` — LiveSpec v1.0*
*Must be updated by: `/spec.implement`, `/spec.check`, or manually after any code change*
