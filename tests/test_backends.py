from pathlib import Path
import subprocess
import tempfile
import unittest

from fluxway.backends import GammastepBackend, GnomeBackend


class RecordingRunner:
    def __init__(self):
        self.commands: list[tuple[str, ...]] = []
        self.values = {
            "night-light-enabled": "false",
            "night-light-schedule-automatic": "true",
            "night-light-schedule-from": "20.0",
            "night-light-schedule-to": "6.0",
            "night-light-temperature": "uint32 2700",
        }

    def __call__(self, command):
        command = tuple(command)
        self.commands.append(command)
        if command[1] == "get":
            output = self.values[command[-1]] + "\n"
        else:
            output = ""
        return subprocess.CompletedProcess(command, 0, output, "")


class BackendTests(unittest.TestCase):
    def test_gnome_prepares_applies_and_restores_settings(self) -> None:
        runner = RecordingRunner()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            backend = GnomeBackend(state, runner)

            backend.prepare()
            backend.apply(3650)
            self.assertTrue(state.exists())
            self.assertIn(
                ("gsettings", "set", backend.schema, "night-light-temperature", "3650"),
                runner.commands,
            )

            backend.reset()
            self.assertFalse(state.exists())
            self.assertIn(
                (
                    "gsettings",
                    "set",
                    backend.schema,
                    "night-light-temperature",
                    "uint32 2700",
                ),
                runner.commands,
            )

    def test_gammastep_uses_requested_adjustment_method(self) -> None:
        runner = RecordingRunner()
        backend = GammastepBackend("wayland", runner)

        backend.apply(2500)
        backend.reset()

        self.assertEqual(
            runner.commands,
            [
                ("gammastep", "-m", "wayland", "-P", "-O", "2500"),
                ("gammastep", "-m", "wayland", "-x"),
            ],
        )


if __name__ == "__main__":
    unittest.main()

