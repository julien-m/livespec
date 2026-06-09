<!-- LiveSpec traceability anchors -->
<!-- @spec(FR-009) -->

# iOS/watchOS UI Runner (XCUITest)

<!-- @spec FR-009: developer documentation — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-009 -->

LiveSpec's built-in iOS/watchOS UI runner drives XCUITest on the iOS and watchOS simulators.
It integrates with `/spec-test --visual` to capture screenshots from `.xcresult` bundles
and compare them to baselines using the same pixelmatch engine as the web runner.

## Prerequisites

| Requirement | How to install |
|---|---|
| macOS | Required — Xcode tooling is macOS-only |
| Xcode 15+ | App Store or `xcodes install latest` |
| Xcode license | `sudo xcodebuild -license accept` |
| iOS 18 Simulator | Xcode > Settings > Platforms > iOS 18 |
| watchOS Simulator (optional) | Xcode > Settings > Platforms > watchOS |

The runner automatically skips on non-macOS hosts (Linux CI) with exit code 0.

## Setup in a Downstream Project

### Step 1 — Add UITests target

In Xcode: **File > New > Target > iOS UI Testing Bundle**.

Name it `<AppName>UITests`. Make sure the scheme includes this target under
**Test > Test Plans** (or the classic test target list).

### Step 2 — Copy the template

```bash
cp $(livespec dir)/livespec/ui-runners/xcuitest-template/LSSampleUITests.swift \
   <your-xcode-project>/UITests/LSSampleUITests.swift
```

Rename the class to match your app (e.g. `StraptUITests`).

### Step 3 — Configure ios.yaml

Add or update `livespec/ui-runners/ios.yaml` in your project root. At minimum,
set the `test_scheme` to match your Xcode scheme:

```yaml
scenarios:
  - name: default
    test_scheme: "MyAppUITests"   # ← your scheme name
    launch_arguments: []
    timeout_seconds: 300
```

### Step 4 — Run visual tests

```bash
/spec-test --visual
```

For watchOS only:

```bash
/spec-test --visual --platform=watchos
```

## Screenshot Capture Pattern

Use `XCUIScreen.main.screenshot()` with `XCTAttachment` and `lifetime = .keepAlways`:

```swift
func testCaptureHome() throws {
    let screenshot = XCUIScreen.main.screenshot()
    let attachment = XCTAttachment(screenshot: screenshot)
    attachment.name = "home"          // Used as the PNG filename
    attachment.lifetime = .keepAlways // Required — Xcode deletes passing attachments by default
    add(attachment)
}
```

Screenshots are written to `.specs/design/screens/<destination_id>/home.png`.

## Launch Arguments for State Presets

The manifest `launch_arguments` field lets you preset app state without UI navigation —
a key advantage of XCUITest over Maestro for iOS.

**ios.yaml:**
```yaml
scenarios:
  - name: logged_in
    test_scheme: MyAppUITests
    launch_arguments:
      - "--ui-test-mode"
      - "--mock-user=admin"
```

**Swift template (setUpWithError already wired):**
```swift
// The template reads XCUI_LAUNCH_ARGS automatically:
if let json = ProcessInfo.processInfo.environment["XCUI_LAUNCH_ARGS"],
   let args = try? JSONDecoder().decode([String].self, from: Data(json.utf8)) {
    app.launchArguments = args
}
```

**App code reading arguments:**
```swift
// In AppDelegate.application(_:didFinishLaunchingWithOptions:):
if CommandLine.arguments.contains("--ui-test-mode") {
    // Bypass auth, load fixture data
}
if let flag = CommandLine.arguments.first(where: { $0.hasPrefix("--mock-user=") }) {
    let user = flag.replacingOccurrences(of: "--mock-user=", with: "")
    MockDataStore.shared.setUser(user)
}
```

## Accessibility Identifiers

Use `.accessibilityIdentifier` for stable selectors that survive text changes
and localization:

```swift
// In your SwiftUI view:
Button("Submit") { ... }
    .accessibilityIdentifier("submit_button")

// In your XCUITest:
app.buttons["submit_button"].tap()    // ✅ stable
// app.buttons["Submit"].tap()       // ❌ breaks on localization
```

## Coordinated Execution with Swift Driver

When your project also has XCTest unit tests (Feature 019 Swift driver):

```bash
/spec-test            # runs XCTest unit tests + XCUITest UI tests
/spec-test --visual   # runs only XCUITest UI tests
```

Both results are merged into the unified `/spec-test` summary.

## Surfaces Integration

The `scripts/generate-surfaces.js` automatically detects iOS/watchOS projects:

```bash
# Detect and generate surfaces.yaml for an Xcode project
node scripts/generate-surfaces.js

# Append iOS surface to an existing surfaces.yaml (migration v12)
node scripts/generate-surfaces.js --migrate-native
```

Detected surface entry:
```yaml
- id: default
  name: Default
  path: .
  testDir: UITests
  runner: xcuitest
  platform: ios
```

## Troubleshooting

| Problem | Solution |
|---|---|
| `Xcode license not accepted` | `sudo xcodebuild -license accept` |
| `watchOS simulator runtime not installed` | Xcode > Settings > Platforms > install watchOS |
| `Simulator not found` | `xcrun simctl list devices` — check UDID in ios.yaml |
| `No .xcresult bundle produced` | Verify scheme includes UITests target and it runs on simulator |
| HEIC screenshots not converting to PNG | Verify macOS `sips` tool: `which sips` |
| Tests skip on CI | Expected on non-macOS hosts — exit code 0 (not a failure) |
| Xcode version mismatch | Use `xcode-select -p` to check active Xcode; use `xcodes select` to switch |
| Code signing errors on simulator | Add `CODE_SIGN_IDENTITY=""` and `CODE_SIGNING_REQUIRED=NO` to xcodebuild invocation (already done by the runner) |

## Architecture

The iOS runner consists of:

| File | Role |
|---|---|
| `validator/ui_runner_xcuitest.py` | Python orchestrator (subprocess wrapper) |
| `livespec/ui-runners/ios.yaml` | Manifest: detect rules, capabilities, destinations |
| `scripts/xcuitest-capture.sh` | Shell script for direct invocation from CI |
| `livespec/ui-runners/xcuitest-template/` | Template XCUITest target for downstream projects |

The runner mirrors the shape of `validator/ui_runner_web.py` and shares the same
`UICapabilityResult` contract.

## Reference

- Feature spec: `.specs/features/030-ui-runner-ios-watchos/spec.md`
- Implementation: `.specs/features/030-ui-runner-ios-watchos/implementation.md`
- XCUITest Apple docs: https://developer.apple.com/documentation/xctest/xcuitest
- xcrun simctl man page: `man xcrun`
