"""Command-line interface for CircadianLight."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Sequence

from circadianlight import __version__
from circadianlight.backends import BackendError, select_backend
from circadianlight.config import (
    Config,
    ConfigError,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    Phase,
    VALID_BACKENDS,
    default_config_path,
    default_state_path,
    load_config,
    migrate_legacy_files,
    save_config,
)
from circadianlight.daemon import apply_once, run_forever
from circadianlight.schedule import temperature_at


def temperature(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("temperature must be an integer") from error
    if not MIN_TEMPERATURE <= parsed <= MAX_TEMPERATURE:
        raise argparse.ArgumentTypeError(
            f"temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE} K"
        )
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="circadian-light",
        description="circadian color temperature scheduling for Linux",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", type=Path, default=default_config_path())
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="run the scheduler until interrupted")
    run.add_argument("--backend", choices=VALID_BACKENDS, help="override configured backend")

    once = subparsers.add_parser("once", help="apply the current scheduled temperature once")
    once.add_argument("--backend", choices=VALID_BACKENDS, help="override configured backend")

    subparsers.add_parser("status", help="show current phase and temperature")
    subparsers.add_parser("show", help="print the current configuration as JSON")

    configure = subparsers.add_parser("config", help="update scheduler parameters")
    configure.add_argument("--day-start")
    configure.add_argument("--day-temp", type=temperature)
    configure.add_argument("--evening-start")
    configure.add_argument("--evening-temp", type=temperature)
    configure.add_argument("--night-start")
    configure.add_argument("--night-temp", type=temperature)
    configure.add_argument("--transition-minutes", type=int)
    configure.add_argument("--interval-seconds", type=int)
    configure.add_argument("--backend", choices=VALID_BACKENDS)

    reset = subparsers.add_parser("reset", help="restore display settings")
    reset.add_argument("--backend", choices=VALID_BACKENDS, help="override configured backend")
    return parser


def update_config(config: Config, arguments: argparse.Namespace) -> Config:
    day = replace(
        config.day,
        start=arguments.day_start if arguments.day_start is not None else config.day.start,
        temperature=arguments.day_temp if arguments.day_temp is not None else config.day.temperature,
    )
    evening = replace(
        config.evening,
        start=arguments.evening_start if arguments.evening_start is not None else config.evening.start,
        temperature=(
            arguments.evening_temp
            if arguments.evening_temp is not None
            else config.evening.temperature
        ),
    )
    night = replace(
        config.night,
        start=arguments.night_start if arguments.night_start is not None else config.night.start,
        temperature=(
            arguments.night_temp if arguments.night_temp is not None else config.night.temperature
        ),
    )
    updated = replace(
        config,
        day=day,
        evening=evening,
        night=night,
        transition_minutes=(
            arguments.transition_minutes
            if arguments.transition_minutes is not None
            else config.transition_minutes
        ),
        interval_seconds=(
            arguments.interval_seconds
            if arguments.interval_seconds is not None
            else config.interval_seconds
        ),
        backend=arguments.backend if arguments.backend is not None else config.backend,
    )
    updated.validate()
    return updated


def format_status(config: Config, backend_name: str | None = None) -> str:
    scheduled = temperature_at(config, datetime.now())
    details = {
        "phase": scheduled.phase,
        "temperature": scheduled.temperature,
        "target_temperature": scheduled.target_temperature,
        "transition_progress": round(scheduled.transition_progress, 3),
        "backend": backend_name or config.backend,
    }
    return json.dumps(details, indent=2)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        if arguments.config == default_config_path():
            migrate_legacy_files()
        config = load_config(arguments.config)

        if arguments.command == "show":
            print(json.dumps(config.to_dict(), indent=2))
            return 0
        if arguments.command == "config":
            updated = update_config(config, arguments)
            save_config(updated, arguments.config)
            print(f"Saved configuration to {arguments.config}")
            return 0
        if arguments.command == "status":
            print(format_status(config))
            return 0

        requested_backend = arguments.backend or config.backend
        backend = select_backend(requested_backend, default_state_path())
        if arguments.command == "once":
            backend.prepare()
            scheduled = apply_once(config, backend)
            print(
                f"Applied {scheduled.temperature} K via {backend.name} "
                f"({scheduled.phase}, target {scheduled.target_temperature} K)"
            )
            return 0
        if arguments.command == "reset":
            backend.reset()
            print(f"Reset {backend.name} display settings")
            return 0
        if arguments.command == "run":
            print(f"CircadianLight running via {backend.name}; press Ctrl+C to stop", flush=True)
            try:
                run_forever(config, backend)
            except KeyboardInterrupt:
                print(
                    "\nCircadianLight stopped; use 'circadian-light reset' "
                    "to restore prior settings"
                )
            return 0
    except (ConfigError, BackendError, OSError) as error:
        print(f"circadian-light: error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
