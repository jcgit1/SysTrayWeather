use std::fs;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

pub const DEFAULT_POLL_MINUTES: u32 = 20;

/// Forecast popup theme: "light", "dark", or "system".
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ThemeChoice {
    Light,
    Dark,
    System,
}

impl Default for ThemeChoice {
    fn default() -> Self {
        Self::System
    }
}

impl ThemeChoice {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Light => "light",
            Self::Dark => "dark",
            Self::System => "system",
        }
    }
}

/// True when the config asks for Celsius; anything else stays Fahrenheit.
pub fn is_metric(units: &str) -> bool {
    units.eq_ignore_ascii_case("metric")
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default)]
    pub location_query: String,
    #[serde(default)]
    pub location_name: String,
    #[serde(default)]
    pub latitude: f64,
    #[serde(default)]
    pub longitude: f64,
    #[serde(default = "auto_tz")]
    pub timezone: String,
    #[serde(default = "imperial")]
    pub units: String,
    #[serde(default = "default_poll")]
    pub poll_interval_minutes: u32,
    #[serde(default)]
    pub location_setup_complete: bool,
    #[serde(default)]
    pub show_unit_on_icon: bool,
    #[serde(default)]
    pub theme: ThemeChoice,
}

fn auto_tz() -> String {
    "auto".into()
}
fn imperial() -> String {
    "imperial".into()
}
fn default_poll() -> u32 {
    DEFAULT_POLL_MINUTES
}

impl Default for Config {
    fn default() -> Self {
        Self {
            location_query: String::new(),
            location_name: String::new(),
            latitude: 0.0,
            longitude: 0.0,
            timezone: auto_tz(),
            units: imperial(),
            poll_interval_minutes: DEFAULT_POLL_MINUTES,
            location_setup_complete: false,
            show_unit_on_icon: false,
            theme: ThemeChoice::default(),
        }
    }
}

impl Config {
    pub fn is_configured(&self) -> bool {
        self.location_setup_complete
            && self.latitude != 0.0
            && self.longitude != 0.0
            && !self.location_name.is_empty()
    }

    pub fn load() -> Self {
        let path = config_path();
        let Ok(text) = fs::read_to_string(&path) else {
            return Self::default();
        };
        serde_json::from_str(&text).unwrap_or_default()
    }

    pub fn save(&self) -> Result<(), String> {
        let path = config_path();
        if let Some(dir) = path.parent() {
            fs::create_dir_all(dir).map_err(|err| err.to_string())?;
        }
        let text = serde_json::to_string_pretty(self).map_err(|err| err.to_string())?;
        fs::write(path, text + "\n").map_err(|err| err.to_string())
    }
}

pub fn config_path() -> PathBuf {
    config_dir().join("config.json")
}

pub fn config_dir() -> PathBuf {
    #[cfg(windows)]
    {
        let base = std::env::var_os("APPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("."));
        base.join("systrayweather")
    }
    #[cfg(not(windows))]
    {
        let home = std::env::var_os("HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("."));
        home.join(".config").join("systrayweather")
    }
}

pub fn log_path() -> PathBuf {
    #[cfg(windows)]
    {
        let base = std::env::var_os("LOCALAPPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("."));
        base.join("systrayweather").join("systrayweather.log")
    }
    #[cfg(not(windows))]
    {
        let home = std::env::var_os("HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("."));
        home.join(".local")
            .join("log")
            .join("systrayweather")
            .join("systrayweather.log")
    }
}
