mod config;
mod icon;
mod instance;
mod log;
mod sky;
mod tray;
mod weather;

use std::time::{Duration, Instant};

use iced::widget::{button, column, container, row, text, text_input};
use iced::window::{self, Level, Position};
use iced::{Color, Element, Fill, Point, Size, Subscription, Task, Theme};

use config::Config;
use weather::{Snapshot, Sky};

const FORECAST_W: f32 = 700.0;
const FORECAST_H: f32 = 330.0;

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
        .theme(Theme::Dark)
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
        } else {
            "SysTrayWeather".into()
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
                        let label = format!("{}°", snapshot.current_f.round());
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
            Message::WindowOpened => Task::none(),
            Message::WindowClosed(id) => {
                if self.forecast == Some(id) {
                    self.forecast = None;
                    self.forecast_at = None;
                }
                if self.location == Some(id) {
                    self.location = None;
                }
                Task::none()
            }
            Message::Quit => {
                log::info("Quit requested, shutting down");
                iced::exit()
            }
        }
    }

    fn view(&self, id: window::Id) -> Element<'_, Message> {
        if self.location == Some(id) {
            return location_view(self);
        }
        forecast_view(self)
    }
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
            text(format!("{}°", day.temp_max_f.round())).size(14),
            text(format!("{}°", day.temp_min_f.round()))
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
