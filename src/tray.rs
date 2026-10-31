use std::cell::RefCell;

use tray_icon::menu::{Menu, MenuEvent, MenuItem};
use tray_icon::{Icon, MouseButton, MouseButtonState, TrayIcon, TrayIconBuilder, TrayIconEvent};

pub enum TrayAction {
    Activate { x: f64, y: f64 },
    Refresh,
    Location,
    Quit,
}

thread_local! {
    static TRAY: RefCell<Option<TrayIcon>> = RefCell::new(None);
}

pub fn install() -> Result<(), String> {
    let refresh = MenuItem::with_id("refresh", "Refresh", true, None);
    let location = MenuItem::with_id("location", "Location…", true, None);
    let quit = MenuItem::with_id("quit", "Quit", true, None);
    let menu = Menu::new();
    menu.append(&refresh).map_err(|err| err.to_string())?;
    menu.append(&location).map_err(|err| err.to_string())?;
    menu.append(&quit).map_err(|err| err.to_string())?;

    let (rgba, width, height) = crate::icon::temperature_icon("--")?;
    let icon = Icon::from_rgba(rgba, width, height).map_err(|err| err.to_string())?;

    let builder = TrayIconBuilder::new()
        .with_menu(Box::new(menu))
        .with_tooltip("SysTrayWeather")
        .with_icon(icon);
    #[cfg(windows)]
    let builder = builder.with_menu_on_left_click(false);
    let tray = builder.build().map_err(|err| err.to_string())?;
    TRAY.with(|slot| *slot.borrow_mut() = Some(tray));
    Ok(())
}

pub fn drain() -> Vec<TrayAction> {
    let mut actions = Vec::new();
    while let Ok(event) = TrayIconEvent::receiver().try_recv() {
        crate::log::info(&format!("tray event: {event:?}"));
        match event {
            TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                position,
                ..
            }
            | TrayIconEvent::DoubleClick {
                button: MouseButton::Left,
                position,
                ..
            } => actions.push(TrayAction::Activate {
                x: position.x,
                y: position.y,
            }),
            _ => {}
        }
    }
    while let Ok(event) = MenuEvent::receiver().try_recv() {
        crate::log::info(&format!("tray menu: {}", event.id.0));
        match event.id.0.as_str() {
            "refresh" => actions.push(TrayAction::Refresh),
            "location" => actions.push(TrayAction::Location),
            "quit" => actions.push(TrayAction::Quit),
            _ => {}
        }
    }
    actions
}

pub fn set_temperature(label: &str, tooltip: &str) {
    let Ok((rgba, width, height)) = crate::icon::temperature_icon(label) else {
        return;
    };
    let Ok(icon) = Icon::from_rgba(rgba, width, height) else {
        return;
    };
    TRAY.with(|slot| {
        if let Some(tray) = slot.borrow().as_ref() {
            let _ = tray.set_icon(Some(icon));
            let _ = tray.set_tooltip(Some(tooltip));
        }
    });
}
