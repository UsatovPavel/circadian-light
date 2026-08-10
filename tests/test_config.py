from pathlib import Path
import tempfile
import unittest

from fluxway.config import Config, ConfigError, Phase, load_config, save_config


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


if __name__ == "__main__":
    unittest.main()

