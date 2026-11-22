"""Private JSON-lines bridge between the desktop controller and the pairing protocol."""
import json
from pathlib import Path
import sys

from twisted.internet import defer, stdio, task
from twisted.protocols.basic import LineOnlyReceiver
from wormhole.cli.public_relay import MAILBOX_RELAY

from engine import Engine, initialize
from trial import pair


class Desktop(LineOnlyReceiver):
    delimiter = b"\n"
    MAX_LENGTH = 1024

    def __init__(self, reactor, profile):
        self.reactor = reactor
        self.profile = profile
        self.engine = self.operation = self.confirmation = self.monitor = None
        self.closed = defer.Deferred()
        self.cancelling = False

    def update(self, stage, **details):
        self.stage = stage
        print(json.dumps(dict(stage=stage, **details)), flush=True)

    def connectionMade(self):
        if (self.profile / "pairing.pending").exists():
            self.update("incomplete")
        elif (self.profile / "pairing.complete").exists():
            self.start("sync", "")
        else:
            self.update("ready")

    def start(self, action, code):
        try:
            if not self.profile.exists():
                initialize(self.profile)
            self.engine = Engine(self.profile).__enter__()
            if action == "sync":
                self.begin_monitoring()
                return
            self.update("connecting")
            self.operation = defer.ensureDeferred(pair(
                self.reactor, self.engine, action == "invite", code, MAILBOX_RELAY,
                lambda value: self.update("invite", code=value), self.approve))
            self.operation.addTimeout(600, self.reactor).addCallbacks(self.begin_monitoring, self.failed)
        except Exception:
            self.failed(None)

    def approve(self, name):
        self.confirmation = defer.Deferred()
        self.update("confirm", peer=name)
        return self.confirmation

    def begin_monitoring(self, result=None):
        self.operation = None
        self.monitor = task.LoopingCall(self.status)
        self.monitor.start(3).addErrback(self.failed)

    def status(self):
        engine = self.engine
        peer = engine.paired.read_text().strip()
        link = engine.request("system/connections")["connections"].get(peer, {})
        folder = engine.request("db/status?folder=pairthing-trial")
        remote = engine.request("db/completion?folder=pairthing-trial&device=" + peer)
        device = engine.request("config/devices/" + peer)
        self.update("active", folder=str(engine.files), online=bool(link.get("connected")),
                    peer=device.get("name") or peer[:7], transport=link.get("type", ""),
                    files=folder["localFiles"], remaining=folder["needTotalItems"] + remote["needItems"],
                    scanning=folder["state"] != "idle", errors=folder.get("pullErrors", 0))

    def stop_engine(self):
        if self.monitor and self.monitor.running:
            self.monitor.stop()
        if self.engine:
            self.engine.__exit__()
            self.engine = None

    def failed(self, failure):
        self.operation = self.confirmation = None
        self.stop_engine()
        if (self.profile / "pairing.pending").exists():
            self.update("incomplete")
        elif self.cancelling:
            self.cancelling = False
            self.update("ready")
        else:
            self.update("error")

    def lineReceived(self, line):
        msg = json.loads(line)
        action = msg.get("action")
        if action in ("invite", "join", "retry") and self.stage in ("ready", "error"):
            paired = (self.profile / "pairing.complete").exists()
            if action == "retry":
                if paired:
                    self.start("sync", "")
                else:
                    self.update("ready")
            elif not paired:
                self.start(action, msg.get("code", ""))
        elif action == "approve" and self.stage == "confirm":
            answer, self.confirmation = self.confirmation, None
            self.update("connecting")
            answer.callback(True)
        elif action == "cancel" and self.operation and not self.engine.pending.exists():
            self.cancelling = True
            self.operation.cancel()

    def connectionLost(self, reason):
        if self.operation:
            self.operation.cancel()
        self.stop_engine()
        if not self.closed.called:
            self.closed.callback(None)


def main(reactor):
    bridge = Desktop(reactor, Path(sys.argv[1]).resolve())
    stdio.StandardIO(bridge, reactor=reactor)
    return bridge.closed


if __name__ == "__main__":
    task.react(main)
