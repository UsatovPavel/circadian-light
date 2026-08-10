from datetime import datetime
import unittest

from circadianlight.config import Config
from circadianlight.schedule import temperature_at


class ScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config(transition_minutes=30)

    def at(self, hour: int, minute: int):
        return temperature_at(self.config, datetime(2026, 8, 10, hour, minute))

    def test_phase_targets_after_transition(self) -> None:
        self.assertEqual((self.at(1, 0).phase, self.at(1, 0).temperature), ("night", 2500))
        self.assertEqual((self.at(9, 0).phase, self.at(9, 0).temperature), ("day", 4750))
        self.assertEqual(
            (self.at(22, 30).phase, self.at(22, 30).temperature),
            ("evening", 3650),
        )

    def test_transition_is_linear(self) -> None:
        transition = self.at(21, 45)

        self.assertEqual(transition.phase, "evening")
        self.assertEqual(transition.temperature, 4200)
        self.assertEqual(transition.target_temperature, 3650)
        self.assertEqual(transition.transition_progress, 0.5)

    def test_midnight_wrap_uses_evening_as_previous_phase(self) -> None:
        transition = self.at(0, 15)

        self.assertEqual(transition.phase, "night")
        self.assertEqual(transition.temperature, 3075)

    def test_zero_transition_applies_target_at_start(self) -> None:
        config = Config(transition_minutes=0)
        scheduled = temperature_at(config, datetime(2026, 8, 10, 8, 0))

        self.assertEqual(scheduled.temperature, 4750)
        self.assertEqual(scheduled.transition_progress, 1.0)


if __name__ == "__main__":
    unittest.main()
