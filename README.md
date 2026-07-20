# SysTrayWeather

Linux system tray weather indicator for **KDE Plasma**. Shows the current temperature in the tray and city + temperature on hover.

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

On first launch you will be prompted for a **city or US zip code** (e.g. `Austin` or `90210`). Settings are stored in `~/.config/systrayweather/config.json`.

## Usage

| Action | Result |
|--------|--------|
| Tray icon | Shows current temperature (e.g. `72°`) |
| Hover icon | Tooltip with city and temperature |
| Right-click icon | Menu: Refresh, Location, Quit |

Temperature refreshes automatically every **20 minutes**. Use **Refresh** in the tray menu to update immediately.

## Autostart with Plasma

```bash
mkdir -p ~/.config/autostart
cp data/com.systrayweather.app.desktop ~/.config/autostart/
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
  "poll_interval_minutes": 20,
  "location_setup_complete": true
}
```

## Cursor workspace

Standalone project — **not** part of LM9LLM. Open only:

```text
/home/jcain/Cursor Projects/SysTrayWeather.code-workspace
```

See [Cursor Projects README](../README.md) for other workspaces.
