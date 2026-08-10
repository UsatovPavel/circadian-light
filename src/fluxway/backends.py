"""Display temperature backends for GNOME and wlroots compositors."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Mapping, Sequence


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class BackendError(RuntimeError):
    """Raised when the selected display backend cannot apply a temperature."""


def run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError as error:
        raise BackendError(f"required command not found: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or str(error)).strip()
        raise BackendError(f"{' '.join(command)} failed: {detail}") from error
    except subprocess.TimeoutExpired as error:
        raise BackendError(f"{' '.join(command)} timed out") from error


class Backend(ABC):
    name: str

    def prepare(self) -> None:
        """Prepare the display system before the first adjustment."""

    @abstractmethod
    def apply(self, temperature: int) -> None:
        """Apply a color temperature in Kelvin."""

    @abstractmethod
    def reset(self) -> None:
        """Restore the display settings changed by this backend."""


class GnomeBackend(Backend):
    name = "gnome"
    schema = "org.gnome.settings-daemon.plugins.color"
    saved_keys = (
        "night-light-enabled",
        "night-light-schedule-automatic",
        "night-light-schedule-from",
        "night-light-schedule-to",
        "night-light-temperature",
    )

    def __init__(self, state_path: Path, runner: CommandRunner = run_command):
        self.state_path = state_path
        self.runner = runner

    def _get(self, key: str) -> str:
        return self.runner(("gsettings", "get", self.schema, key)).stdout.strip()

    def _set(self, key: str, value: str) -> None:
        self.runner(("gsettings", "set", self.schema, key, value))

    def prepare(self) -> None:
        if not self.state_path.exists():
            original = {key: self._get(key) for key in self.saved_keys}
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(original, indent=2) + "\n", encoding="utf-8")
        self._set("night-light-enabled", "true")
        self._set("night-light-schedule-automatic", "false")
        self._set("night-light-schedule-from", "0.0")
        self._set("night-light-schedule-to", "24.0")

    def apply(self, temperature: int) -> None:
        self._set("night-light-temperature", str(temperature))

    def reset(self) -> None:
        if not self.state_path.exists():
            return
        try:
            original = json.loads(self.state_path.read_text(encoding="utf-8"))
            for key in self.saved_keys:
                if key in original:
                    self._set(key, str(original[key]))
        except (OSError, json.JSONDecodeError) as error:
            raise BackendError(f"cannot restore GNOME settings: {error}") from error
        self.state_path.unlink()


class GammastepBackend(Backend):
    name = "gammastep"

    def __init__(
        self,
        method: str,
        runner: CommandRunner = run_command,
    ):
        self.method = method
        self.runner = runner

    def apply(self, temperature: int) -> None:
        self.runner(("gammastep", "-m", self.method, "-P", "-O", str(temperature)))

    def reset(self) -> None:
        self.runner(("gammastep", "-m", self.method, "-x"))


def select_backend(
    requested: str,
    state_path: Path,
    *,
    environ: Mapping[str, str] | None = None,
    runner: CommandRunner = run_command,
) -> Backend:
    environment = os.environ if environ is None else environ
    desktop = environment.get("XDG_CURRENT_DESKTOP", "").lower()
    if requested == "auto":
        requested = "gnome" if "gnome" in desktop else "gammastep"

    if requested == "gnome":
        if shutil.which("gsettings") is None:
            raise BackendError("GNOME backend requires the gsettings command")
        return GnomeBackend(state_path, runner)
    if requested == "gammastep":
        if shutil.which("gammastep") is None:
            raise BackendError("Gammastep backend requires the gammastep command")
        method = "wayland" if environment.get("WAYLAND_DISPLAY") else "randr"
        return GammastepBackend(method, runner)
    raise BackendError(f"unknown backend: {requested}")

