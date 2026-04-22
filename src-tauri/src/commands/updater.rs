use serde::{Deserialize, Serialize};
use std::fs;
use std::io;
use std::process::Command;

const REPO: &str = "felixchaos/Manaka-MOD-Station";

#[derive(Debug, Serialize, Deserialize)]
pub struct UpdateInfo {
    pub update_available: bool,
    pub latest_version: String,
    pub current_version: String,
    pub release_url: Option<String>,
    pub installer_name: Option<String>,
    pub installer_url: Option<String>,
    pub notes: Option<String>,
    pub error: Option<String>,
}

fn parse_semver(v: &str) -> (u32, u32, u32) {
    let v = v.trim_start_matches('v').trim_start_matches('V');
    let parts: Vec<&str> = v.split('.').collect();
    let get = |i: usize| parts.get(i).and_then(|s| s.parse().ok()).unwrap_or(0);
    (get(0), get(1), get(2))
}

fn fetch_latest_release() -> Result<serde_json::Value, String> {
    let url = format!("https://api.github.com/repos/{}/releases/latest", REPO);

    let client = ureq::builder()
        .timeout(std::time::Duration::from_secs(15))
        .build()
        .get(&url)
        .set("User-Agent", "ManakaModStation-Updater/1.1")
        .call()
        .map_err(|e| e.to_string())?;

    let body = client.into_string().map_err(|e| e.to_string())?;
    serde_json::from_str(&body).map_err(|e| e.to_string())
}

fn asset_score(name: &str) -> i32 {
    let lower = name.to_lowercase();
    let mut score = if lower.ends_with(".msi") {
        100
    } else if lower.ends_with(".exe") {
        60
    } else {
        return -10_000;
    };

    match std::env::consts::ARCH {
        "x86_64" => {
            if ["x64", "x86_64", "amd64"].iter().any(|t| lower.contains(t)) {
                score += 20;
            }
            if ["arm64", "aarch64", "ia32", "i686", "x86"].iter().any(|t| lower.contains(t)) {
                score -= 100;
            }
        }
        "aarch64" => {
            if ["arm64", "aarch64"].iter().any(|t| lower.contains(t)) {
                score += 20;
            }
            if ["x64", "x86_64", "amd64", "ia32", "i686", "x86"].iter().any(|t| lower.contains(t)) {
                score -= 100;
            }
        }
        _ => {}
    }

    score
}

fn select_installer_asset(data: &serde_json::Value) -> Option<(String, String)> {
    data.get("assets")
        .and_then(|v| v.as_array())
        .and_then(|assets| {
            assets
                .iter()
                .filter_map(|asset| {
                    let name = asset.get("name")?.as_str()?.to_string();
                    let url = asset.get("browser_download_url")?.as_str()?.to_string();
                    Some((asset_score(&name), name, url))
                })
                .max_by_key(|(score, _, _)| *score)
                .and_then(|(score, name, url)| if score > 0 { Some((name, url)) } else { None })
        })
}

#[tauri::command]
pub fn check_for_updates(current_version: String) -> UpdateInfo {
    let data = match fetch_latest_release() {
        Ok(v) => v,
        Err(e) => {
            return UpdateInfo {
                update_available: false,
                latest_version: current_version.clone(),
                current_version,
                release_url: None,
                installer_name: None,
                installer_url: None,
                notes: None,
                error: Some(e),
            }
        }
    };

    let latest_tag = data
        .get("tag_name")
        .or_else(|| data.get("name"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let release_url = data
        .get("html_url")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let notes = data
        .get("body")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());

    let (installer_name, installer_url) = select_installer_asset(&data)
        .map(|(name, url)| (Some(name), Some(url)))
        .unwrap_or((None, None));

    let update_available =
        parse_semver(&latest_tag) > parse_semver(&current_version);

    UpdateInfo {
        update_available,
        latest_version: latest_tag,
        current_version,
        release_url,
        installer_name,
        installer_url,
        notes,
        error: None,
    }
}

#[tauri::command]
pub fn download_and_install_update(current_version: String) -> Result<(), String> {
    let info = check_for_updates(current_version);
    if let Some(error) = info.error {
        return Err(error);
    }
    if !info.update_available {
        return Err("Already up to date".to_string());
    }

    let installer_url = info
        .installer_url
        .ok_or_else(|| "No supported Windows installer asset was found in the latest GitHub release".to_string())?;
    let installer_name = info
        .installer_name
        .unwrap_or_else(|| "manaka-mod-station-update.msi".to_string());

    let response = ureq::builder()
        .timeout(std::time::Duration::from_secs(300))
        .build()
        .get(&installer_url)
        .set("User-Agent", "ManakaModStation-Updater/1.1")
        .call()
        .map_err(|e| e.to_string())?;

    let update_dir = std::env::temp_dir().join("ManakaModStation").join("updates");
    fs::create_dir_all(&update_dir).map_err(|e| e.to_string())?;

    let installer_path = update_dir.join(&installer_name);
    let mut reader = response.into_reader();
    let mut file = fs::File::create(&installer_path).map_err(|e| e.to_string())?;
    io::copy(&mut reader, &mut file).map_err(|e| e.to_string())?;

    let lower = installer_name.to_lowercase();
    if lower.ends_with(".msi") {
        Command::new("msiexec")
            .args(["/i"])
            .arg(&installer_path)
            .arg("/passive")
            .spawn()
            .map_err(|e| e.to_string())?;
    } else if lower.ends_with(".exe") {
        Command::new(&installer_path)
            .arg("/S")
            .spawn()
            .map_err(|e| e.to_string())?;
    } else {
        return Err("Unsupported installer type".to_string());
    }

    Ok(())
}
