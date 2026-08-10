"""Scheduler run loop."""

from __future__ import annotations

from datetime import datetime
import time
from typing import Callable

from fluxway.backends import Backend
from fluxway.config import Config
from fluxway.schedule import ScheduledTemperature, temperature_at


def apply_once(
    config: Config,
    backend: Backend,
    *,
    now: Callable[[], datetime] = datetime.now,
) -> ScheduledTemperature:
    scheduled = temperature_at(config, now())
    backend.apply(scheduled.temperature)
    return scheduled


def run_forever(
    config: Config,
    backend: Backend,
    *,
    now: Callable[[], datetime] = datetime.now,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    backend.prepare()
    last_temperature: int | None = None
    while True:
        scheduled = temperature_at(config, now())
        if scheduled.temperature != last_temperature:
            backend.apply(scheduled.temperature)
            last_temperature = scheduled.temperature
        sleep(config.interval_seconds)

