#!/bin/sh
# LiveSpec trusted Cargo runner: RUSTC_WORKSPACE_WRAPPER for workspace members.
# Instruments only libtest harness crates (rustc --test) with LLVM source-based
# coverage so the runner can observe which assertion invocations each test executed.
# Cargo hashes the wrapper into workspace artifact names, keeping these builds
# separate from ordinary `cargo test` artifacts in the same target directory.
rustc="$1"
shift
for arg in "$@"; do
  if [ "$arg" = "--test" ]; then
    exec "$rustc" "$@" -C instrument-coverage
  fi
done
exec "$rustc" "$@"
