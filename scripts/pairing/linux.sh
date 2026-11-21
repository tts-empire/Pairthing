#!/bin/sh
# Install and run the trial in the checkout, without system-wide packages.
set -eu
umask 077
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
runtime="$here/../../.tools/linux-trial"
profile=${PAIRTHING_PROFILE:-"$HOME/Pairthing-prova"}
action=${1:-prepare}
case "$action" in prepare|join|sync) ;; *) echo "Uso: $0 [prepare|join|sync]" >&2; exit 2;; esac
[ "$(uname -s)" = Linux ] || { echo 'Questo comando è per Linux.' >&2; exit 1; }
case "$(uname -m)" in
    x86_64) arch=amd64; uvarch=x86_64; uvsum=a7fbaff2b9a271d85c1bdb540941090fd1ce011797b4abeb48e4dcd39c2471d5; stsum=2edc416e7ed136b7c858ed5f3f02a3b8316589605e54c380228ceea7acbf0142;;
    aarch64|arm64) arch=arm64; uvarch=aarch64; uvsum=0797542018e541a9288855df555c8077eed06f7a47d206362030480e8ecc9f3d; stsum=48e456690cd2b97e7d26b02b5ac35f62a3b36172267b144cfeaf02c993ab955c;;
    *) echo 'Architettura Linux non supportata.' >&2; exit 1;;
esac
mkdir -p "$runtime"
tmp=$(mktemp -d "$runtime/download.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
install_binary() {
    url=$1 member=$2 expected=$3 destination=$4
    [ ! -x "$destination" ] || return 0
    if command -v curl >/dev/null; then
        curl -fLsS --retry 2 "$url" -o "$tmp/package"
    elif command -v wget >/dev/null; then
        wget -qO "$tmp/package" "$url"
    else
        echo 'Per scaricare il runtime serve curl oppure wget.' >&2; exit 1
    fi
    echo "$expected  $tmp/package" | sha256sum -c - >/dev/null
    tar -xzOf "$tmp/package" "$member" > "$tmp/bin"
    chmod 700 "$tmp/bin"
    mv "$tmp/bin" "$destination"
}
uvpkg="uv-$uvarch-unknown-linux-gnu"
stpkg="syncthing-linux-$arch-v2.1.7"
uv="$runtime/uv-0.13.9"
export PAIRTHING_ENGINE="$runtime/syncthing-2.1.7"
install_binary "https://github.com/astral-sh/uv/releases/download/0.13.9/$uvpkg.tar.gz" "$uvpkg/uv" "$uvsum" "$uv"
install_binary "https://github.com/syncthing/syncthing/releases/download/v2.1.7/$stpkg.tar.gz" "$stpkg/syncthing" "$stsum" "$PAIRTHING_ENGINE"
export UV_PYTHON_INSTALL_DIR="$runtime/python" UV_CACHE_DIR="$runtime/cache" UV_LINK_MODE=copy
venv="$runtime/venv"
if [ ! -x "$venv/bin/python" ]; then
    "$uv" venv --managed-python --python 3.12 "$venv"
fi
"$uv" pip install --python "$venv/bin/python" -r "$here/requirements.txt"
if [ ! -e "$profile" ]; then
    "$venv/bin/python" "$here/trial.py" init "$profile"
elif [ ! -f "$profile/pairthing.json" ]; then
    echo "Percorso già occupato: $profile. Imposta PAIRTHING_PROFILE su un percorso nuovo." >&2
    exit 1
fi
if [ "$action" = prepare ]; then
    "$PAIRTHING_ENGINE" --version
    echo 'Linux pronto'
else
    "$venv/bin/python" "$here/trial.py" "$action" "$profile"
fi
