# SysTrayWeather

## "ship it!" — the standing release ritual (user-defined 2026-11-04)
When the user says "ship it!" for SysTrayWeather, run the full cycle without
being asked per-step:
0. Bump the version: edit `Cargo.toml` `version` (patch bump by default;
   minor for features, major for breaking), and note it in the commit.
   Every binary also carries an auto-stamped build id — version + short commit
   + UTC build time (`systrayweather --version`, logged at startup, shown in
   the About window) — so binaries are distinguishable even without a bump.
1. Commit anything uncommitted on the working branch.
2. Create a GitHub PR for the new commit(s) on `jcgit1/SysTrayWeather`
   (`gh pr create` as jcgit1).
3. Merge the PR (squash, delete branch).
4. Sync: local `main` = GitHub `main` = Forgejo `jcain/SysTrayWeather` main
   (`git push forgejo main` after the squash). Remotes: `origin` = GitHub,
   `forgejo` = https://www.lm9llm.com/github/jcain/SysTrayWeather.git
   (auth: basic auth `jcain` + token from `~/forgejo_token--again`).
5. `cargo build --release` — must finish clean (no warnings). No test suite;
   the build is the check. Verify `--version` prints the new version.
6. `install -m 755 target/release/systrayweather /home/jcain/.local/bin/systrayweather`,
   then `systemctl --user stop systrayweather` and
   `systemd-run --user --collect --unit=systrayweather /home/jcain/.local/bin/systrayweather`.
   Confirm the log shows a fresh `Tray updated:` line before declaring done.

KDE Plasma (and Windows) system tray weather indicator. The tray icon shows the current temperature. A left click opens a 5-day forecast popup. The menu can refresh, change location, open Options (units, refresh interval, unit on icon, popup theme, start-with-login), show About, or quit.

This is a standalone app. It is not part of LM9LLM, TradeRadar, or any customer site.

## Root

`/home/jcain/Projects/SystrayWeather`

The running copy on this machine is the installed binary, not `cargo run`:

`/home/jcain/.local/bin/systrayweather`

## What to edit

The app is the Rust crate. `Cargo.toml` version is 0.2.0. Entry point is `src/main.rs`.

| Path | Role |
|---|---|
| `src/main.rs` | iced daemon: forecast popup, location dialog, options window, About window, poll loop |
| `src/tray.rs` | tray icon and menu (`tray-icon`, Linux feature `ksni`) |
| `src/icon.rs` | 64×64 temperature icon, rasterized with `fontdue` |
| `src/weather.rs` | Open-Meteo forecast and geocoding |
| `src/sky.rs` | forecast sky glyphs drawn on an iced canvas |
| `src/config.rs` | `config.json` load/save and log path |
| `src/autostart.rs` | start-with-login toggle (XDG autostart file on Linux, HKCU Run key on Windows) |
| `src/instance.rs` | one-instance file lock for this binary |
| `src/log.rs` | append-only log, also printed to stderr |
| `data/com.systrayweather.app.desktop` | desktop entry template in the repo |

Leave the Python tree alone. `src/systrayweather/`, `pyproject.toml`, `requirements.txt`, `test_fetch.py`, and `README.md` are the old PyQt6 app. The README install steps (`venv`, `pip install -e .`, `systrayweather` from the venv) do not match the running app. `result.json` is unrelated.

## Dependencies

Rust 2021 edition. Crates: `iced` 0.14 (canvas, tokio, advanced), `tray-icon` 0.26 (`ksni` on Linux), `reqwest` 0.12 (blocking, rustls), `serde` / `serde_json`, `fontdue`, `chrono`.

No API key. Weather is `https://api.open-meteo.com/v1/forecast`. Location search is `https://geocoding-api.open-meteo.com/v1/search`. A city name or a 5-digit US zip is accepted. Fetch asks for Fahrenheit/inches or Celsius/mm based on `config.json` `units` (`"imperial"` / `"metric"`); the Options window sets it.

Linux tray text needs a bold font. `src/icon.rs` uses `/usr/share/fonts/noto/NotoSans-Bold.ttf` when it exists, otherwise `/usr/share/fonts/TTF/DejaVuSans-Bold.ttf`. Windows uses `C:\Windows\Fonts\segoeuib.ttf`.

## Runtime files

| What | Where |
|---|---|
| Config | `~/.config/systrayweather/config.json` |
| Log | `~/.local/log/systrayweather/systrayweather.log` |
| Instance lock | `$XDG_RUNTIME_DIR/systrayweather-<hash>.lock` |
| Plasma autostart | `~/.config/autostart/com.systrayweather.app.desktop` |

On Windows, config is `%APPDATA%\systrayweather\config.json` and the log is `%LOCALAPPDATA%\systrayweather\systrayweather.log`.

Config fields: `location_query`, `location_name`, `latitude`, `longitude`, `timezone`, `units`, `poll_interval_minutes` (default 20), `location_setup_complete`, `show_unit_on_icon` (default false), `theme` (`"light"`/`"dark"`/`"system"`, default `"system"`; iced 0.14 has no system-dark detection, so system maps to Dark). The location dialog opens on startup when setup is incomplete or lat/lon/name are missing. The Options window edits all of these except the location fields, and toggles autostart directly (not via config).

The lock is per executable path. `cargo run` and `~/.local/bin/systrayweather` can both be running. A second start of the same binary logs "already running" and shows a short notice.

## Build, install, restart

After a feature or bugfix build, install the binary and restart the session copy before treating the change as done. Skip that for questions, reviews, and edits that were not built.

```bash
cargo build --release
install -m 755 target/release/systrayweather /home/jcain/.local/bin/systrayweather
```

Autostart `Exec` must stay:

```
Exec=/home/jcain/.local/bin/systrayweather
```

Keep `X-KDE-autostart-after=panel` and `OnlyShowIn=KDE;`. The repo template uses a bare `Exec=systrayweather`; the installed autostart file uses the absolute path above.

Stop the current `systrayweather` process, then start the installed binary under the user systemd manager so it is not parented to the agent shell:

```bash
systemd-run --user --collect --unit=systrayweather /home/jcain/.local/bin/systrayweather
```

There is no test suite. `cargo build --release` is the check. A debug build for a quick compile is `cargo build`.

## Behavior worth knowing

- Left click toggles the forecast popup near the click. A second click within 450 ms is ignored. The window is borderless and always on top.
- The menu is Refresh, Location…, and Quit. On Windows, left click does not open the menu.
- The tray is polled every 80 ms. Weather refreshes every `poll_interval_minutes`.
- HTTP calls run on a background thread so the iced loop stays responsive. Timeout is 20 seconds.
- Sky icons come from Open-Meteo weather codes (storm, snow, rain, drizzle, freezing, fog, clear, cloudy).

## Troubleshooting

Read `~/.local/log/systrayweather/systrayweather.log` first. Lines look like `2026-11-04 07:09:00 [INFO] systrayweather: …`. Weather failures are `[WARN]` and include the Open-Meteo error. A successful update logs `Open-Meteo:` and `Tray updated:`.

If the tray icon is blank or still shows `--`, the font file is missing or the fetch failed before `set_temperature`. If a new build seems to do nothing, check which binary is running: the session may still be on `~/.local/bin/systrayweather` while `cargo run` started a second copy, or the old process was never stopped.

`ksni` talks to the Plasma StatusNotifier. The icon appears only after the panel is up, which is why autostart waits with `X-KDE-autostart-after=panel`. A missing tray with a clean log usually means the process started before the panel, or it is not the installed binary.
