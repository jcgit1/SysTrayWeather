mod autostart;
mod config;
mod icon;
mod instance;
mod log;
mod sky;
mod tray;
mod weather;

use std::time::{Duration, Instant};

use iced::widget::{
    button, checkbox, column, container, radio, row, space, text, text_input,
};
use iced::window::{self, Level, Position};
use iced::{Color, Element, Fill, Point, Size, Subscription, Task, Theme};

use config::{Config, ThemeChoice};
use weather::{Snapshot, Sky};

const FORECAST_W: f32 = 700.0;
const FORECAST_H: f32 = 330.0;
const POLL_CHOICES: [u32; 4] = [10, 20, 30, 60];

fn main() -> iced::Result {
    log::init();
    let _instance = match instance::acquire() {
        Ok(lock) => lock,
        Err(instance::AlreadyRunning) => {
            log::warn("SysTrayWeather is already running; refusing a second instance");
            return already_running();
        }
    };
    if let Err(err) = tray::install() {
        log::warn(&format!("tray icon failed: {err}"));
    }
    iced::daemon(App::boot, App::update, App::view)
        .subscription(App::subscription)
        .title(App::title)
        .theme(App::theme)
        .run()
}

struct App {
    config: Config,
    snapshot: Option<Snapshot>,
    status: String,
    query: String,
    forecast: Option<window::Id>,
    forecast_at: Option<Instant>,
    location: Option<window::Id>,
    options: Option<window::Id>,
    about: Option<window::Id>,
    about_text: Option<(String, String, String)>,
    autostart: bool,
}

#[derive(Debug, Clone)]
enum Message {
    Poll,
    Fetched(Result<Snapshot, String>),
    ShowForecast { x: f64, y: f64 },
    Refresh,
    ShowLocation,
    QueryChanged(String),
    SaveLocation,
    LocationReady(Result<Config, String>),
    ShowOptions,
    ShowAbout,
    OptionsClose,
    UnitsChanged(bool),
    PollChanged(u32),
    ShowUnitToggled(bool),
    ThemeChanged(ThemeChoice),
    AutostartToggled(bool),
    WindowOpened,
    WindowClosed(window::Id),
    Quit,
}

impl App {
    fn boot() -> (Self, Task<Message>) {
        let config = Config::load();
        let query = config.location_query.clone();
        let app = Self {
            config,
            snapshot: None,
            status: String::new(),
            query,
            forecast: None,
            forecast_at: None,
            location: None,
            options: None,
            about: None,
            about_text: None,
            autostart: autostart::is_enabled(),
        };
        let task = if app.config.is_configured() {
            fetch_task(app.config.clone())
        } else {
            Task::done(Message::ShowLocation)
        };
        (app, task)
    }

    fn title(&self, id: window::Id) -> String {
        if self.location == Some(id) {
            "SysTrayWeather — Location".into()
        } else if self.options == Some(id) {
            "SysTrayWeather — Options".into()
        } else if self.about == Some(id) {
            "SysTrayWeather — About".into()
        } else {
            "SysTrayWeather".into()
        }
    }

    fn theme(&self, id: window::Id) -> Theme {
        if self.options == Some(id) || self.about == Some(id) {
            return Theme::Dark;
        }
        match self.config.theme {
            ThemeChoice::Light => Theme::Light,
            // iced 0.14 has no system-dark detection; "System" keeps the
            // app's traditional Dark look.
            ThemeChoice::Dark | ThemeChoice::System => Theme::Dark,
        }
    }

    fn subscription(&self) -> Subscription<Message> {
        let minutes = self.config.poll_interval_minutes.max(1) as u64;
        Subscription::batch([
            iced::time::every(Duration::from_millis(80)).map(|_| Message::Poll),
            iced::time::every(Duration::from_secs(minutes * 60)).map(|_| Message::Refresh),
            window::close_events().map(Message::WindowClosed),
        ])
    }

    fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::Poll => {
                let mut task = Task::none();
                let mut refresh = false;
                for action in tray::drain() {
                    match action {
                        tray::TrayAction::Activate { x, y } => {
                            task = task.chain(self.update(Message::ShowForecast { x, y }));
                        }
                        tray::TrayAction::Refresh => refresh = true,
                        tray::TrayAction::Location => {
                            task = task.chain(self.update(Message::ShowLocation));
                        }
                        tray::TrayAction::Options => {
                            task = task.chain(self.update(Message::ShowOptions));
                        }
                        tray::TrayAction::About => {
                            task = task.chain(self.update(Message::ShowAbout));
                        }
                        tray::TrayAction::Quit => {
                            task = task.chain(self.update(Message::Quit));
                        }
                    }
                }
                if refresh {
                    log::info("Refresh requested");
                    task = task.chain(self.update(Message::Refresh));
                }
                task
            }
            Message::Refresh => {
                if self.config.is_configured() {
                    fetch_task(self.config.clone())
                } else {
                    Task::done(Message::ShowLocation)
                }
            }
            Message::Fetched(result) => {
                match result {
                    Ok(snapshot) => {
                        let unit = if snapshot.metric { "°C" } else { "°F" };
                        let mut label = format!("{}°", snapshot.current.round());
                        if self.config.show_unit_on_icon {
                            label.push_str(&unit[1..]);
                        }
                        let tip = format!("{} — {label}", snapshot.location_name);
                        tray::set_temperature(&label, &tip);
                        log::info(&format!("Tray updated: {tip}"));
                        self.snapshot = Some(snapshot);
                        self.status.clear();
                    }
                    Err(err) => {
                        log::warn(&format!("Weather update error: {err}"));
                        self.status = err;
                    }
                }
                Task::none()
            }
            Message::ShowForecast { x, y } => {
                if let Some(opened) = self.forecast_at {
                    if opened.elapsed() < Duration::from_millis(450) {
                        return Task::none();
                    }
                    if let Some(id) = self.forecast.take() {
                        self.forecast_at = None;
                        return window::close(id);
                    }
                }
                let (left, top) = popup_origin(x, y);
                let (id, task) = window::open(window::Settings {
                    size: Size::new(FORECAST_W, FORECAST_H),
                    position: Position::Specific(Point::new(left, top)),
                    decorations: false,
                    resizable: false,
                    level: Level::AlwaysOnTop,
                    exit_on_close_request: false,
                    ..window::Settings::default()
                });
                self.forecast = Some(id);
                self.forecast_at = Some(Instant::now());
                log::info(&format!(
                    "Forecast popup at {left:.0},{top:.0} from click {x:.0},{y:.0}"
                ));
                task.map(|_| Message::WindowOpened)
            }
            Message::ShowLocation => {
                if self.location.is_some() {
                    return Task::none();
                }
                let (id, task) = window::open(window::Settings {
                    size: Size::new(420.0, 180.0),
                    position: Position::Centered,
                    resizable: false,
                    level: Level::AlwaysOnTop,
                    exit_on_close_request: false,
                    ..window::Settings::default()
                });
                self.location = Some(id);
                task.map(|_| Message::WindowOpened)
            }
            Message::QueryChanged(query) => {
                self.query = query;
                Task::none()
            }
            Message::SaveLocation => {
                let query = self.query.clone();
                Task::perform(
                    async move {
                        let (tx, rx) = iced::futures::channel::oneshot::channel();
                        std::thread::spawn(move || {
                            let _ = tx.send(weather::geocode(&query));
                        });
                        rx.await
                            .unwrap_or_else(|_| Err("Location lookup was cancelled".into()))
                    },
                    Message::LocationReady,
                )
            }
            Message::LocationReady(result) => match result {
                Ok(config) => {
                    if let Err(err) = config.save() {
                        self.status = err;
                        return Task::none();
                    }
                    log::info(&format!("Location set to {}", config.location_name));
                    self.query = config.location_query.clone();
                    self.config = config;
                    let close = self
                        .location
                        .take()
                        .map(window::close)
                        .unwrap_or_else(Task::none);
                    close.chain(fetch_task(self.config.clone()))
                }
                Err(err) => {
                    self.status = err;
                    Task::none()
                }
            },
            Message::ShowOptions => {
                if self.options.is_some() {
                    return Task::none();
                }
                self.autostart = autostart::is_enabled();
                let (id, task) = window::open(window::Settings {
                    size: Size::new(440.0, 400.0),
                    position: Position::Centered,
                    resizable: false,
                    level: Level::AlwaysOnTop,
                    exit_on_close_request: false,
                    ..window::Settings::default()
                });
                self.options = Some(id);
                task.map(|_| Message::WindowOpened)
            }
            Message::UnitsChanged(metric) => {
                let units = if metric { "metric" } else { "imperial" };
                if self.config.units != units {
                    log::info(&format!("Units set to {units}"));
                    self.config.units = units.into();
                    return self.apply_config(true);
                }
                Task::none()
            }
            Message::PollChanged(minutes) => {
                if self.config.poll_interval_minutes != minutes {
                    log::info(&format!("Poll interval set to {minutes} minutes"));
                    self.config.poll_interval_minutes = minutes;
                    return self.apply_config(true);
                }
                Task::none()
            }
            Message::ShowUnitToggled(show) => {
                self.config.show_unit_on_icon = show;
                self.apply_config(true)
            }
            Message::ThemeChanged(theme) => {
                if self.config.theme != theme {
                    log::info(&format!("Theme set to {}", theme.as_str()));
                    self.config.theme = theme;
                    return self.apply_config(true);
                }
                Task::none()
            }
            Message::AutostartToggled(enable) => {
                if let Err(err) = autostart::set_enabled(enable) {
                    log::warn(&format!("Autostart change failed: {err}"));
                    self.status = format!("Could not change autostart: {err}");
                    return Task::none();
                }
                self.autostart = enable;
                self.status.clear();
                Task::none()
            }
            Message::ShowAbout => {
                let version = env!("CARGO_PKG_VERSION");
                let config_path = config::config_path().display().to_string();
                let log_path = config::log_path().display().to_string();
                let (id, task) = window::open(window::Settings {
                    size: Size::new(460.0, 210.0),
                    position: Position::Centered,
                    resizable: false,
                    level: Level::AlwaysOnTop,
                    exit_on_close_request: false,
                    ..window::Settings::default()
                });
                self.about = Some(id);
                self.about_text = Some((version.into(), config_path, log_path));
                return task.map(|_| Message::WindowOpened);
            }
            Message::OptionsClose => {
                let Some(id) = self.about.take() else {
                    return Task::none();
                };
                self.about_text = None;
                window::close(id)
            }
            Message::WindowOpened => Task::none(),
            Message::WindowClosed(id) => {
                if self.forecast == Some(id) {
                    self.forecast = None;
                    self.forecast_at = None;
                }
                if self.location == Some(id) {
                    self.location = None;
                }
                if self.options == Some(id) {
                    self.options = None;
                }
                if self.about == Some(id) {
                    self.about = None;
                    self.about_text = None;
                }
                Task::none()
            }
            Message::Quit => {
                log::info("Quit requested, shutting down");
                iced::exit()
            }
        }
    }

    /// Persist the config; optionally re-fetch (unit changes make the cached
    /// snapshot wrong) and re-render the tray label.
    fn apply_config(&mut self, refetch: bool) -> Task<Message> {
        if let Err(err) = self.config.save() {
            log::warn(&format!("Config save failed: {err}"));
            self.status = err;
            return Task::none();
        }
        self.status.clear();
        if let Some(snapshot) = self.snapshot.clone() {
            let stale_unit = snapshot.metric != config::is_metric(&self.config.units);
            if !stale_unit {
                let unit = if snapshot.metric { "°C" } else { "°F" };
                let mut label = format!("{}°", snapshot.current.round());
                if self.config.show_unit_on_icon {
                    label.push_str(&unit[1..]);
                }
                let tip = format!("{} — {label}", snapshot.location_name);
                tray::set_temperature(&label, &tip);
            }
        }
        if refetch && self.config.is_configured() {
            return fetch_task(self.config.clone());
        }
        Task::none()
    }

    fn view(&self, id: window::Id) -> Element<'_, Message> {
        if self.location == Some(id) {
            return location_view(self);
        }
        if self.options == Some(id) {
            return options_view(self);
        }
        if self.about == Some(id) {
            return about_view(self);
        }
        forecast_view(self)
    }
}

fn about_view(app: &App) -> Element<'_, Message> {
    let (version, config_path, log_path) = app
        .about_text
        .as_ref()
        .map(|(v, c, l)| (v.as_str(), c.as_str(), l.as_str()))
        .unwrap_or(("?", "", ""));
    let body = column![
        text("SysTrayWeather").size(20),
        text(format!("Version {version}")).size(14).color(muted()),
        text("System tray weather indicator for KDE Plasma").size(13).color(muted()),
        text(format!("Config: {config_path}")).size(12).color(dim()),
        text(format!("Log: {log_path}")).size(12).color(dim()),
        button("Close").on_press(Message::OptionsClose),
    ]
    .spacing(10)
    .padding(22);
    container(body).width(Fill).height(Fill).into()
}

fn options_view(app: &App) -> Element<'_, Message> {
    let metric = config::is_metric(&app.config.units);
    let location_row = row![
        column![
            text("Location").size(15),
            text(if app.config.location_name.is_empty() {
                "Not set".to_string()
            } else {
                app.config.location_name.clone()
            })
            .size(13)
            .color(muted()),
        ]
        .spacing(2),
        space(),
        button("Change…").on_press(Message::ShowLocation),
    ]
    .align_y(iced::Alignment::Center);

    let units_row = row![
        text("Units").size(15).width(110.0),
        radio("°F", false, (!metric).then_some(false), Message::UnitsChanged),
        radio("°C", true, metric.then_some(true), Message::UnitsChanged),
    ]
    .spacing(14)
    .align_y(iced::Alignment::Center);

    let poll_row = row![text("Refresh every").size(15).width(110.0)].spacing(14);
    let current = (POLL_CHOICES.contains(&app.config.poll_interval_minutes)
        .then_some(app.config.poll_interval_minutes))
        .or(Some(20));
    let poll_row = POLL_CHOICES.into_iter().fold(poll_row, |row, minutes| {
        row.push(radio(
            format!("{minutes} min"),
            minutes,
            current.filter(|c| *c == minutes),
            Message::PollChanged,
        ))
    });

    let icon_row = row![
        text("Icon").size(15).width(110.0),
        checkbox(app.config.show_unit_on_icon)
            .label("show unit (74°)")
            .on_toggle(Message::ShowUnitToggled),
    ]
    .spacing(14)
    .align_y(iced::Alignment::Center);

    let theme = app.config.theme;
    let theme_row = row![
        text("Theme").size(15).width(110.0),
        radio("Light", ThemeChoice::Light, (theme == ThemeChoice::Light).then_some(ThemeChoice::Light), Message::ThemeChanged),
        radio("Dark", ThemeChoice::Dark, (theme == ThemeChoice::Dark).then_some(ThemeChoice::Dark), Message::ThemeChanged),
        radio("System", ThemeChoice::System, (theme == ThemeChoice::System).then_some(ThemeChoice::System), Message::ThemeChanged),
    ]
    .spacing(14)
    .align_y(iced::Alignment::Center);

    let login_row = row![
        text("Login").size(15).width(110.0),
        checkbox(app.autostart)
            .label("start with login")
            .on_toggle(Message::AutostartToggled),
    ]
    .spacing(14)
    .align_y(iced::Alignment::Center);

    let mut col = column![
        text("Options").size(20),
        location_row,
        units_row,
        poll_row,
        icon_row,
        theme_row,
        login_row,
    ]
    .spacing(16)
    .padding(22);
    if !app.status.is_empty() {
        col = col.push(text(&app.status).size(13).color(Color::from_rgb(0.9, 0.45, 0.4)));
    }
    container(col).width(Fill).height(Fill).into()
}

fn location_view(app: &App) -> Element<'_, Message> {
    let body = column![
        text("Where should the tray look?").size(18),
        text("City name or US zip code").size(13).color(muted()),
        text_input("90210 or Austin", &app.query)
            .on_input(Message::QueryChanged)
            .on_submit(Message::SaveLocation)
            .padding(10)
            .width(Fill),
        text(&app.status).size(13).color(Color::from_rgb(0.9, 0.45, 0.4)),
        button("Use this location").on_press(Message::SaveLocation),
    ]
    .spacing(12)
    .padding(22);
    container(body).width(Fill).height(Fill).into()
}

fn forecast_view(app: &App) -> Element<'_, Message> {
    let Some(snapshot) = app.snapshot.as_ref() else {
        let body = column![
            text("SysTrayWeather").size(18),
            text(if app.status.is_empty() {
                "Waiting for the first forecast."
            } else {
                app.status.as_str()
            })
            .size(14)
            .color(muted()),
        ]
        .spacing(8)
        .padding(24);
        return panel(body);
    };

    let days = snapshot.days.iter().map(day_column);
    let body = column![
        text(&snapshot.location_name).size(20),
        text("Next 5 days  ·  precipitation")
            .size(13)
            .color(muted()),
        row(days).spacing(8).width(Fill),
    ]
    .spacing(14)
    .padding(22);
    panel(body)
}

fn day_column(day: &weather::Day) -> Element<'_, Message> {
    let kind = weather::sky_kind(day);
    let name = if day.is_today {
        "Today".to_string()
    } else {
        day.date.format("%a").to_string()
    };
    let lines = weather::precip_lines(day);
    let primary = lines[0].clone();
    let extra = lines.get(1).cloned();
    let precip_color = match kind {
        Sky::Snow | Sky::Sleet => Color::from_rgb(0.93, 0.95, 0.97),
        Sky::Rain | Sky::Drizzle | Sky::Storm => Color::from_rgb(0.84, 0.92, 0.96),
        _ if primary == "No precip" => dim(),
        _ => Color::from_rgb(0.84, 0.92, 0.96),
    };
    let mut col = column![
        text(name).size(14),
        sky::glyph(kind),
        text(kind.label()).size(12).color(muted()),
        row![
            text(format!("{}°", day.temp_max.round())).size(14),
            text(format!("{}°", day.temp_min.round()))
                .size(14)
                .color(dim()),
        ]
        .spacing(6),
        text(primary).size(15).color(precip_color),
    ]
    .spacing(6)
    .align_x(iced::Alignment::Center)
    .width(Fill);
    if let Some(extra) = extra {
        col = col.push(text(extra).size(13).color(precip_color));
    }
    if let Some(chance) = day.precip_probability {
        col = col.push(text(format!("{chance}%")).size(12).color(muted()));
    }
    col.into()
}

fn panel(body: iced::widget::Column<'_, Message>) -> Element<'_, Message> {
    container(body)
        .width(Fill)
        .height(Fill)
        .style(|_| container::Style {
            background: Some(iced::Background::Color(Color::from_rgb(0.106, 0.118, 0.141))),
            text_color: Some(Color::from_rgb(0.95, 0.96, 0.97)),
            border: iced::Border {
                color: Color::from_rgb(0.20, 0.23, 0.28),
                width: 1.0,
                radius: 16.0.into(),
            },
            ..container::Style::default()
        })
        .into()
}

fn muted() -> Color {
    Color::from_rgb(0.56, 0.59, 0.65)
}

fn dim() -> Color {
    Color::from_rgb(0.42, 0.45, 0.50)
}

#[derive(Debug, Clone)]
enum Notice {
    Ok,
}

fn already_running() -> iced::Result {
    iced::application(|| (), on_notice, notice_view)
        .title("SysTrayWeather")
        .theme(Theme::Dark)
        .window(window::Settings {
            size: Size::new(480.0, 190.0),
            position: Position::Centered,
            resizable: false,
            level: Level::AlwaysOnTop,
            ..window::Settings::default()
        })
        .run()
}

fn on_notice(_state: &mut (), _message: Notice) -> Task<Notice> {
    iced::exit()
}

fn notice_view(_state: &()) -> Element<'_, Notice> {
    let body = column![
        text("SysTrayWeather is already running.").size(18),
        text("It will only run one instance of the application at the same time.").size(14),
        button("OK").on_press(Notice::Ok),
    ]
    .spacing(16)
    .padding(24);
    container(body).width(Fill).height(Fill).into()
}

fn popup_origin(x: f64, y: f64) -> (f32, f32) {
    if x < 2.0 && y < 2.0 {
        return (80.0, 80.0);
    }
    let mut left = x as f32 - FORECAST_W / 2.0;
    let mut top = y as f32 - FORECAST_H - 14.0;
    if top < 8.0 {
        top = y as f32 + 24.0;
    }
    if left < 8.0 {
        left = 8.0;
    }
    (left, top)
}

fn fetch_task(config: Config) -> Task<Message> {
    if !config.is_configured() {
        return Task::done(Message::ShowLocation);
    }
    Task::perform(
        async move {
            let (tx, rx) = iced::futures::channel::oneshot::channel();
            std::thread::spawn(move || {
                let _ = tx.send(weather::fetch(&config));
            });
            rx.await
                .unwrap_or_else(|_| Err("Weather fetch was cancelled".into()))
        },
        Message::Fetched,
    )
}
