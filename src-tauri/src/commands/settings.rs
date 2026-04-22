use serde::{Deserialize, Serialize};
use std::fs;

use super::config::{ensure_dirs, settings_file};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Settings {
    pub language: String,
    pub theme: String,
    #[serde(rename = "gameDir")]
    pub game_dir: Option<String>,
    #[serde(rename = "modLibraryDir")]
    pub mod_library_dir: Option<String>,
    #[serde(rename = "rememberLastPage")]
    pub remember_last_page: bool,
    #[serde(rename = "rememberLastSelectedMod")]
    pub remember_last_selected_mod: bool,
    #[serde(rename = "rememberCollapsedGroups")]
    pub remember_collapsed_groups: bool,
    #[serde(rename = "confirmDelete")]
    pub confirm_delete: bool,
    pub encoding: String,
    #[serde(rename = "lastUpdateCheck")]
    pub last_update_check: Option<String>,
    #[serde(rename = "startupUpdateCheck")]
    pub startup_update_check: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Settings {
            language: "zh-CN".to_string(),
            theme: "system".to_string(),
            game_dir: None,
            mod_library_dir: None,
            remember_last_page: true,
            remember_last_selected_mod: true,
            remember_collapsed_groups: true,
            confirm_delete: true,
            encoding: "UTF-8".to_string(),
            last_update_check: None,
            startup_update_check: true,
        }
    }
}

#[tauri::command]
pub fn load_settings() -> Settings {
    ensure_dirs();
    let path = settings_file();
    if !path.exists() {
        let defaults = Settings::default();
        let _ = save_settings_inner(&defaults);
        return defaults;
    }
    let text = fs::read_to_string(&path).unwrap_or_default();
    let raw: serde_json::Value = serde_json::from_str(&text).unwrap_or(serde_json::Value::Object(
        serde_json::Map::new(),
    ));

    let mut s = Settings::default();
    if let Some(v) = raw.get("language").and_then(|v| v.as_str()) {
        s.language = v.to_string();
    }
    if let Some(v) = raw.get("theme").and_then(|v| v.as_str()) {
        if ["system", "light", "dark"].contains(&v) {
            s.theme = v.to_string();
        }
    }
    if let Some(v) = raw.get("gameDir") {
        s.game_dir = v.as_str().map(|s| s.to_string());
    }
    if let Some(v) = raw.get("modLibraryDir") {
        s.mod_library_dir = v
            .as_str()
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
    }
    if let Some(v) = raw.get("rememberLastPage").and_then(|v| v.as_bool()) {
        s.remember_last_page = v;
    }
    if let Some(v) = raw.get("rememberLastSelectedMod").and_then(|v| v.as_bool()) {
        s.remember_last_selected_mod = v;
    }
    if let Some(v) = raw.get("rememberCollapsedGroups").and_then(|v| v.as_bool()) {
        s.remember_collapsed_groups = v;
    }
    if let Some(v) = raw.get("confirmDelete").and_then(|v| v.as_bool()) {
        s.confirm_delete = v;
    }
    if let Some(v) = raw.get("encoding").and_then(|v| v.as_str()) {
        s.encoding = v.to_string();
    }
    if let Some(v) = raw.get("lastUpdateCheck") {
        s.last_update_check = v.as_str().map(|s| s.to_string());
    }
    if let Some(v) = raw.get("startupUpdateCheck").and_then(|v| v.as_bool()) {
        s.startup_update_check = v;
    }
    s
}

fn save_settings_inner(s: &Settings) -> Result<(), String> {
    ensure_dirs();
    if let Some(path) = s.mod_library_dir.as_deref() {
        if !path.trim().is_empty() {
            std::fs::create_dir_all(path).map_err(|e| e.to_string())?;
        }
    }

    let mut normalized = s.clone();
    normalized.mod_library_dir = normalized
        .mod_library_dir
        .map(|path| path.trim().to_string())
        .filter(|path| !path.is_empty());

    let text = serde_json::to_string_pretty(&normalized).map_err(|e| e.to_string())?;
    fs::write(settings_file(), text).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn save_settings(settings: Settings) -> Result<(), String> {
    save_settings_inner(&settings)
}

#[tauri::command]
pub fn reset_settings() -> Settings {
    let defaults = Settings::default();
    let _ = save_settings_inner(&defaults);
    defaults
}
