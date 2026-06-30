// PASS fixture for rust.no_panic.
fn run() -> Result<(), String> {
    Err("recoverable".to_string())
}
