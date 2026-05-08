---
version: 12
description: "Append native (xcuitest + maestro) surfaces to surfaces.yaml (Features 030, 031)"
date: 2026-05-08
---

# Migration v12: Native UI Runner Surfaces (iOS/watchOS + Android)

Features 030 (UI Runner iOS/watchOS) and 031 (UI Runner Android Maestro)
extended `scripts/generate-surfaces.js` to detect native UI projects and
emit `surfaces.yaml` entries with the appropriate runners:

- **iOS / watchOS** — projects containing `.xcodeproj`, `.xcworkspace`,
  or `Package.swift` get a surface with `runner: xcuitest` and
  `platform: ios` (and an additional `platform: watchos` entry when
  watchOS targets are detected).
- **Android (Maestro)** — projects containing `build.gradle`,
  `build.gradle.kts`, or `AndroidManifest.xml` together with a
  `maestro/` or `.specs/maestro/` flow directory get a surface with
  `runner: maestro` and `platform: android`.

Existing projects already on v11 have a `surfaces.yaml` that only
declares Playwright surfaces. This migration detects that legacy state
and **appends** the missing native surface(s) using the same
text-level append strategy as v11. This backward-compatibility path
exists specifically for v11 projects so existing entries (and any
user-authored comments) are preserved byte-for-byte instead of being
rewritten by a full regeneration pass. The migration is **idempotent**
— re-running on a manifest that already declares both native surfaces
is a no-op.

Projects with no native (Xcode / Gradle) markers are unaffected: the
detection finds nothing to append and the manifest stays identical.

If `.specs/surfaces.yaml` does not exist yet, the wrapper bootstraps a
fresh manifest via the standard `generate-surfaces.js` path (which is
now multi-platform aware).

## Actions

RUN migrate-native.sh
SET_VERSION 12
