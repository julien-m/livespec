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

    /// Capture screenshot + accessibility tree. The `.tree.txt` attachment lets
    /// `livespec ui-runner inspect` auto-correct identifiers when navigation
    /// TODOs miss their target — no manual editing required.
    ///
    /// Waits for `.runningForeground` and forces an initial hierarchy query
    /// because on iOS, app.debugDescription returns only "Query chain:" until
    /// the snapshot cache has been populated by at least one .exists call.
    private func snapshot(_ name: String) {
        if app.state != .runningForeground {
            let pred = NSPredicate(format: "state == %d",
                                   XCUIApplication.State.runningForeground.rawValue)
            let exp = expectation(for: pred, evaluatedWith: app)
            wait(for: [exp], timeout: 10.0)
        }
        _ = app.descendants(matching: .any).firstMatch.exists

        let png = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        png.name = name
        png.lifetime = .keepAlways
        add(png)

        // Dump per-kind so inspect can reliably parse buttons/cells/tabs.
        let dump = "\(app.debugDescription)\n\n=== Buttons ===\n" +
            app.buttons.allElementsBoundByIndex.map { $0.debugDescription }
                .joined(separator: "\n") +
            "\n\n=== StaticTexts ===\n" +
            app.staticTexts.allElementsBoundByIndex.map { $0.debugDescription }
                .joined(separator: "\n") +
            "\n\n=== Cells ===\n" +
            app.cells.allElementsBoundByIndex.map { $0.debugDescription }
                .joined(separator: "\n") +
            "\n\n=== TabBar ===\n" +
            app.tabBars.allElementsBoundByIndex.map { $0.debugDescription }
                .joined(separator: "\n")
        let tree = XCTAttachment(string: dump)
        tree.name = "\(name).tree.txt"
        tree.lifetime = .keepAlways
        add(tree)
    }

    /// Capture the main screen for baseline comparison.
    func testCaptureMainScreen() throws {
        // TODO: navigate to the screen you want to capture
        // Example: app.tabBars.buttons["Home"].tap()
        snapshot("main_screen")
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
