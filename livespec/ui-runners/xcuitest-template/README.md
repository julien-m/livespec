# XCUITest Template for LiveSpec

<!-- @spec FR-009: developer documentation — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-009 -->

This template integrates your Xcode project with LiveSpec's iOS/watchOS visual testing runner (Feature 030).

## Prerequisites

| Requirement | Install |
|---|---|
| Xcode 15+ | App Store or `xcodes install latest` |
| iOS 18 Simulator | Xcode > Settings > Platforms |
| watchOS Simulator (optional) | Xcode > Settings > Platforms |
| Xcode license accepted | `sudo xcodebuild -license accept` |

## Setup Steps

### 1. Add the UITests target

In Xcode:
1. File > New > Target > iOS UI Testing Bundle
2. Name it `<AppName>UITests`
3. Copy `LSSampleUITests.swift` into the target

### 2. Copy the template

```bash
cp livespec/ui-runners/xcuitest-template/LSSampleUITests.swift <path-to-your-uitests>/
```

Rename the class to match your app (e.g., `StraptUITests`).

### 3. Configure ios.yaml

LiveSpec reads `livespec/ui-runners/ios.yaml` in your project. Update the
`scenarios` block to match your Xcode scheme name:

```yaml
scenarios:
  - name: default
    test_scheme: "MyAppUITests"   # ← your scheme name here
    launch_arguments: []
    timeout_seconds: 300
```

### 4. Run visual tests

```bash
/spec-test --visual
```

The runner will:
1. Boot the configured iOS simulator (auto-boot if needed)
2. Run `xcodebuild test -scheme MyAppUITests`
3. Extract screenshots from the `.xcresult` bundle
4. Compare to baselines in `.specs/design/screens/`

## Screenshot Pattern

Use `XCUIScreen.main.screenshot()` + `XCTAttachment` with `lifetime = .keepAlways`:

```swift
func testCaptureHomeScreen() throws {
    let screenshot = XCUIScreen.main.screenshot()
    let attachment = XCTAttachment(screenshot: screenshot)
    attachment.name = "home_screen"   // ← used as the PNG filename
    attachment.lifetime = .keepAlways  // ← required so Xcode keeps it on pass
    add(attachment)
}
```

Screenshots are exported to `.specs/design/screens/<destination_id>/home_screen.png`.

## Launch Arguments for State Presets

The `launch_arguments` field in a manifest scenario is serialised as JSON and
passed via the `XCUI_LAUNCH_ARGS` environment variable. The template's
`setUpWithError()` reads it automatically.

**ios.yaml scenario:**
```yaml
scenarios:
  - name: logged_in
    test_scheme: MyAppUITests
    launch_arguments: ["--ui-test-mode", "--mock-user=admin"]
```

**AppDelegate / @main:**
```swift
if CommandLine.arguments.contains("--ui-test-mode") {
    // Skip onboarding, load fixture data, bypass auth
    UserDefaults.standard.set(true, forKey: "mockMode")
}
if let mockUser = CommandLine.arguments.first(where: { $0.hasPrefix("--mock-user=") }) {
    let user = mockUser.replacingOccurrences(of: "--mock-user=", with: "")
    // load user fixture...
}
```

## Accessibility Identifiers

Use `.accessibilityIdentifier` for stable element selectors — these survive
text changes and localization:

```swift
// In your SwiftUI view:
Button("Submit") { ... }
    .accessibilityIdentifier("submit_button")

// In your XCUITest:
app.buttons["submit_button"].tap()
// NOT: app.buttons["Submit"].tap()  ← breaks on localization
```

## watchOS Tests

Add a `watchOS Simulator` destination to `ios.yaml`:

```yaml
destinations:
  - platform: "watchOS Simulator"
    name: "Apple Watch Series 10 - 46mm"
    udid: "auto-detect"
    default: false
```

Run with `--platform=watchos`:

```bash
/spec-test --visual --platform=watchos
```

## Troubleshooting

| Problem | Solution |
|---|---|
| `Xcode license not accepted` | Run `sudo xcodebuild -license accept` |
| `watchOS simulator runtime not installed` | Xcode > Settings > Platforms > install watchOS |
| `Simulator not found` | Run `xcrun simctl list devices` to see available simulators |
| `No .xcresult bundle produced` | Check scheme has UI testing target enabled |
| HEIC screenshots not converting | Ensure macOS `sips` is available (`which sips`) |
| Tests run on non-macOS CI | Expected — runner emits a skip message and exits 0 |
