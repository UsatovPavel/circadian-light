"""Phase selection and smooth temperature transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from circadianlight.config import Config, Phase


MINUTES_PER_DAY = 24 * 60


@dataclass(frozen=True)
class ScheduledTemperature:
    phase: str
    temperature: int
    target_temperature: int
    transition_progress: float


def parse_minutes(value: str) -> int:
    hours, minutes = (int(part) for part in value.split(":"))
    return hours * 60 + minutes


def _ordered_phases(config: Config) -> list[tuple[str, Phase, int]]:
    phases = [
        ("day", config.day, parse_minutes(config.day.start)),
        ("evening", config.evening, parse_minutes(config.evening.start)),
        ("night", config.night, parse_minutes(config.night.start)),
    ]
    return sorted(phases, key=lambda item: item[2])


def temperature_at(config: Config, moment: datetime) -> ScheduledTemperature:
    """Return the scheduled temperature for a local wall-clock time.

    A transition starts at each configured phase start and reaches that phase's
    target after ``transition_minutes``. Before the first start of a day, the
    last phase from the previous day remains active.
    """

    config.validate()
    minute = moment.hour * 60 + moment.minute + moment.second / 60
    ordered = _ordered_phases(config)
    current_index = max(
        (index for index, (_, _, start) in enumerate(ordered) if start <= minute),
        default=len(ordered) - 1,
    )
    name, phase, start = ordered[current_index]
    previous_phase = ordered[current_index - 1][1]

    elapsed = minute - start
    if elapsed < 0:
        elapsed += MINUTES_PER_DAY

    duration = config.transition_minutes
    if duration == 0 or elapsed >= duration:
        return ScheduledTemperature(name, phase.temperature, phase.temperature, 1.0)

    progress = max(0.0, min(1.0, elapsed / duration))
    interpolated = previous_phase.temperature + (
        phase.temperature - previous_phase.temperature
    ) * progress
    return ScheduledTemperature(name, round(interpolated), phase.temperature, progress)
