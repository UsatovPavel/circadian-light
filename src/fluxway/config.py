"""Configuration model and persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping


MIN_TEMPERATURE = 1900
MAX_TEMPERATURE = 6500
VALID_BACKENDS = ("auto", "gnome", "gammastep")
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class ConfigError(ValueError):
    """Raised when user configuration is invalid."""


@dataclass(frozen=True)
class Phase:
    start: str
    temperature: int

    def validate(self, name: str) -> None:
        if not TIME_PATTERN.fullmatch(self.start):
            raise ConfigError(f"{name} start must use 24-hour HH:MM format")
        if not MIN_TEMPERATURE <= self.temperature <= MAX_TEMPERATURE:
            raise ConfigError(
                f"{name} temperature must be between "
                f"{MIN_TEMPERATURE} K and {MAX_TEMPERATURE} K"
            )


@dataclass(frozen=True)
class Config:
    day: Phase = Phase("08:00", 4750)
    evening: Phase = Phase("21:30", 3650)
    night: Phase = Phase("00:00", 2500)
    transition_minutes: int = 30
    interval_seconds: int = 60
    backend: str = "auto"

    def validate(self) -> None:
        phases = (("day", self.day), ("evening", self.evening), ("night", self.night))
        for name, phase in phases:
            phase.validate(name)
        starts = [phase.start for _, phase in phases]
        if len(starts) != len(set(starts)):
            raise ConfigError("phase start times must be unique")
        if not 0 <= self.transition_minutes <= 240:
            raise ConfigError("transition minutes must be between 0 and 240")
        if not 1 <= self.interval_seconds <= 3600:
            raise ConfigError("interval seconds must be between 1 and 3600")
        if self.backend not in VALID_BACKENDS:
            raise ConfigError(f"backend must be one of: {', '.join(VALID_BACKENDS)}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Config":
        try:
            config = cls(
                day=Phase(**data.get("day", {})),
                evening=Phase(**data.get("evening", {})),
                night=Phase(**data.get("night", {})),
                transition_minutes=data.get("transition_minutes", 30),
                interval_seconds=data.get("interval_seconds", 60),
                backend=data.get("backend", "auto"),
            )
        except TypeError as error:
            raise ConfigError(f"invalid configuration structure: {error}") from error
        config.validate()
        return config


def default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    return Path(base) / "fluxway/config.json" if base else Path.home() / ".config/fluxway/config.json"


def default_state_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    return Path(base) / "fluxway/gnome.json" if base else Path.home() / ".local/state/fluxway/gnome.json"


def load_config(path: Path) -> Config:
    if not path.exists():
        config = Config()
        config.validate()
        return config
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigError(f"cannot read {path}: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError("configuration root must be a JSON object")
    return Config.from_dict(data)


def save_config(config: Config, path: Path) -> None:
    config.validate()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(config.to_dict(), indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=".config-", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(payload)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise

