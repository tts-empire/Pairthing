#!/bin/sh
# Produce a local ad-hoc signed development app with its own controller and engine.
set -eu
cd "$(dirname "$0")/.."
if [ -x .tools/cargo/bin/cargo ]; then
    export CARGO_HOME="$PWD/.tools/cargo" RUSTUP_HOME="$PWD/.tools/rustup" PATH="$PWD/.tools/cargo/bin:$PATH"
fi
runtime="$PWD/.tools/desktop-runtime"
engine=${PAIRTHING_ENGINE:-/Applications/Syncthing.app/Contents/Resources/syncthing/syncthing}
test -x "$engine"
.tools/pair-env/bin/pyinstaller --noconfirm --onedir --name pairthing-controller \
    --collect-submodules wormhole --exclude-module wormhole.test \
    --distpath "$runtime" --workpath .tools/freeze-work --specpath .tools scripts/pairing/desktop.py
npm run tauri build -- --debug --bundles app --config '{"bundle":{"active":true}}'
bundle="$PWD/src-tauri/target/debug/bundle/macos/Pairthing.app"
mkdir -p "$bundle/Contents/Resources/runtime"
ditto "$runtime/pairthing-controller" "$bundle/Contents/Resources/runtime/pairthing-controller"
cp "$engine" "$bundle/Contents/Resources/runtime/syncthing"
xattr -cr "$bundle"
codesign --force --deep --sign - "$bundle"
codesign --verify --deep "$bundle"
echo "$bundle"
