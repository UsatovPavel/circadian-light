from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

from circadianlight.config import (
    Config,
    ConfigError,
    Phase,
    default_config_path,
    default_state_path,
    load_config,
    migrate_legacy_files,
    save_config,
)


class ConfigTests(unittest.TestCase):
    def test_defaults_match_agent_66(self) -> None:
        config = Config()

        self.assertEqual((config.day.start, config.day.temperature), ("08:00", 4750))
        self.assertEqual((config.evening.start, config.evening.temperature), ("21:30", 3650))
        self.assertEqual((config.night.start, config.night.temperature), ("00:00", 2500))

    def test_temperature_range_is_enforced(self) -> None:
        with self.assertRaisesRegex(ConfigError, "between 1900 K and 6500 K"):
            Config(day=Phase("08:00", 1899)).validate()
        with self.assertRaisesRegex(ConfigError, "between 1900 K and 6500 K"):
            Config(night=Phase("00:00", 6501)).validate()

    def test_time_format_and_unique_starts_are_enforced(self) -> None:
        with self.assertRaisesRegex(ConfigError, "HH:MM"):
            Config(day=Phase("8:00", 4750)).validate()
        with self.assertRaisesRegex(ConfigError, "must be unique"):
            Config(evening=Phase("08:00", 3650)).validate()

    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            expected = Config(transition_minutes=45, backend="gammastep")
            save_config(expected, path)

            self.assertEqual(load_config(path), expected)

    def test_migrates_legacy_configuration_and_state_without_deleting_them(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            "os.environ",
            {
                "XDG_CONFIG_HOME": f"{directory}/config",
                "XDG_STATE_HOME": f"{directory}/state",
            },
        ):
            old_config = Path(directory) / "config/fluxway/config.json"
            old_state = Path(directory) / "state/fluxway/gnome.json"
            old_config.parent.mkdir(parents=True)
            old_state.parent.mkdir(parents=True)
            old_config.write_text('{"legacy": true}\n', encoding="utf-8")
            old_state.write_text('{"night-light-enabled": false}\n', encoding="utf-8")

            migrated = migrate_legacy_files()

            self.assertEqual(migrated, [default_config_path(), default_state_path()])
            self.assertEqual(default_config_path().read_text(), old_config.read_text())
            self.assertEqual(default_state_path().read_text(), old_state.read_text())
            self.assertTrue(old_config.exists())
            self.assertTrue(old_state.exists())


if __name__ == "__main__":
    unittest.main()
