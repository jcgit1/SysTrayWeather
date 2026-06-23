# SysTrayWeather

Linux system tray weather indicator for **KDE Plasma**. Shows the current temperature in the tray, a hover summary for yesterday/today/tomorrow, and an expandable window with hourly, daily, and weekly forecasts.

Weather data is provided by [Open-Meteo](https://open-meteo.com/) (free, no API key required).

## Requirements

- Python 3.11+
- KDE Plasma (or any desktop with a system tray)
- PyQt6

## Install

```bash
cd ~/Cursor\ Projects/SysTrayWeather
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
systrayweather
```

Or without installing:

```bash
source .venv/bin/activate
PYTHONPATH=src python -m systrayweather.main
```

On first launch you will be prompted for a **city or US zip code** (e.g. `Austin, TX` or `90210`). Settings are stored in `~/.config/systrayweather/config.json`.

## Usage

| Action | Result |
|--------|--------|
| Tray icon | Shows current temperature (e.g. `72°`) |
| Hover icon | Popup with yesterday / today / tomorrow highs and lows; raindrop when precip > 30% |
| Left-click icon | Open or hide the main window |
| Right-click icon | Menu: Show window, Refresh, Location, Quit |
| Location button | Change city or zip code (main window header or tray menu) |
| Close main window | Minimizes to tray (app keeps running) |

### Main window views

- **Hourly** — next 12 hours
- **Daily** — next 12 days
- **Weekly** — next 14 days (this week + next week)

## Autostart with Plasma

Copy the desktop file into your autostart folder:

```bash
mkdir -p ~/.config/autostart
cp data/com.systrayweather.app.desktop ~/.config/autostart/
```

If `systrayweather` is not on your `PATH`, edit the `Exec=` line to use the full path to your venv script, for example:

```ini
Exec=/home/you/Cursor Projects/SysTrayWeather/.venv/bin/systrayweather
```

## Configuration

`~/.config/systrayweather/config.json`:

```json
{
  "location_query": "90210",
  "location_name": "Beverly Hills, California",
  "latitude": 34.09,
  "longitude": -118.41,
  "timezone": "America/Los_Angeles",
  "units": "imperial",
  "poll_interval_minutes": 10,
  "location_setup_complete": true
}
```

## Cursor workspace

Open this project on the dev machine:

```text
File → Open Workspace from File… → ~/Cursor Projects/SysTrayWeather.code-workspace
```

Do not mix SysTrayWeather changes into LM9LLM or other project PRs.

## License

MIT (or your choice — add a LICENSE file if needed)
