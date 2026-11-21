"""Exercise the real terminal entry points on macOS and in a Linux container."""
import asyncio
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


async def start(command):
    return await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE,
               stdout=asyncio.subprocess.PIPE, start_new_session=True)


async def expect(process, prefix, seconds=70):
    async with asyncio.timeout(seconds):
        while line := await process.stdout.readline():
            if line.startswith(prefix):
                return line[len(prefix):].strip()
        raise RuntimeError("Il client si è chiuso prima del messaggio previsto")


async def transfer(source, dest, name, container=None):
    content = secrets.token_bytes(4096)
    if container:
        subprocess.run(["docker", "exec", "-i", container, "python", "-c",
                        "from pathlib import Path; import sys; Path(sys.argv[1]).write_bytes(sys.stdin.buffer.read())",
                        "/test/linux/Files/" + name], input=content, check=True)
    else:
        (source / name).write_bytes(content)
    async with asyncio.timeout(200):
        while not (dest / name).exists() or (dest / name).read_bytes() != content:
            await asyncio.sleep(1)
    print("Contenuto verificato:", name, flush=True)


async def run():
    with tempfile.TemporaryDirectory(dir=Path.home(), prefix=".pairthing-test-") as tmp:
        base = Path(tmp)
        container = "pairthing-trial-" + secrets.token_hex(4)
        mac = [sys.executable, "-u", str(HERE / "trial.py")]
        linux = ["docker", "run", "--rm", "-i", "--name", container,
                 "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
                 "-v", f"{base}:/test", "pairthing-trial:local"]
        subprocess.run(mac + ["init", str(base / "mac")], check=True)
        subprocess.run(linux + ["init", "/test/linux"], check=True)
        for restart in (False, True):
            owner = await start(mac + ["sync" if restart else "invite", str(base / "mac")])
            guest = None
            try:
                code = None if restart else await expect(owner, b"Codice:")
                guest = await start(linux + ["sync" if restart else "join", "/test/linux"])
                if code:
                    guest.stdin.write(code + b"\n")
                    await expect(owner, b"Confermi?")
                    owner.stdin.write(b"si\n")
                await asyncio.gather(expect(owner, b"Motore attivo"), expect(guest, b"Motore attivo"))
                print("Client macOS e Linux attivi", flush=True)
                a, b = base / "mac/Files", base / "linux/Files"
                await transfer(a, b, f"mac-linux-{int(restart)}")
                await transfer(b, a, f"linux-mac-{int(restart)}", container)
            finally:
                if owner.returncode is None:
                    os.killpg(owner.pid, signal.SIGINT)
                if guest:
                    subprocess.run(["docker", "stop", "-t", "5", container], stdout=subprocess.DEVNULL)
                    await guest.wait()
                await owner.wait()


if __name__ == "__main__":
    asyncio.run(run())
