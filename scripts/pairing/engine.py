"""Dedicated Syncthing profile for the two-computer feasibility trial."""
import json
import os
import secrets
import shutil
import socket
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


def binary():
    return (os.environ.get("PAIRTHING_ENGINE") or shutil.which("syncthing")
            or "/Applications/Syncthing.app/Contents/Resources/syncthing/syncthing")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def initialize(root, local=False, relay_only=False):
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    home = root / "engine"
    subprocess.run([binary(), "generate", "--home", str(home)], check=True,
                   stdout=subprocess.DEVNULL)
    path = home / "config.xml"
    tree = ET.parse(path)
    for folder in tree.findall("folder"):
        tree.getroot().remove(folder)
    gui = tree.find("gui")
    gui.set("tls", "false")
    gui.find("address").text = f"127.0.0.1:{free_port()}"
    options = tree.find("options")
    for tag, value in {"autoUpgradeIntervalH": "0", "urAccepted": "-1"}.items():
        options.find(tag).text = value
    endpoint = "dynamic"
    if local:
        endpoint = f"tcp://127.0.0.1:{free_port()}"
        for elem in options.findall("listenAddress"):
            options.remove(elem)
        ET.SubElement(options, "listenAddress").text = endpoint
        for tag in ("globalAnnounceEnabled", "localAnnounceEnabled", "relaysEnabled", "natEnabled"):
            options.find(tag).text = "false"
    if relay_only:
        for elem in options.findall("listenAddress"):
            options.remove(elem)
        ET.SubElement(options, "listenAddress").text = "dynamic+https://relays.syncthing.net/endpoint"
        options.find("localAnnounceEnabled").text = "false"
        options.find("natEnabled").text = "false"
    tree.write(path)
    (root / "Files").mkdir(mode=0o700)
    (root / "pairthing.json").write_text(json.dumps({"endpoint": endpoint}))


class Engine:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.endpoint = json.loads((self.root / "pairthing.json").read_text())["endpoint"]
        self.files = self.root / "Files"
        self.pending = self.root / "pairing.pending"
        self.paired = self.root / "pairing.complete"
        self.key = secrets.token_hex(32)
        self.address = f"127.0.0.1:{free_port()}"
        self.process = None

    def request(self, path, body=None, method=None):
        req = urllib.request.Request(f"http://{self.address}/rest/{path}",
              headers={"X-API-Key": self.key, "Content-Type": "application/json"},
              data=None if body is None else json.dumps(body).encode(), method=method)
        with urllib.request.urlopen(req, timeout=3) as response:
            raw = response.read()
            return json.loads(raw) if raw.strip() else None

    def __enter__(self):
        if self.pending.exists():
            raise RuntimeError("Associazione interrotta: conservare Files e iniziare con un profilo nuovo")
        env = dict(os.environ, STGUIADDRESS="http://" + self.address, STGUIAPIKEY=self.key)
        self.process = subprocess.Popen([binary(), "serve", "--home", str(self.root / "engine"),
                     "--no-browser", "--no-restart", "--no-upgrade"], env=env,
                     stdout=subprocess.DEVNULL)
        try:
            for _ in range(100):
                if self.process.poll() is not None:
                    raise RuntimeError("Il motore di prova si è fermato")
                try:
                    self.identity = self.request("system/status")["myID"]
                    return self
                except OSError:
                    time.sleep(.1)
            raise RuntimeError("Avvio motore scaduto")
        except BaseException:
            self.__exit__()
            raise

    def __exit__(self, *exc):
        self.process.terminate()
        self.process.wait(timeout=15)

    def fresh(self):
        if self.request("config/folders") or any(
            d["deviceID"] != self.identity for d in self.request("config/devices")
        ):
            raise ValueError("Profilo già associato: usare il comando sync")

    def remember_relay(self, relay):
        # Keep this relay reachable after restart while retaining upstream discovery.
        options = self.request("config/options")
        listeners = options["listenAddresses"]
        if relay not in listeners:
            self.request("config/options", {"listenAddresses": [*listeners, relay]}, method="PATCH")

    def provision(self, peer, addresses):
        self.fresh()
        device = self.request("config/defaults/device")
        device.update(deviceID=peer, addresses=addresses, autoAcceptFolders=False)
        folder = self.request("config/defaults/folder")
        folder.update(id="pairthing-trial", label="Pairthing", path=str(self.files),
                      rescanIntervalS=20,
                      devices=[{"deviceID": self.identity}, {"deviceID": peer}])
        self.request("config/devices", device)
        self.request("config/folders", folder)
        actual = self.request("config/folders/pairthing-trial")
        if {d["deviceID"] for d in actual["devices"]} != {peer, self.identity}:
            raise RuntimeError("Provisioning incompleto")
