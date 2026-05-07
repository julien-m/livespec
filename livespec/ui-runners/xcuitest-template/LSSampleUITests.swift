// LSSampleUITests.swift — LiveSpec XCUITest template
//
// Copy this file into your Xcode project's UITests target to integrate with
// LiveSpec's iOS/watchOS visual testing runner (Feature 030).
//
// SETUP:
//  1. Add this file to your <AppName>UITests target in Xcode.
//  2. Configure the test scheme: Product > Scheme > Edit Scheme > Test.
//  3. Update ios.yaml scenarios.test_scheme to match your scheme name.
//
// @spec FR-005: launch_arguments injection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005
// @spec FR-002: XCUIScreen screenshot capture — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002

import XCTest

class LSSampleUITests: XCTestCase {

    // @spec FR-005: launch_arguments injection — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-005
    var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()

        // LiveSpec state preset: read launch arguments from XCUI_LAUNCH_ARGS env var.
        // The LiveSpec iOS runner serialises the `launch_arguments` field from the
        // manifest scenario as a JSON array and passes it in this environment variable.
        if let launchArgsJSON = ProcessInfo.processInfo.environment["XCUI_LAUNCH_ARGS"],
           let argsData = launchArgsJSON.data(using: .utf8),
           let args = try? JSONDecoder().decode([String].self, from: argsData) {
            app.launchArguments = args
        }

        app.launch()
    }

    override func tearDownWithError() throws {
        app = nil
    }

    // MARK: - Screenshots captured by LiveSpec visual regression

    // @spec FR-002: XCUIScreen screenshot capture — .specs/features/030-ui-runner-ios-watchos/spec.md#fr-002

    /// Capture the main screen for baseline comparison.
    ///
    /// LiveSpec extracts XCTAttachment screenshots from the .xcresult bundle.
    /// Use `lifetime = .keepAlways` so the attachment survives even when the
    /// test passes (Xcode's default is to delete passing-test attachments).
    func testCaptureMainScreen() throws {
        // TODO: navigate to the screen you want to capture
        // Example: app.tabBars.buttons["Home"].tap()

        let screenshot = XCUIScreen.main.screenshot()
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = "main_screen"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    /// Example: capture the dashboard screen.
    func testCaptureDashboard() throws {
        // TODO: navigate to dashboard
        // app.tabBars.buttons["dashboard_tab"].tap()

        let screenshot = XCUIScreen.main.screenshot()
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = "dashboard"
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    /// Example: capture with a state preset (logged-in user).
    ///
    /// In ios.yaml, declare:
    ///   scenarios:
    ///     - name: logged_in
    ///       launch_arguments: ["--ui-test-mode", "--mock-user=admin"]
    ///
    /// In your AppDelegate / @main struct, read the arguments:
    ///   if CommandLine.arguments.contains("--ui-test-mode") {
    ///       // Skip auth, load mock data, etc.
    ///   }
    func testCaptureLoggedInState() throws {
        // This test is driven by the "logged_in" scenario in ios.yaml.
        // launchArguments were already set in setUpWithError() above.

        let screenshot = XCUIScreen.main.screenshot()
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = "logged_in_main"
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
