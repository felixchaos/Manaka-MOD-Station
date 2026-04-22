use std::path::PathBuf;

pub fn app_dir() -> PathBuf {
    // Always resolve the default data directory from the current user profile.
    // This avoids leaking a developer machine path into reset/default settings.
    let appdata = std::env::var("APPDATA")
        .unwrap_or_else(|_| {
            dirs_next_home()
                .join("AppData")
                .join("Roaming")
                .to_string_lossy()
                .to_string()
        });
    PathBuf::from(appdata).join("ManakaModStation")
}

fn dirs_next_home() -> PathBuf {
    std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."))
}

pub fn database_dir() -> PathBuf {
    app_dir().join("database")
}

pub fn default_custom_missions_dir() -> PathBuf {
    database_dir().join("CustomMissions")
}

fn configured_custom_missions_dir() -> Option<PathBuf> {
    let path = settings_file();
    let text = std::fs::read_to_string(path).ok()?;
    let raw = serde_json::from_str::<serde_json::Value>(&text).ok()?;
    raw.get("modLibraryDir")
        .and_then(|value| value.as_str())
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
}

pub fn custom_missions_dir() -> PathBuf {
    configured_custom_missions_dir().unwrap_or_else(default_custom_missions_dir)
}

pub fn settings_dir() -> PathBuf {
    database_dir().join("Settings")
}

pub fn settings_file() -> PathBuf {
    settings_dir().join("settings.json")
}

pub fn mods_state_file() -> PathBuf {
    settings_dir().join("mods_state.json")
}

pub fn ensure_dirs() {
    for d in &[
        app_dir(),
        database_dir(),
        settings_dir(),
        default_custom_missions_dir(),
        custom_missions_dir(),
    ] {
        let _ = std::fs::create_dir_all(d);
    }
}

#[tauri::command]
pub fn get_mod_library_path() -> String {
    custom_missions_dir().to_string_lossy().to_string()
}

#[tauri::command]
pub fn get_app_data_path() -> String {
    app_dir().to_string_lossy().to_string()
}

/// Read whether Windows is in dark mode directly from the registry.
/// WebView2's prefers-color-scheme media query is unreliable — this is the authoritative source.
#[cfg(target_os = "windows")]
fn is_system_dark_mode_win() -> bool {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x08000000;
    let Ok(o) = std::process::Command::new("reg")
        .args([
            "query",
            "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
            "/v",
            "AppsUseLightTheme",
        ])
        .creation_flags(CREATE_NO_WINDOW)
        .output()
    else {
        return true; // default dark
    };
    if !o.status.success() {
        return true;
    }
    let s = String::from_utf8_lossy(&o.stdout);
    // "0x1" means light mode; "0x0" means dark mode
    !s.contains("0x1")
}

#[tauri::command]
pub fn get_system_dark_mode() -> bool {
    #[cfg(target_os = "windows")]
    {
        return is_system_dark_mode_win();
    }
    #[cfg(not(target_os = "windows"))]
    false
}

#[cfg(target_os = "windows")]
fn get_system_accent_color_win() -> Option<String> {
    use windows::Win32::Foundation::BOOL;
    use windows::Win32::Graphics::Dwm::DwmGetColorizationColor;

    let mut color = 0u32;
    let mut opaque = BOOL(0);
    if unsafe { DwmGetColorizationColor(&mut color, &mut opaque) }.is_ok() {
        let red = ((color >> 16) & 0xFF) as u8;
        let green = ((color >> 8) & 0xFF) as u8;
        let blue = (color & 0xFF) as u8;
        return Some(format!("#{:02X}{:02X}{:02X}", red, green, blue));
    }
    None
}

#[tauri::command]
pub fn get_system_accent_color() -> String {
    #[cfg(target_os = "windows")]
    {
        return get_system_accent_color_win().unwrap_or_else(|| "#4F6BED".to_string());
    }
    #[cfg(not(target_os = "windows"))]
    "#4F6BED".to_string()
}
