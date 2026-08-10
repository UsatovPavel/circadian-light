# Fluxway

Fluxway is a small, dependency-free Linux daemon that changes display color
temperature throughout the day. It provides three CLI-configurable phases and
supports both Ubuntu GNOME Wayland and wlroots compositors such as Sway.

Default schedule:

| Phase | Starts | Target temperature |
| --- | ---: | ---: |
| Night | 00:00 | 2500 K |
| Day | 08:00 | 4750 K |
| Evening | 21:30 | 3650 K |

Temperatures may be set from 1900 K to 6500 K. By default, Fluxway fades to a
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
PYTHONPATH=src python3 -m fluxway status
```

## Use

Show the active configuration:

```bash
fluxway show
```

Configure all Jira AGENT-66 parameters from the CLI:

```bash
fluxway config \
  --day-start 08:00 --day-temp 4750 \
  --evening-start 21:30 --evening-temp 3650 \
  --night-start 00:00 --night-temp 2500
```

Additional controls:

```bash
fluxway config --transition-minutes 30 --interval-seconds 60
fluxway config --backend auto       # auto, gnome, or gammastep
fluxway status
fluxway once                        # apply now and exit
fluxway run                         # run continuously
fluxway reset                       # restore the previous display settings
```

Configuration is stored at `${XDG_CONFIG_HOME:-~/.config}/fluxway/config.json`.

### Run automatically with systemd

After installing with `pipx`:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/fluxway.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now fluxway.service
```

Inspect it with:

```bash
systemctl --user status fluxway.service
journalctl --user -u fluxway.service
```

## Sway example

Select the Gammastep backend and start the daemon:

```bash
fluxway config --backend gammastep
fluxway run
```

Sway must advertise the Wayland gamma-control protocol. GNOME does not, which
is why Fluxway automatically uses its native Night Light API there.

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## License

Copyright 2026 UsatovPavel

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

