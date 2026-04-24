mod commands;

use commands::{
    config::{
        get_app_data_path, get_mod_library_path, get_system_accent_color, get_system_dark_mode,
    },
    game_sync::{
        disable_mod_in_game, enable_mod_in_game, is_mod_enabled_in_game, open_directory,
        sync_game_to_workspace,
    },
    mod_manager::{
        delete_mod, list_directory, read_mod_file, read_text_file_absolute, scan_mods,
        set_all_mods_enabled, set_mod_enabled, write_mod_file, write_text_file_absolute,
    },
    settings::{load_settings, reset_settings, save_settings},
    updater::{check_for_updates, download_and_install_update},
    validator::{format_json, validate_mission_json},
};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    commands::config::ensure_dirs();

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            // Enable Mica on Windows 11
            #[cfg(target_os = "windows")]
            {
                use tauri::Manager;
                let window = app.get_webview_window("main").unwrap();
                let _ = window_vibrancy::apply_mica(&window, None);
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            // mod manager
            scan_mods,
            set_mod_enabled,
            set_all_mods_enabled,
            delete_mod,
            read_mod_file,
            write_mod_file,
            list_directory,
            read_text_file_absolute,
            write_text_file_absolute,
            // game sync
            sync_game_to_workspace,
            enable_mod_in_game,
            disable_mod_in_game,
            is_mod_enabled_in_game,
            open_directory,
            // settings
            load_settings,
            save_settings,
            reset_settings,
            get_app_data_path,
            get_mod_library_path,
            get_system_accent_color,
            get_system_dark_mode,
            // validator
            validate_mission_json,
            format_json,
            // updater
            check_for_updates,
            download_and_install_update,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Manaka MOD Station");
}
