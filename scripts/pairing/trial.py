"""Pair two dedicated trial profiles via an authenticated Magic Wormhole mailbox."""
import argparse
import getpass
import ipaddress
import json
from pathlib import Path
import re
import signal
import socket

from twisted.internet import defer, task
from urllib.parse import parse_qs, urlsplit

import wormhole
from wormhole.cli.public_relay import MAILBOX_RELAY

from engine import Engine, initialize

APP_ID = "io.github.tts-empire.pairthing/trial-v1"
DEVICE = re.compile(r"[A-Z2-7]{7}(?:-[A-Z2-7]{7}){7}")


def public_relay(address):
    if not isinstance(address, str) or len(address) > 400:
        return False
    try:
        url = urlsplit(address)
        return (url.scheme == "relay" and url.port and url.username is None
                and url.password is None and url.path in ("", "/") and not url.fragment
                and ipaddress.ip_address(url.hostname).is_global
                and re.fullmatch(r"id=[A-Z2-7-]+", url.query)
                and DEVICE.fullmatch(parse_qs(url.query)["id"][0]))
    except (ValueError, TypeError, KeyError):
        return False


async def relay_hint(reactor, engine):
    if engine.endpoint == "dynamic":
        for _ in range(15):
            services = engine.request("system/status").get("connectionServiceStatus", {})
            for service in services.values():
                for address in service.get("wanAddresses") or []:
                    if public_relay(address):
                        return address
            await task.deferLater(reactor, 1, lambda: None)
    return None


async def pair(reactor, engine, owner, code, mailbox, announce, approve):
    engine.fresh()
    channel = wormhole.create(APP_ID, mailbox, reactor)
    try:
        if owner:
            channel.allocate_code(code_length=3)
            announce(await channel.get_code())
        else:
            channel.set_code(code)
        await channel.get_verifier()
        message = {"role": "owner" if owner else "join", "id": engine.identity,
                   "endpoint": engine.endpoint, "relay": await relay_hint(reactor, engine),
                   "name": socket.gethostname()[:64]}
        channel.send_message(json.dumps(message).encode())
        raw = await channel.get_message()
        if len(raw) > 1024:
            raise ValueError("Messaggio troppo grande")
        peer = json.loads(raw)
        if (peer["role"] != ("join" if owner else "owner")
                or not DEVICE.fullmatch(peer["id"]) or peer["id"] == engine.identity):
            raise ValueError("Identità del peer non valida")
        endpoint = peer["endpoint"]
        if engine.endpoint == "dynamic":
            if endpoint != "dynamic":
                raise ValueError("Indirizzo remoto non consentito")
        elif not re.fullmatch(r"tcp://127\.0\.0\.1:[0-9]{1,5}", endpoint):
            raise ValueError("Indirizzo del laboratorio non valido")
        if owner:
            if not await approve(ascii(str(peer["name"])[:64])):
                channel.send_message(b"denied")
                raise ValueError("Associazione annullata")
            channel.send_message(b"approved")
        elif await channel.get_message() != b"approved":
            raise ValueError("Autorizzazione mancante")
        addresses = [endpoint]
        if endpoint == "dynamic" and public_relay(peer.get("relay")):
            addresses.append(peer["relay"])
        # Never reopen a partially provisioned profile for synchronization.
        with engine.pending.open("x") as marker:
            marker.write(peer["id"])
        if message["relay"]:
            engine.remember_relay(message["relay"])
        engine.provision(peer["id"], addresses)
        channel.send_message(b"configured")
        if await channel.get_message() != b"configured":
            raise ValueError("Peer non configurato")
        engine.pending.replace(engine.paired)
    finally:
        await channel.close().addTimeout(5, reactor)


async def run(reactor, args):
    profile = Engine(args.profile)
    if args.action == "sync" and not profile.paired.is_file():
        raise ValueError("Completare prima il collegamento con invite o join")
    with profile as engine:
        if args.action != "sync":
            owner = args.action == "invite"
            code = None if owner else getpass.getpass("Codice Pairthing: ")
            def approve(name):
                print(f"Dispositivo {name} richiede la cartella di prova.", flush=True)
                # Read via reactor to keep the invitation timeout active.
                from twisted.internet import stdio
                from twisted.protocols.basic import LineOnlyReceiver
                answer = defer.Deferred()
                class Confirmation(LineOnlyReceiver):
                    delimiter = b"\n"
                    def lineReceived(self, line):
                        if not answer.called:
                            answer.callback(line.strip().lower() == b"si")
                print("Confermi? Scrivi si e premi Invio.", flush=True)
                transport = stdio.StandardIO(Confirmation(), reactor=reactor)
                answer.addBoth(lambda result: (transport.loseConnection(), result)[1])
                return answer
            await defer.ensureDeferred(pair(reactor, engine, owner, code, args.mailbox,
                         lambda c: print("Codice:", c, flush=True), approve)).addTimeout(600, reactor)
        print(f"Motore attivo. Cartella: {engine.files}. Ctrl+C per fermare.", flush=True)
        done = defer.Deferred()
        previous = signal.signal(signal.SIGINT, lambda *_: reactor.callFromThread(done.callback, None))
        try:
            await done
        finally:
            signal.signal(signal.SIGINT, previous)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "invite", "join", "sync"])
    parser.add_argument("profile", type=Path)
    parser.add_argument("--mailbox", default=MAILBOX_RELAY)
    args = parser.parse_args()
    if args.action == "init":
        initialize(args.profile.resolve())
    else:
        task.react(lambda r: defer.ensureDeferred(run(r, args)))
