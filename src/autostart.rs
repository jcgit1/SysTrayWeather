use std::fs;
use std::path::PathBuf;

const DESKTOP_BODY: &str = "\
[Desktop Entry]
Type=Application
Name=SysTrayWeather
Comment=System tray weather indicator for KDE Plasma
Exec={exec}
Icon=weather-clear
Terminal=false
Categories=Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
OnlyShowIn=KDE;
";

pub fn is_enabled() -> bool {
    #[cfg(windows)]
    {
        win::is_enabled()
    }
    #[cfg(not(windows))]
    {
        autostart_file().exists()
    }
}

pub fn set_enabled(enabled: bool) -> Result<(), String> {
    #[cfg(windows)]
    {
        return win::set_enabled(enabled);
    }
    #[cfg(not(windows))]
    {
        let path = autostart_file();
        if !enabled {
            if path.exists() {
                fs::remove_file(&path).map_err(|err| err.to_string())?;
            }
            crate::log::info("Autostart disabled");
            return Ok(());
        }
        let exec = std::env::current_exe()
            .map_err(|err| err.to_string())?
            .to_string_lossy()
            .into_owned();
        if let Some(dir) = path.parent() {
            fs::create_dir_all(dir).map_err(|err| err.to_string())?;
        }
        // The repo template uses a bare Exec; the installed entry needs the
        // absolute path so Plasma can find the binary without a login PATH.
        fs::write(&path, DESKTOP_BODY.replace("{exec}", &exec)).map_err(|err| err.to_string())?;
        crate::log::info(&format!("Autostart enabled: {exec}"));
        Ok(())
    }
}

#[cfg(not(windows))]
fn autostart_file() -> PathBuf {
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."));
    home.join(".config")
        .join("autostart")
        .join("com.systrayweather.app.desktop")
}

#[cfg(windows)]
mod win {
    use winreg::enums::{HKEY_CURRENT_USER, KEY_SET_VALUE};
    use winreg::RegKey;

    const RUN_KEY: &str = r"Software\Microsoft\Windows\CurrentVersion\Run";
    const VALUE: &str = "SysTrayWeather";

    pub fn is_enabled() -> bool {
        run_key()
            .and_then(|key| key.get_value::<String, _>(VALUE).map_err(Into::into))
            .is_ok()
    }

    pub fn set_enabled(enabled: bool) -> Result<(), String> {
        let key = run_key()?;
        if enabled {
            let exe = std::env::current_exe()
                .map_err(|err| err.to_string())?
                .to_string_lossy()
                .into_owned();
            key.set_value(VALUE, &exe).map_err(|err| err.to_string())?;
            crate::log::info(&format!("Autostart enabled: {exe}"));
        } else {
            let _ = key.delete_value(VALUE);
            crate::log::info("Autostart disabled");
        }
        Ok(())
    }

    fn run_key() -> Result<RegKey, String> {
        RegKey::predef(HKEY_CURRENT_USER)
            .open_subkey_with_flags(RUN_KEY, KEY_SET_VALUE)
            .map_err(|err| err.to_string())
    }
}
