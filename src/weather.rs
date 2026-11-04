use chrono::{NaiveDate, Utc};
use serde::Deserialize;

use crate::config::Config;

#[derive(Debug, Clone)]
pub struct Snapshot {
    pub location_name: String,
    /// Current temperature in the unit the fetch asked for (`metric` says which).
    pub current: f64,
    pub metric: bool,
    pub days: Vec<Day>,
}

#[derive(Debug, Clone)]
pub struct Day {
    pub date: NaiveDate,
    pub is_today: bool,
    pub weather_code: i32,
    pub temp_max: f64,
    pub temp_min: f64,
    pub precip: f64,
    pub precip_probability: Option<i32>,
    pub snowfall: f64,
    pub cloud_cover: Option<i32>,
    pub metric: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Sky {
    Clear,
    MostlySunny,
    Partly,
    Cloudy,
    Fog,
    Drizzle,
    Rain,
    Snow,
    Sleet,
    Storm,
}

impl Sky {
    pub fn label(self) -> &'static str {
        match self {
            Self::Clear => "Clear",
            Self::MostlySunny => "Mostly sunny",
            Self::Partly => "Partly cloudy",
            Self::Cloudy => "Cloudy",
            Self::Fog => "Fog",
            Self::Drizzle => "Drizzle",
            Self::Rain => "Rain",
            Self::Snow => "Snow",
            Self::Sleet => "Wintry mix",
            Self::Storm => "Storm",
        }
    }
}

const STORM: &[i32] = &[95, 96, 99];
const SNOW: &[i32] = &[71, 73, 75, 77, 85, 86];
const RAIN: &[i32] = &[61, 63, 65, 80, 81, 82];
const DRIZZLE: &[i32] = &[51, 53, 55];
const FREEZING: &[i32] = &[56, 57, 66, 67];
const FOG: &[i32] = &[45, 48];

pub fn sky_kind(day: &Day) -> Sky {
    let code = day.weather_code;
    if STORM.contains(&code) {
        return Sky::Storm;
    }
    let snowing = SNOW.contains(&code) || day.snowfall >= precip_trace(day.metric);
    let raining = RAIN.contains(&code) || DRIZZLE.contains(&code) || FREEZING.contains(&code);
    if snowing && (raining || (day.precip >= precip_trace(day.metric) && !SNOW.contains(&code))) {
        return Sky::Sleet;
    }
    if snowing {
        return Sky::Snow;
    }
    if FREEZING.contains(&code) {
        return Sky::Sleet;
    }
    if DRIZZLE.contains(&code) {
        return Sky::Drizzle;
    }
    if RAIN.contains(&code) || day.precip >= precip_rain(day.metric) {
        return Sky::Rain;
    }
    if day.precip >= precip_trace(day.metric) {
        return Sky::Drizzle;
    }
    if FOG.contains(&code) {
        return Sky::Fog;
    }
    let cloud = day.cloud_cover;
    if (0..=3).contains(&code) {
        let kind = match code {
            0 => Sky::Clear,
            1 => Sky::MostlySunny,
            2 => Sky::Partly,
            _ => Sky::Cloudy,
        };
        if let Some(cloud) = cloud {
            if code <= 1 && cloud >= 55 {
                return Sky::Partly;
            }
            if code == 3 && cloud < 40 {
                return Sky::Partly;
            }
            if code == 0 && cloud >= 20 {
                return Sky::MostlySunny;
            }
        }
        return kind;
    }
    Sky::Partly
}

/// Precip amounts scale with the unit system: 0.01 in is a trace, ~2 mm in metric.
fn precip_trace(metric: bool) -> f64 {
    if metric {
        0.25
    } else {
        0.01
    }
}

fn precip_rain(metric: bool) -> f64 {
    if metric {
        2.5
    } else {
        0.1
    }
}

pub fn precip_lines(day: &Day) -> Vec<String> {
    let mut lines = Vec::new();
    let kind = sky_kind(day);
    if day.snowfall >= precip_trace(day.metric) {
        lines.push(format!("{} snow", amount(day.snowfall, day.metric)));
    }
    if day.precip >= precip_trace(day.metric) && kind != Sky::Snow {
        let mut text = amount(day.precip, day.metric);
        if day.snowfall >= precip_trace(day.metric) {
            text = format!("{text} rain");
        }
        lines.push(text);
    }
    if lines.is_empty() {
        lines.push("No precip".into());
    }
    lines
}

pub fn amount(value: f64, metric: bool) -> String {
    if metric {
        if value >= 10.0 {
            format!("{value:.0} mm")
        } else {
            format!("{value:.1} mm")
        }
    } else if value >= 1.0 {
        format!("{value:.1} in")
    } else {
        format!("{value:.2} in")
    }
}

pub fn fetch(config: &Config) -> Result<Snapshot, String> {
    let metric = crate::config::is_metric(&config.units);
    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(20))
        .build()
        .map_err(|err| err.to_string())?;
    let response = client
        .get("https://api.open-meteo.com/v1/forecast")
        .query(&[
            ("latitude", config.latitude.to_string()),
            ("longitude", config.longitude.to_string()),
            ("timezone", config.timezone.clone()),
            ("current", "temperature_2m".into()),
            (
                "daily",
                "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,snowfall_sum,cloud_cover_mean".into(),
            ),
            ("forecast_days", "5".into()),
            (
                "temperature_unit",
                if metric { "celsius" } else { "fahrenheit" }.into(),
            ),
            (
                "precipitation_unit",
                if metric { "millimeter" } else { "inch" }.into(),
            ),
        ])
        .send()
        .map_err(|err| err.to_string())?
        .error_for_status()
        .map_err(|err| err.to_string())?;
    let payload: ForecastPayload = response.json().map_err(|err| err.to_string())?;
    let temp = payload
        .current
        .as_ref()
        .and_then(|current| current.temperature_2m)
        .ok_or_else(|| "No current temperature returned".to_string())?;
    let days = parse_days(&payload);
    crate::log::info(&format!(
        "Open-Meteo: {} temp={temp:.1}{} days={}",
        config.location_name,
        if metric { "C" } else { "F" },
        days.len()
    ));
    Ok(Snapshot {
        location_name: config.location_name.clone(),
        current: temp,
        metric,
        days,
    })
}

pub fn geocode(query: &str) -> Result<Config, String> {
    let cleaned = query.trim();
    if cleaned.is_empty() {
        return Err("Enter a city name or 5-digit US zip code.".into());
    }
    if cleaned.chars().all(|ch| ch.is_ascii_digit()) && cleaned.len() != 5 {
        return Err("Enter a valid 5-digit US zip code.".into());
    }
    if !cleaned.chars().all(|ch| ch.is_ascii_digit()) && cleaned.chars().count() < 2 {
        return Err("Enter at least 2 characters for a city search.".into());
    }

    let client = reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(20))
        .build()
        .map_err(|err| err.to_string())?;
    let mut request = client
        .get("https://geocoding-api.open-meteo.com/v1/search")
        .query(&[("name", cleaned), ("count", "5"), ("language", "en")]);
    if cleaned.chars().all(|ch| ch.is_ascii_digit()) {
        request = request.query(&[("countryCode", "US")]);
    }
    let response = request
        .send()
        .map_err(|err| err.to_string())?
        .error_for_status()
        .map_err(|err| err.to_string())?;
    let payload: GeoPayload = response.json().map_err(|err| err.to_string())?;
    let place = payload
        .results
        .into_iter()
        .flatten()
        .next()
        .ok_or_else(|| format!("No location found for \"{cleaned}\""))?;
    let location_name = match (place.admin1, place.country) {
        (Some(admin), _) if !admin.is_empty() => format!("{}, {admin}", place.name),
        (_, Some(country)) if !country.is_empty() => format!("{}, {country}", place.name),
        _ => place.name.clone(),
    };
    // Keep the user's existing settings; a location change replaces only
    // the location fields.
    let mut config = Config::load();
    config.location_query = cleaned.to_string();
    config.location_name = location_name;
    config.latitude = place.latitude;
    config.longitude = place.longitude;
    config.timezone = place.timezone.unwrap_or_else(|| "auto".into());
    config.location_setup_complete = true;
    Ok(config)
}

fn parse_days(payload: &ForecastPayload) -> Vec<Day> {
    let Some(daily) = payload.daily.as_ref() else {
        return Vec::new();
    };
    let metric = payload
        .current_units
        .as_ref()
        .and_then(|units| units.temperature_2m.as_deref())
        .map_or(false, |unit| unit == "°C");
    let offset = payload.utc_offset_seconds.unwrap_or(0);
    let today = (Utc::now() + chrono::Duration::seconds(offset)).date_naive();
    let mut days = Vec::new();
    for (index, raw) in daily.time.iter().take(5).enumerate() {
        let Ok(date) = NaiveDate::parse_from_str(raw, "%Y-%m-%d") else {
            continue;
        };
        let (Some(code), Some(high), Some(low)) = (
            at(&daily.weather_code, index),
            at(&daily.temperature_2m_max, index),
            at(&daily.temperature_2m_min, index),
        ) else {
            continue;
        };
        days.push(Day {
            date,
            is_today: date == today,
            weather_code: code as i32,
            temp_max: high,
            temp_min: low,
            precip: at(&daily.precipitation_sum, index).unwrap_or(0.0),
            precip_probability: at(&daily.precipitation_probability_max, index).map(|v| v as i32),
            snowfall: at(&daily.snowfall_sum, index).unwrap_or(0.0),
            cloud_cover: at(&daily.cloud_cover_mean, index).map(|v| v.round() as i32),
            metric,
        });
    }
    days
}

fn at(values: &Option<Vec<Option<f64>>>, index: usize) -> Option<f64> {
    values.as_ref()?.get(index)?.as_ref().copied()
}

#[derive(Deserialize)]
struct ForecastPayload {
    utc_offset_seconds: Option<i64>,
    current: Option<Current>,
    #[serde(rename = "current_units")]
    current_units: Option<CurrentUnits>,
    daily: Option<Daily>,
}

#[derive(Deserialize)]
struct CurrentUnits {
    temperature_2m: Option<String>,
}

#[derive(Deserialize)]
struct Current {
    temperature_2m: Option<f64>,
}

#[derive(Deserialize)]
struct Daily {
    time: Vec<String>,
    weather_code: Option<Vec<Option<f64>>>,
    temperature_2m_max: Option<Vec<Option<f64>>>,
    temperature_2m_min: Option<Vec<Option<f64>>>,
    precipitation_sum: Option<Vec<Option<f64>>>,
    precipitation_probability_max: Option<Vec<Option<f64>>>,
    snowfall_sum: Option<Vec<Option<f64>>>,
    cloud_cover_mean: Option<Vec<Option<f64>>>,
}

#[derive(Deserialize)]
struct GeoPayload {
    results: Option<Vec<GeoPlace>>,
}

#[derive(Deserialize)]
struct GeoPlace {
    name: String,
    latitude: f64,
    longitude: f64,
    timezone: Option<String>,
    admin1: Option<String>,
    country: Option<String>,
}
