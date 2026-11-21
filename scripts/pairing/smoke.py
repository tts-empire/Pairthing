"""Two isolated Syncthing engines; real PAKE exchange, sync and persisted restart."""
import argparse
from contextlib import ExitStack
import hashlib
from pathlib import Path
import secrets
import tempfile
from twisted.internet import defer, task
from engine import Engine, initialize
from trial import pair, MAILBOX_RELAY


async def transfer(reactor, sender, receiver, filename):
    content = secrets.token_bytes(8192)
    (sender.files / filename).write_bytes(content)
    sender.request("db/scan?folder=pairthing-trial", {})
    destination = receiver.files / filename
    for _ in range(180):
        if destination.exists() and destination.read_bytes() == content:
            print(f"{filename}: SHA256 {hashlib.sha256(content).hexdigest()}", flush=True)
            return
        await task.deferLater(reactor, 1, lambda: None)
    raise RuntimeError("Trasferimento scaduto: " + filename)


async def check_refusal(reactor, a, b, mailbox, wrong_code):
    code = defer.Deferred()
    def receive(value):
        code.callback(value + "-incorrect" if wrong_code else value)
    invite = defer.ensureDeferred(pair(reactor, a, True, None, mailbox, receive,
                                        lambda _: defer.succeed(False)))
    async def join():
        await pair(reactor, b, False, await code, mailbox, None, None)
    results = await defer.DeferredList([invite, defer.ensureDeferred(join())],
                                       consumeErrors=True).addTimeout(45, reactor)
    if any(success for success, _ in results):
        raise AssertionError("Associazione accettata")
    a.fresh()
    b.fresh()
    print("Codice errato rifiutato" if wrong_code else "Conferma negata, profili intatti",
          flush=True)


async def run(reactor, mailbox, relay_only):
    with tempfile.TemporaryDirectory(prefix="pairthing-pair-") as tmp:
        profiles = [Path(tmp) / name for name in ("owner", "join")]
        for path in profiles:
            initialize(path, local=not relay_only, relay_only=relay_only)
        for restart in (False, True):
            with ExitStack() as stack:
                a, b = [stack.enter_context(Engine(path)) for path in profiles]
                if not restart:
                    await check_refusal(reactor, a, b, mailbox, True)
                    await check_refusal(reactor, a, b, mailbox, False)
                    code = defer.Deferred()
                    accept = lambda _: defer.succeed(True)
                    invite = defer.ensureDeferred(pair(reactor, a, True, None, mailbox, code.callback, accept))
                    async def join():
                        await pair(reactor, b, False, await code, mailbox, None, None)
                    await defer.gatherResults([invite, defer.ensureDeferred(join())],
                                              consumeErrors=True).addTimeout(45, reactor)
                    print("Pairing confermato sui due motori", flush=True)
                await transfer(reactor, a, b, f"forward-{int(restart)}")
                await transfer(reactor, b, a, f"reverse-{int(restart)}")
                transport = a.request("system/connections")["connections"][b.identity]["type"]
                print("Trasporto:", transport, flush=True)
                if relay_only and "relay" not in transport.lower():
                    raise AssertionError("Trasporto relay richiesto")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mailbox", default=MAILBOX_RELAY)
    parser.add_argument("--relay-only", action="store_true")
    args = parser.parse_args()
    task.react(lambda r: defer.ensureDeferred(run(r, args.mailbox, args.relay_only)))
