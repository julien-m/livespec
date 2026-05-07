# LiveSpec Maestro Flow Template

<!-- @spec FR-008: Maestro flow conventions — .specs/features/031-ui-runner-android/spec.md#fr-008 -->

This directory contains Maestro YAML flow templates for Android UI testing with LiveSpec.

## Quick Start

1. **Copy flows to your project:**
   ```bash
   mkdir -p .specs/maestro/
   cp <livespec-dir>/livespec/ui-runners/maestro-template/flows/*.yaml .specs/maestro/
   ```

2. **Edit the flows** — replace `com.example.myapp` with your app's package name
   and customize the steps for your UI.

3. **Run visual tests:**
   ```bash
   /spec.test --visual
   ```

LiveSpec automatically discovers all `.yaml` files in `.specs/maestro/` and
runs them sequentially on the configured Android emulator.

---

## Directory Layout

```
your-project/
├── .specs/
│   ├── maestro/               ← LiveSpec-style flow directory (preferred)
│   │   ├── home.yaml
│   │   ├── checkout.yaml
│   │   └── settings.yaml
│   └── surfaces.yaml
└── build.gradle.kts
```

Alternatively, place flows in a top-level `maestro/` directory:

```
your-project/
├── maestro/                   ← Alternative flow directory
│   └── home.yaml
└── build.gradle.kts
```

---

## Maestro Syntax Basics

### Launch and navigate

```yaml
appId: com.example.myapp
---
- launchApp
- waitForAnimationToEnd
- tapOn:
    id: "my_button_id"
```

### Assertions

```yaml
- assertVisible:
    id: "dashboard_title"

- assertVisible:
    text: "Welcome back"
```

### Screenshot capture (for LiveSpec baselines)

```yaml
# Named screenshot — LiveSpec uses this name for the PNG file
- takeScreenshot: dashboard

# Multiple screenshots in one flow
- takeScreenshot: logged_in_state
- tapOn: "Settings"
- takeScreenshot: settings_screen
```

### Parameterization

```yaml
env:
  USER_EMAIL: ${USER_EMAIL}
---
- launchApp
- tapOn:
    id: "email_field"
- inputText: ${USER_EMAIL}
```

---

## Integration with surfaces.yaml

When `generate-surfaces.js` detects an Android project with Maestro flows,
it automatically creates a surface entry:

```yaml
# .specs/surfaces.yaml (auto-generated)
surfaces:
  - id: default
    name: Default
    path: .
    testDir: .specs/maestro
    runner: maestro
    platform: android
```

To add the Android surface to an existing `surfaces.yaml`:

```bash
node scripts/generate-surfaces.js --migrate-native
```

---

## Configuration (android.yaml)

The default AVD and timeout are configured in `livespec/ui-runners/android.yaml`.
To override for your project, copy and adjust the manifest:

```yaml
# Project-level override in your project root
runner:
  id: maestro

scenarios:
  - name: default
    avd_name: Pixel_8_API_35     # Change to your AVD name
    fail_fast: false
    timeout_seconds: 300
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Maestro CLI not installed` | `curl -Ls https://get.maestro.mobile.dev \| bash` |
| `Android SDK not configured` | Set `ANDROID_HOME` to your SDK path |
| `AVD not found` | Run `avdmanager list avd` to see available AVDs |
| `adb sees no devices` | Start emulator: `emulator -avd Pixel_8_API_35 -no-window &` |
| `Emulator boot timeout` | Check `$ANDROID_HOME/emulator/emulator` is executable |
| Wear OS flows | Add `--platform=wearos` flag — support is experimental |

---

## Resources

- [Maestro documentation](https://maestro.mobile.dev)
- [Maestro YAML reference](https://maestro.mobile.dev/api-reference/commands)
- [Feature spec](../../.specs/features/031-ui-runner-android/spec.md)
- [Maestro developer guide](../../docs/ui-runners/maestro.md)
