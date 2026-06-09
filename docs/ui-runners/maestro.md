<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-008) -->

# Android UI Runner (Maestro)

<!-- @spec FR-008: developer documentation — .specs/features/031-ui-runner-android/spec.md#fr-008 -->

LiveSpec's built-in Android UI runner drives Maestro YAML flows on Android emulators.
It integrates with `/spec-test --visual` to run flows, capture screenshots, and compare
them to baselines using the same pixelmatch engine as the web and iOS runners.

## Prerequisites

| Requirement | How to install |
|---|---|
| Android SDK (`$ANDROID_HOME`) | [Android Studio](https://developer.android.com/studio) or `sdkmanager` standalone |
| `adb` (Android Debug Bridge) | Bundled with Android SDK platform-tools |
| `emulator` binary | Bundled with Android SDK emulator package |
| Maestro CLI | `curl -Ls https://get.maestro.mobile.dev \| bash` |
| AVD (e.g., Pixel_8_API_35) | `avdmanager create avd -n Pixel_8_API_35 -k 'system-images;android-35;google_apis;arm64-v8a'` |
| JDK 17+ | [OpenJDK / Adoptium](https://adoptium.net) |

The runner automatically skips on hosts without `ANDROID_HOME` set (e.g., Linux CI without
Android SDK) — exit code 0 (skipped, not failure).

## Setup in a Downstream Project

### Step 1 — Create Maestro flow directory

```bash
mkdir -p .specs/maestro/
```

### Step 2 — Copy the flow templates

```bash
cp $(livespec dir)/livespec/ui-runners/maestro-template/flows/*.yaml .specs/maestro/
```

Edit the copied YAML files:
- Replace `com.example.myapp` with your app's `applicationId` from `build.gradle`
- Customize the steps for your app's screens
- Add `takeScreenshot: <name>` at key moments

### Step 3 — Run visual tests

```bash
/spec-test --visual
```

For a specific device:

```bash
/spec-test --visual --device=Pixel_Tablet_API_34
```

For Wear OS (experimental):

```bash
/spec-test --visual --platform=wearos
```

## Screenshot Capture Pattern

Use `takeScreenshot: <name>` to capture named screenshots for visual regression:

```yaml
# .specs/maestro/home.yaml
appId: com.example.myapp
---
- launchApp
- waitForAnimationToEnd
- takeScreenshot: home           # Saved as home.png in .specs/design/screens/

- tapOn:
    id: "settings_tab"
- waitForAnimationToEnd
- takeScreenshot: settings       # Saved as settings.png
```

### Flows without takeScreenshot

If a flow has no `takeScreenshot` command, the runner automatically captures one
screenshot at the end of the flow using `adb shell screencap`, named `<flow_name>.png`.

## Per-Device Baselines

When running with a device override, screenshots are stored in a subdirectory:

```
.specs/design/screens/
├── home.png                     # Default device (Pixel_8_API_35)
├── settings.png
└── Pixel_Tablet_API_34/
    ├── home.png                 # Tablet-specific baseline
    └── settings.png
```

## Coordinated Execution with JVM Driver

When your project also has JVM unit tests (Feature 022 JVM driver):

```bash
/spec-test            # runs JVM driver unit tests + Maestro UI flows
/spec-test --visual   # runs only Maestro UI flows
```

Both results are merged into the unified `/spec-test` summary.

## Surfaces Integration

`scripts/generate-surfaces.js` automatically detects Android/Maestro projects:

```bash
# Detect and generate surfaces.yaml for an Android project
node scripts/generate-surfaces.js

# Append Android surface to an existing surfaces.yaml (migration v12)
node scripts/generate-surfaces.js --migrate-native
```

Detected surface entry:
```yaml
- id: default
  name: Default
  path: .
  testDir: maestro
  runner: maestro
  platform: android
```

Detection criteria in `scripts/generate-surfaces.js`:
- `build.gradle` at project root or `app/build.gradle`
- `build.gradle.kts` at project root or `app/build.gradle.kts`
- `maestro/` directory presence
- `.specs/maestro/` directory presence

## Direct Screenshot Capture

Use the capture script for quick, CI-friendly screenshot capture without running a full flow:

```bash
# Capture current emulator state
scripts/maestro-capture.sh .specs/design/screens/home.png

# Target a specific emulator serial
scripts/maestro-capture.sh .specs/design/screens/home.png emulator-5554
```

## Fail-Fast Mode

By default, a failed flow does not stop the others (AC-011). To stop on first failure:

```bash
/spec-test --visual --fail-fast
```

## Wear OS (Experimental)

Maestro has experimental Wear OS support. To target a Wear OS AVD:

```bash
/spec-test --visual --platform=wearos
```

This emits a one-line warning: `Wear OS support is experimental in Maestro — proceed with caution`.

## Troubleshooting

| Problem | Solution |
|---|---|
| `Maestro CLI not installed` | `curl -Ls https://get.maestro.mobile.dev \| bash` |
| `Android SDK not configured` | Set `ANDROID_HOME` to your Android SDK path |
| `AVD not found` | `avdmanager list avd` — verify name; create with `avdmanager create avd` |
| `ADB sees no devices` | Start emulator: `emulator -avd Pixel_8_API_35 -no-window &` |
| `Emulator boot timeout (90s)` | Check emulator binary: `$ANDROID_HOME/emulator/emulator` |
| `adb not on PATH` | Add `$ANDROID_HOME/platform-tools` to PATH |
| Tests skip on CI | Expected when `ANDROID_HOME` is not set — exit 0 (not a failure) |
| Multiple AVDs match | Runner picks first alphabetically; see EC-001 in spec |

## Architecture

The Android runner consists of:

| File | Role |
|---|---|
| `validator/ui_runner_maestro.py` | Python orchestrator (subprocess wrapper) |
| `livespec/ui-runners/android.yaml` | Manifest: detect rules, capabilities, destinations |
| `scripts/maestro-capture.sh` | Shell script for direct adb screenshot capture |
| `livespec/ui-runners/maestro-template/` | Template Maestro flows for downstream projects |

The runner mirrors the shape of `validator/ui_runner_xcuitest.py` and shares the same
`UICapabilityResult` contract and pixelmatch comparison engine.

## Reference

- Feature spec: [`.specs/features/031-ui-runner-android/spec.md`](../../.specs/features/031-ui-runner-android/spec.md)
- Maestro docs: https://maestro.mobile.dev
- adb reference: `adb --help`
- Android Emulator docs: https://developer.android.com/studio/run/emulator-commandline
