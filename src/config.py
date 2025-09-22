from __future__ import annotations

from pathlib import Path
import os


# 将 database 放到用户 AppData 目录，避免权限问题
_appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
APP_DIR = Path(_appdata) / "PracticeApp"
DATABASE_DIR = APP_DIR / "database"
CUSTOM_MISSIONS_DIR = DATABASE_DIR / "CustomMissions"
SETTINGS_DIR = DATABASE_DIR / "Settings"

# 设置文件
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
MODS_STATE_FILE = SETTINGS_DIR / "mods_state.json"


def ensure_directories() -> None:
    """确保关键目录存在。"""
    for d in (APP_DIR, DATABASE_DIR, CUSTOM_MISSIONS_DIR, SETTINGS_DIR):
        d.mkdir(parents=True, exist_ok=True)
