use std::fs::{self, OpenOptions};
use std::io::Write;
use std::sync::Mutex;

use crate::config::log_path;

static FILE: Mutex<Option<std::fs::File>> = Mutex::new(None);

pub fn init() {
    let path = log_path();
    if let Some(dir) = path.parent() {
        let _ = fs::create_dir_all(dir);
    }
    let file = OpenOptions::new().create(true).append(true).open(&path).ok();
    *FILE.lock().expect("log lock") = file;
    info(&format!("Logging to {}", path.display()));
}

pub fn info(message: &str) {
    write_line("INFO", message);
}

pub fn warn(message: &str) {
    write_line("WARN", message);
}

fn write_line(level: &str, message: &str) {
    let stamp = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");
    let line = format!("{stamp} [{level}] systrayweather: {message}");
    eprintln!("{line}");
    if let Ok(mut slot) = FILE.lock() {
        if let Some(file) = slot.as_mut() {
            let _ = writeln!(file, "{line}");
            let _ = file.flush();
        }
    }
}
