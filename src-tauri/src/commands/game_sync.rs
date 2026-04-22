use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

use super::mod_manager::compute_sha256;
use super::config::custom_missions_dir;

#[derive(Debug, Serialize, Deserialize)]
pub struct SyncResult {
    pub copied: u32,
    pub skipped: u32,
    pub renamed: u32,
    pub errors: Vec<String>,
}

fn game_custom_dir(game_dir: &str) -> PathBuf {
    PathBuf::from(game_dir).join("CustomMissions")
}

fn sync_dirs(src_dir: &Path, dst_dir: &Path) -> SyncResult {
    let _ = fs::create_dir_all(dst_dir);

    let mut result = SyncResult {
        copied: 0,
        skipped: 0,
        renamed: 0,
        errors: vec![],
    };

    if !src_dir.exists() {
        result.errors.push(format!("游戏目录不存在: {}", src_dir.display()));
        return result;
    }

    let entries = match fs::read_dir(src_dir) {
        Ok(rd) => rd,
        Err(e) => {
            result.errors.push(e.to_string());
            return result;
        }
    };

    for entry in entries.filter_map(|e| e.ok()) {
        let src = entry.path();
        if src.extension().map(|e| e != "json").unwrap_or(true) {
            continue;
        }
        let fname = src.file_name().unwrap_or_default().to_string_lossy().to_string();
        let dst = dst_dir.join(&fname);

        if !dst.exists() {
            match fs::copy(&src, &dst) {
                Ok(_) => result.copied += 1,
                Err(e) => result.errors.push(format!("{}: {}", fname, e)),
            }
        } else {
            let src_hash = compute_sha256(&src);
            let dst_hash = compute_sha256(&dst);
            match (src_hash, dst_hash) {
                (Ok(sh), Ok(dh)) if sh == dh => {
                    result.skipped += 1;
                }
                _ => {
                    let stem = dst.file_stem().unwrap_or_default().to_string_lossy().to_string();
                    let mut n = 1u32;
                    loop {
                        let cand = dst_dir.join(format!("{}.{}.json", stem, n));
                        if !cand.exists() {
                            match fs::copy(&src, &cand) {
                                Ok(_) => result.renamed += 1,
                                Err(e) => result.errors.push(format!("{}: {}", fname, e)),
                            }
                            break;
                        }
                        n += 1;
                        if n > 999 {
                            result.errors.push(format!("{}: too many conflicts", fname));
                            break;
                        }
                    }
                }
            }
        }
    }

    result
}

fn copy_mod_to_game(filename: &str, src_dir: &Path, dst_dir: &Path) -> Result<(), String> {
    let src = src_dir.join(filename);
    if !src.exists() {
        return Err(format!("Mod 文件不存在: {}", filename));
    }
    fs::create_dir_all(dst_dir).map_err(|e| e.to_string())?;
    fs::copy(&src, dst_dir.join(filename))
        .map(|_| ())
        .map_err(|e| e.to_string())
}

fn remove_mod_from_game(filename: &str, dst_dir: &Path) -> Result<(), String> {
    let target = dst_dir.join(filename);
    if target.exists() {
        fs::remove_file(&target).map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn mod_exists_in_game(filename: &str, dst_dir: &Path) -> bool {
    dst_dir.join(filename).exists()
}

#[tauri::command]
pub fn sync_game_to_workspace(game_dir: String) -> SyncResult {
    let src_dir = game_custom_dir(&game_dir);
    let dst_dir = custom_missions_dir();
    sync_dirs(&src_dir, &dst_dir)
}

#[tauri::command]
pub fn enable_mod_in_game(filename: String, game_dir: String) -> Result<(), String> {
    copy_mod_to_game(&filename, &custom_missions_dir(), &game_custom_dir(&game_dir))
}

#[tauri::command]
pub fn disable_mod_in_game(filename: String, game_dir: String) -> Result<(), String> {
    remove_mod_from_game(&filename, &game_custom_dir(&game_dir))
}

#[tauri::command]
pub fn is_mod_enabled_in_game(filename: String, game_dir: String) -> bool {
    mod_exists_in_game(&filename, &game_custom_dir(&game_dir))
}

#[tauri::command]
pub fn open_directory(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("explorer")
            .arg(&path)
            .spawn()
            .map(|_| ())
            .map_err(|e| e.to_string())
    }
    #[cfg(not(target_os = "windows"))]
    {
        Err("Not supported on this platform".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn temp_dir(name: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let dir = std::env::temp_dir().join(format!(
            "manaka-mod-station-{}-{}-{}",
            name,
            std::process::id(),
            nonce
        ));
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn sync_dirs_copies_skips_and_renames_like_legacy_behavior() {
        let src_dir = temp_dir("sync-src");
        let dst_dir = temp_dir("sync-dst");

        fs::write(src_dir.join("new.json"), "{\"value\":1}").unwrap();
        fs::write(src_dir.join("same.json"), "{\"value\":2}").unwrap();
        fs::write(src_dir.join("conflict.json"), "{\"value\":3}").unwrap();

        fs::write(dst_dir.join("same.json"), "{\"value\":2}").unwrap();
        fs::write(dst_dir.join("conflict.json"), "{\"value\":999}").unwrap();

        let result = sync_dirs(&src_dir, &dst_dir);

        assert_eq!(result.copied, 1);
        assert_eq!(result.skipped, 1);
        assert_eq!(result.renamed, 1);
        assert!(result.errors.is_empty());
        assert!(dst_dir.join("new.json").exists());
        assert!(dst_dir.join("conflict.1.json").exists());

        let _ = fs::remove_dir_all(src_dir);
        let _ = fs::remove_dir_all(dst_dir);
    }

    #[test]
    fn enable_disable_and_status_work_without_real_game_files() {
        let workspace_dir = temp_dir("workspace");
        let game_root = temp_dir("game-root");
        let game_custom = game_root.join("CustomMissions");

        fs::write(workspace_dir.join("demo.json"), "{\"title\":\"demo\"}").unwrap();

        copy_mod_to_game("demo.json", &workspace_dir, &game_custom).unwrap();
        assert!(mod_exists_in_game("demo.json", &game_custom));

        remove_mod_from_game("demo.json", &game_custom).unwrap();
        assert!(!mod_exists_in_game("demo.json", &game_custom));

        let _ = fs::remove_dir_all(workspace_dir);
        let _ = fs::remove_dir_all(game_root);
    }
}
