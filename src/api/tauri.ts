import { invoke } from "@tauri-apps/api/core";

export interface ModInfo {
  filename: string;
  name: string;
  enabled: boolean;
  version: string | null;
  author: string | null;
  descriptions: string[];
  stage: string | null;
  is_warp: boolean;
  start_condition: string | null;
}

export interface Settings {
  language: string;
  theme: string;
  gameDir: string | null;
  modLibraryDir: string | null;
  rememberLastPage: boolean;
  rememberLastSelectedMod: boolean;
  rememberCollapsedGroups: boolean;
  confirmDelete: boolean;
  encoding: string;
  lastUpdateCheck: string | null;
  startupUpdateCheck: boolean;
}

export interface SyncResult {
  copied: number;
  skipped: number;
  renamed: number;
  errors: string[];
}

export interface ValidationIssue {
  kind: string;
  message: string;
  line: number | null;
  column: number | null;
}

export interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
}

export interface ExplorerEntry {
  name: string;
  path: string;
  isDirectory: boolean;
}

export interface UpdateInfo {
  update_available: boolean;
  latest_version: string;
  current_version: string;
  release_url: string | null;
  error: string | null;
}

// Mod Manager
export const scanMods = () => invoke<ModInfo[]>("scan_mods");
export const setModEnabled = (filename: string, enabled: boolean) =>
  invoke<void>("set_mod_enabled", { filename, enabled });
export const setAllModsEnabled = (enabled: boolean) =>
  invoke<void>("set_all_mods_enabled", { enabled });
export const deleteMod = (filename: string) =>
  invoke<void>("delete_mod", { filename });
export const readModFile = (filename: string) =>
  invoke<string>("read_mod_file", { filename });
export const writeModFile = (filename: string, content: string) =>
  invoke<void>("write_mod_file", { filename, content });
export const listDirectory = (path: string) =>
  invoke<ExplorerEntry[]>("list_directory", { path });
export const readTextFileAtPath = (path: string) =>
  invoke<string>("read_text_file_absolute", { path });
export const writeTextFileAtPath = (path: string, content: string) =>
  invoke<void>("write_text_file_absolute", { path, content });

// Game Sync
export const syncGameToWorkspace = (gameDir: string) =>
  invoke<SyncResult>("sync_game_to_workspace", { gameDir });
export const enableModInGame = (filename: string, gameDir: string) =>
  invoke<void>("enable_mod_in_game", { filename, gameDir });
export const disableModInGame = (filename: string, gameDir: string) =>
  invoke<void>("disable_mod_in_game", { filename, gameDir });
export const openDirectory = (path: string) =>
  invoke<void>("open_directory", { path });

// Settings
export const loadSettings = () => invoke<Settings>("load_settings");
export const saveSettings = (settings: Settings) =>
  invoke<void>("save_settings", { settings });
export const resetSettings = () => invoke<Settings>("reset_settings");
export const getAppDataPath = () => invoke<string>("get_app_data_path");
export const getModLibraryPath = () => invoke<string>("get_mod_library_path");
export const getSystemAccentColor = () => invoke<string>("get_system_accent_color");
export const getSystemDarkMode = () => invoke<boolean>("get_system_dark_mode");

// Validator
export const validateMissionJson = (content: string) =>
  invoke<ValidationResult>("validate_mission_json", { content });
export const formatJson = (content: string) =>
  invoke<string>("format_json", { content });

// Updater
export const checkForUpdates = (currentVersion: string) =>
  invoke<UpdateInfo>("check_for_updates", { currentVersion });
