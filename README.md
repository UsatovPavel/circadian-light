# CircadianLight

CircadianLight is a small, dependency-free Linux daemon that changes display color
temperature throughout the day. It provides three CLI-configurable phases and
supports both Ubuntu GNOME Wayland and wlroots compositors such as Sway.

Default schedule:

| Phase | Starts | Target temperature |
| --- | ---: | ---: |
| Night | 00:00 | 2500 K |
| Day | 08:00 | 4750 K |
| Evening | 21:30 | 3650 K |

Temperatures may be set from 1900 K to 6500 K. By default, CircadianLight fades to a
new phase over 30 minutes.

## Backends

- **GNOME:** uses GNOME's own Night Light settings. This is the only reliable
  way to change the whole display temperature on GNOME Wayland.
- **Gammastep:** uses Wayland gamma control on Sway and other compatible
  wlroots compositors, or RandR in an X11 session.
- **Auto:** selects GNOME when `XDG_CURRENT_DESKTOP` contains `GNOME`, and
  Gammastep otherwise.

## Install

Python 3.10 or newer is required. For an isolated user installation:

```bash
sudo apt install pipx
pipx install .
```

For the Sway backend, install Gammastep as well:

```bash
sudo apt install gammastep
```

Run without installing while developing:

```bash
PYTHONPATH=src python3 -m circadianlight status
```

## Use

Show the active configuration:

```bash
circadian-light show
```

Configure all Jira AGENT-66 parameters from the CLI:

```bash
circadian-light config \
  --day-start 08:00 --day-temp 4750 \
  --evening-start 21:30 --evening-temp 3650 \
  --night-start 00:00 --night-temp 2500
```

Additional controls:

```bash
circadian-light config --transition-minutes 30 --interval-seconds 60
circadian-light config --backend auto       # auto, gnome, or gammastep
circadian-light status
circadian-light once                        # apply now and exit
circadian-light run                         # run continuously
circadian-light reset                       # restore the previous display settings
```

Configuration is stored at
`${XDG_CONFIG_HOME:-~/.config}/circadian-light/config.json`.

### Run automatically with systemd

After installing with `pipx`:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/circadian-light.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now circadian-light.service
```

Inspect it with:

```bash
systemctl --user status circadian-light.service
journalctl --user -u circadian-light.service
```

## Sway example

Select the Gammastep backend and start the daemon:

```bash
circadian-light config --backend gammastep
circadian-light run
```

Sway must advertise the Wayland gamma-control protocol. GNOME does not, which
is why CircadianLight automatically uses its native Night Light API there.

## Upgrade from Fluxway

CircadianLight automatically copies an existing Fluxway configuration and
GNOME restore state on first launch. The legacy files are retained for safe
rollback. Replace the old `pipx` installation with:

```bash
pipx uninstall fluxway
pipx install .
```

If the legacy systemd service was enabled, replace it as well:

```bash
systemctl --user disable --now fluxway.service
rm ~/.config/systemd/user/fluxway.service
cp systemd/circadian-light.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now circadian-light.service
```

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## License
Copyright 2026 UsatovPavel

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
