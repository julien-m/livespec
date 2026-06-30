// FAIL fixture for rust.no_unwrap.
fn run() {
    let value: Option<i32> = Some(1);
    let _x = value.unwrap();
}
