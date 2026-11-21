import json
from pathlib import Path
import tempfile
import unittest

from engine import Engine, initialize
from trial import public_relay


class TrialTests(unittest.TestCase):
    def test_relay_hint_requires_public_ip_and_device_id(self):
        identity = "-".join(["AAAAAAA"] * 8)
        template = "relay://{}:22067/?id=" + identity
        self.assertTrue(public_relay(template.format("1.1.1.1")))
        for host in ("127.0.0.1", "192.168.1.1", "[::1]", "router.local", "login@1.1.1.1"):
            self.assertFalse(public_relay(template.format(host)))
        self.assertFalse(public_relay("relay://1.1.1.1:22067/?id=invalid"))

    def test_interrupted_pairing_prevents_engine_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pairthing.json").write_text(json.dumps({"endpoint": "dynamic"}))
            (root / "pairing.pending").touch()
            engine = Engine(root)
            with self.assertRaisesRegex(RuntimeError, "interrotta"):
                with engine:
                    self.fail("Motore riavviato con provisioning incompleto")
            self.assertIsNone(engine.process)

    def test_init_preserves_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(FileExistsError):
                initialize(root)
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
