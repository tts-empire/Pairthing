#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if [ -x "$PWD/.tools/cargo/bin/cargo" ]; then
    export CARGO_HOME="$PWD/.tools/cargo" RUSTUP_HOME="$PWD/.tools/rustup" PATH="$PWD/.tools/cargo/bin:$PATH"
fi
npm run build
cargo test --manifest-path src-tauri/Cargo.toml
python3 scripts/lab.py cargo test --manifest-path src-tauri/Cargo.toml lab_snapshot -- --ignored
