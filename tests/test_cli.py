from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from circadianlight.cli import main


class CliTests(unittest.TestCase):
    def test_cli_updates_all_phase_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            output = io.StringIO()
            with redirect_stdout(output):
                result = main(
                    [
                        "--config",
                        str(path),
                        "config",
                        "--day-start",
                        "07:30",
                        "--day-temp",
                        "5000",
                        "--evening-start",
                        "20:45",
                        "--evening-temp",
                        "3500",
                        "--night-start",
                        "23:30",
                        "--night-temp",
                        "1900",
                    ]
                )

            self.assertEqual(result, 0)
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["day"], {"start": "07:30", "temperature": 5000})
            self.assertEqual(saved["evening"], {"start": "20:45", "temperature": 3500})
            self.assertEqual(saved["night"], {"start": "23:30", "temperature": 1900})

    def test_cli_rejects_temperature_outside_range(self) -> None:
        errors = io.StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stderr(errors):
            main(["config", "--night-temp", "1800"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("between 1900 and 6500 K", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
