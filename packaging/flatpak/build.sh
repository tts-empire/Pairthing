#!/usr/bin/env bash
set -euo pipefail
id=org.pairthing.desktop
branch=51
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user -y --noninteractive flathub "org.gnome.Sdk//$branch" "org.gnome.Platform//$branch"
flatpak build-init stage "$id" org.gnome.Sdk org.gnome.Platform "$branch"
toolchain=$(dirname "$(dirname "$(rustup which cargo)")")
flatpak build --share=network --filesystem="$PWD" --filesystem="$toolchain:ro" \
  --build-dir="$PWD" --env="CARGO_HOME=$PWD/.cargo-flatpak" stage \
  sh -ec 'export PATH="$1/bin:$PATH"; pkg-config --exists webkit2gtk-4.1; cargo build --manifest-path src-tauri/Cargo.toml --release --locked --features tauri/custom-protocol' sh "$toolchain"
install -Dm755 src-tauri/target/release/pairthing stage/files/bin/pairthing
runtime=stage/files/bin/runtime
mkdir -p "$runtime"
pyinstaller --noconfirm --onedir --name pairthing-controller --distpath "$runtime" scripts/pairing/desktop.py
case "$(uname -m)" in
  x86_64) arch=amd64; sum=2edc416e7ed136b7c858ed5f3f02a3b8316589605e54c380228ceea7acbf0142 ;;
  aarch64) arch=arm64; sum=48e456690cd2b97e7d26b02b5ac35f62a3b36172267b144cfeaf02c993ab955c ;;
  *) exit 2 ;;
esac
archive=syncthing-linux-$arch-v2.1.7
curl -fsSL --retry 3 "https://github.com/syncthing/syncthing/releases/download/v2.1.7/$archive.tar.gz" -o /tmp/engine.tgz
echo "$sum  /tmp/engine.tgz" | sha256sum -c -
tar -xzf /tmp/engine.tgz -C /tmp
install -m755 "/tmp/$archive/syncthing" "$runtime/syncthing"
mkdir -p stage/files/share/licenses/syncthing
cp /tmp/"$archive"/*.txt stage/files/share/licenses/syncthing/
install -Dm644 LICENSE stage/files/share/licenses/Pairthing.txt
install -Dm644 packaging/flatpak/$id.desktop stage/files/share/applications/$id.desktop
install -Dm644 src-tauri/icons/icon.png stage/files/share/icons/hicolor/32x32/apps/$id.png
flatpak build-finish --command=pairthing --share=network --share=ipc --socket=wayland --socket=fallback-x11 --device=dri stage
flatpak build-export repo stage stable
flatpak build-bundle --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo repo "Pairthing-$(uname -m).flatpak" "$id" stable
