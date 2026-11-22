"""Drive the same private bridge used by the native window with two real engines."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile

from engine import initialize


class Client:
    async def start(self, profile):
        helper = os.environ.get("PAIRTHING_TEST_CONTROLLER")
        command = [helper] if helper else [sys.executable, str(Path(__file__).with_name("desktop.py"))]
        self.process = await asyncio.create_subprocess_exec(
            *command, str(profile),
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)

    async def until(self, stage):
        async with asyncio.timeout(70):
            while line := await self.process.stdout.readline():
                event = json.loads(line)
                print("Expected", stage, "received", event["stage"], flush=True)
                if event["stage"] == stage:
                    return event
                if event["stage"] in ("error", "incomplete"):
                    raise RuntimeError(event["stage"])
        raise RuntimeError("Worker exited")

    def send(self, action, **data):
        self.process.stdin.write(json.dumps(dict(action=action, **data)).encode() + b"\n")

    async def close(self):
        self.process.stdin.close()
        await asyncio.wait_for(self.process.wait(), timeout=20)


async def smoke():
    with tempfile.TemporaryDirectory() as tmp:
        profiles = [Path(tmp) / p for p in ("a", "b")]
        for profile in profiles:
            initialize(profile, local=True)
        a, b = Client(), Client()
        for restart in (False, True):
            await asyncio.gather(a.start(profiles[0]), b.start(profiles[1]))
            try:
                if not restart:
                    await asyncio.gather(a.until("ready"), b.until("ready"))
                    a.send("invite")
                    await a.until("invite")
                    a.send("cancel")
                    await a.until("ready")
                    a.send("invite")
                    event = await a.until("invite")
                    b.send("join", code=event["code"])
                    await a.until("confirm")
                    a.send("approve")
                await asyncio.gather(a.until("active"), b.until("active"))
                for source, dest in (profiles, profiles[::-1]):
                    name = f"{source.name}-{restart}.txt"
                    (source / "Files" / name).write_text(name)
                    async with asyncio.timeout(90):
                        path = dest / "Files" / name
                        while not path.exists() or path.read_text() != name:
                            await asyncio.sleep(1)
                print("Restart" if restart else "Pairing", "bidirectional transfer OK", flush=True)
            finally:
                await asyncio.gather(a.close(), b.close())


if __name__ == "__main__":
    asyncio.run(smoke())
