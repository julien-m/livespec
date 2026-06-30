// PASS fixture for rust.no_expect.
fn run() {
    let value: Option<i32> = Some(1);
    let _x = value.unwrap_or_default();
}
