"""Run a command against an ephemeral loopback-only Syncthing instance."""
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET


def main():
    binary = os.environ.get("PAIRTHING_ENGINE") or shutil.which("syncthing")
    binary = binary or "/Applications/Syncthing.app/Contents/Resources/syncthing/syncthing"
    with tempfile.TemporaryDirectory(prefix="pairthing-lab-") as folder:
        home = Path(folder)
        subprocess.run([binary, "generate", "--home", folder], check=True,
                       stdout=subprocess.DEVNULL)
        path = home / "config.xml"
        tree = ET.parse(path)
        root = tree.getroot()
        for default in root.findall("folder"):
            root.remove(default)
        options = root.find("options")
        for tag in ("globalAnnounceEnabled", "localAnnounceEnabled", "relaysEnabled",
                    "natEnabled", "urAccepted", "autoUpgradeIntervalH"):
            for node in options.findall(tag):
                node.text = "0" if tag in ("urAccepted", "autoUpgradeIntervalH") else "false"
        for node in options.findall("listenAddress"):
            options.remove(node)
        ET.SubElement(options, "listenAddress").text = "tcp://127.0.0.1:0"
        tree.write(path)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            address = "127.0.0.1:" + str(sock.getsockname()[1])
        key = secrets.token_hex(32)
        env = dict(os.environ, STGUIADDRESS="http://" + address, STGUIAPIKEY=key)
        with subprocess.Popen([binary, "serve", "--home", folder, "--no-browser",
                               "--no-restart", "--no-upgrade"], env=env,
                              stdout=subprocess.DEVNULL) as process:
            try:
                request = urllib.request.Request("http://" + address + "/rest/system/version",
                                                 headers={"X-API-Key": key})
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError("Lab engine stopped during startup")
                    try:
                        with urllib.request.urlopen(request, timeout=1) as response:
                            print("Syncthing lab:", json.load(response)["version"], flush=True)
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Lab engine startup timed out")
                if len(sys.argv) > 1:
                    subprocess.run(sys.argv[1:], check=True,
                                   env=dict(os.environ, PAIRTHING_LAB_ADDRESS=address,
                                            PAIRTHING_LAB_KEY=key))
            finally:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
