use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};

use super::config::{custom_missions_dir, mods_state_file};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ModInfo {
    pub filename: String,
    pub name: String,
    pub enabled: bool,
    pub version: Option<String>,
    pub author: Option<String>,
    pub descriptions: Vec<String>,
    pub stage: Option<String>,
    pub is_warp: bool,
    pub start_condition: Option<String>,
}

#[derive(Debug, Serialize, Clone)]
pub struct ExplorerEntry {
    pub name: String,
    pub path: String,
    #[serde(rename = "isDirectory")]
    pub is_directory: bool,
}

fn load_state() -> HashMap<String, bool> {
    let path = mods_state_file();
    if !path.exists() {
        return HashMap::new();
    }
    let text = fs::read_to_string(&path).unwrap_or_default();
    serde_json::from_str(&text).unwrap_or_default()
}

fn save_state(state: &HashMap<String, bool>) {
    let path = mods_state_file();
    if let Some(parent) = path.parent() {
        let _ = fs::create_dir_all(parent);
    }
    if let Ok(text) = serde_json::to_string_pretty(state) {
        let _ = fs::write(&path, text);
    }
}

fn map_stage_name(s: &str) -> &str {
    match s {
        "ShoppingMall" | "Mall" => "Mall",
        "Convenience" | "ConvenienceStore" | "Conve" => "Convenience",
        "Park" => "Park",
        "Apartment" | "Apartment2" => "Apartment",
        "Downtown" => "Downtown",
        "Residential" => "Residential",
        "Shop" | "ShoppingStore" | "ClothingStore" | "Shop_B" => "Shop",
        _ => s,
    }
}

fn infer_stage(title: &str, stem: &str) -> Option<String> {
    let text = format!("{} {}", stem, title).to_lowercase();
    let rules: &[(&[&str], &str)] = &[
        (&["park", "公园", "fountain", "bridge", "toilet"], "Park"),
        (&["mall", "商场", "hella", "elevator"], "Mall"),
        (&["shop", "clothing", "商店", "ch shop", "chshop"], "Shop"),
        (&["res ", "resident", "住宅", "小区"], "Residential"),
        (&["apart", "apartment", "公寓"], "Apartment"),
        (&["dtown", "downtown", "市中心", " down"], "Downtown"),
        (&["conv", "convenience", "便利店"], "Convenience"),
        (&["alley", "小巷"], "Alley"),
    ];
    for (keys, label) in rules {
        if keys.iter().any(|k| text.contains(k)) {
            return Some(label.to_string());
        }
    }
    None
}

fn parse_metadata(path: &Path) -> ModInfo {
    let filename = path
        .file_name()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();
    let stem = path
        .file_stem()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();

    let text = match fs::read_to_string(path) {
        Ok(t) => t,
        Err(_) => {
            return ModInfo {
                filename,
                name: stem,
                enabled: true,
                version: None,
                author: None,
                descriptions: vec![],
                stage: None,
                is_warp: false,
                start_condition: None,
            }
        }
    };

    let obj: serde_json::Value = match serde_json::from_str(&text) {
        Ok(v) => v,
        Err(_) => {
            return ModInfo {
                filename,
                name: stem,
                enabled: true,
                version: None,
                author: None,
                descriptions: vec![],
                stage: None,
                is_warp: false,
                start_condition: None,
            }
        }
    };

    let title = obj
        .get("title")
        .and_then(|v| v.as_str())
        .filter(|s| !s.is_empty())
        .unwrap_or(&stem)
        .to_string();

    let version = obj
        .get("version")
        .or_else(|| obj.get("ver"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let author = obj
        .get("author")
        .or_else(|| obj.get("by"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    // Collect descriptions from checkpoints
    let mut descriptions = vec![];
    if let Some(cps) = obj.get("checkpoints").and_then(|v| v.as_array()) {
        for cp in cps {
            for key in &["condition", "travelcondition"] {
                if let Some(d) = cp
                    .get(key)
                    .and_then(|b| b.get("description"))
                    .and_then(|v| v.as_str())
                {
                    let d = d.trim();
                    if !d.is_empty() {
                        descriptions.push(d.to_string());
                    }
                }
            }
        }
    }

    // Stage: read from zones[0].areas[0].stage (actual game JSON schema)
    let stage = obj
        .get("zones")
        .and_then(|v| v.as_array())
        .and_then(|z| z.first())
        .and_then(|z| z.get("areas"))
        .and_then(|v| v.as_array())
        .and_then(|a| a.first())
        .and_then(|a| a.get("stage"))
        .and_then(|v| v.as_str())
        .filter(|s| !s.is_empty())
        .map(|s| map_stage_name(s).to_string())
        .or_else(|| infer_stage(&title, &stem));

    // is_warp
    let is_warp = title.to_lowercase().contains("warp")
        || text.to_lowercase().contains("warp");

    // start_condition: subconditions[0].condition or first checkpoint condition
    let start_condition = obj
        .get("subconditions")
        .and_then(|v| v.as_array())
        .and_then(|a| a.first())
        .and_then(|s| s.get("condition"))
        .map(|v| serde_json::to_string_pretty(v).unwrap_or_default())
        .or_else(|| {
            obj.get("checkpoints")
                .and_then(|v| v.as_array())
                .and_then(|cps| {
                    for cp in cps {
                        for key in &["condition", "travelcondition"] {
                            if let Some(blk) = cp.get(key) {
                                if blk.is_object() {
                                    return Some(
                                        serde_json::to_string_pretty(blk).unwrap_or_default(),
                                    );
                                }
                            }
                        }
                    }
                    None
                })
        });

    ModInfo {
        filename,
        name: title,
        enabled: true,
        version,
        author,
        descriptions,
        stage,
        is_warp,
        start_condition,
    }
}

#[tauri::command]
pub fn scan_mods() -> Vec<ModInfo> {
    let dir = custom_missions_dir();
    let _ = fs::create_dir_all(&dir);
    let state = load_state();

    let mut mods: Vec<ModInfo> = vec![];
    let mut entries: Vec<PathBuf> = match fs::read_dir(&dir) {
        Ok(rd) => rd
            .filter_map(|e| e.ok())
            .map(|e| e.path())
            .filter(|p| p.extension().map(|e| e == "json").unwrap_or(false))
            .collect(),
        Err(_) => vec![],
    };
    entries.sort();

    for path in entries {
        let mut info = parse_metadata(&path);
        let enabled = state.get(&info.filename).copied().unwrap_or(true);
        info.enabled = enabled;
        mods.push(info);
    }
    mods
}

#[tauri::command]
pub fn set_mod_enabled(filename: String, enabled: bool) -> Result<(), String> {
    let mut state = load_state();
    state.insert(filename, enabled);
    save_state(&state);
    Ok(())
}

#[tauri::command]
pub fn set_all_mods_enabled(enabled: bool) -> Result<(), String> {
    let dir = custom_missions_dir();
    let mut state = load_state();
    if let Ok(rd) = fs::read_dir(&dir) {
        for entry in rd.filter_map(|e| e.ok()) {
            let path = entry.path();
            if path.extension().map(|e| e == "json").unwrap_or(false) {
                let fname = path
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .to_string();
                state.insert(fname, enabled);
            }
        }
    }
    save_state(&state);
    Ok(())
}

#[tauri::command]
pub fn delete_mod(filename: String) -> Result<(), String> {
    let path = custom_missions_dir().join(&filename);
    if path.exists() {
        fs::remove_file(&path).map_err(|e| e.to_string())?;
    }
    let mut state = load_state();
    state.remove(&filename);
    save_state(&state);
    Ok(())
}

#[tauri::command]
pub fn read_mod_file(filename: String) -> Result<String, String> {
    let path = custom_missions_dir().join(&filename);
    fs::read_to_string(&path).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn write_mod_file(filename: String, content: String) -> Result<(), String> {
    // Validate JSON before writing
    serde_json::from_str::<serde_json::Value>(&content)
        .map_err(|e| format!("Invalid JSON: {}", e))?;
    let path = custom_missions_dir().join(&filename);
    fs::write(&path, content).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn list_directory(path: String) -> Result<Vec<ExplorerEntry>, String> {
    let mut entries = fs::read_dir(&path)
        .map_err(|e| e.to_string())?
        .filter_map(|entry| entry.ok())
        .map(|entry| {
            let path = entry.path();
            ExplorerEntry {
                name: entry.file_name().to_string_lossy().to_string(),
                path: path.to_string_lossy().to_string(),
                is_directory: path.is_dir(),
            }
        })
        .collect::<Vec<_>>();

    entries.sort_by(|left, right| {
        left.is_directory
            .cmp(&right.is_directory)
            .reverse()
            .then_with(|| left.name.to_lowercase().cmp(&right.name.to_lowercase()))
    });

    Ok(entries)
}

#[tauri::command]
pub fn read_text_file_absolute(path: String) -> Result<String, String> {
    fs::read_to_string(path).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn write_text_file_absolute(path: String, content: String) -> Result<(), String> {
    let file_path = PathBuf::from(&path);
    if file_path
        .extension()
        .and_then(|ext| ext.to_str())
        .is_some_and(|ext| ext.eq_ignore_ascii_case("json"))
    {
        serde_json::from_str::<serde_json::Value>(&content)
            .map_err(|e| format!("Invalid JSON: {}", e))?;
    }

    if let Some(parent) = file_path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }

    fs::write(file_path, content).map_err(|e| e.to_string())
}

pub fn compute_sha256(path: &Path) -> Result<String, String> {
    let mut file = fs::File::open(path).map_err(|e| e.to_string())?;
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 1024 * 1024];
    loop {
        let n = file.read(&mut buf).map_err(|e| e.to_string())?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hex::encode(hasher.finalize()))
}
