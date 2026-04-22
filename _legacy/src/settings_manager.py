from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from jsonschema import validate, ValidationError

from .config import SETTINGS_FILE, ensure_directories


DEFAULT_SETTINGS: Dict[str, Any] = {
    "language": "zh-CN",
    "theme": "light",
    "gameDir": None,  # 游戏目录（字符串或 None）
    "encoding": "UTF-8",
    "lastUpdateCheck": None,
}

SETTINGS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "language": {"type": "string"},
        "theme": {"type": "string", "enum": ["light", "dark", "system"]},
        "gameDir": {"type": ["string", "null"]},
        "encoding": {"type": "string"},
        "lastUpdateCheck": {"type": ["string", "null"]},
    },
    "additionalProperties": True,
}


def load_settings() -> Dict[str, Any]:
    ensure_directories()
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise json.JSONDecodeError("settings must be object", "{}", 0)
    except json.JSONDecodeError:
        # 文件损坏：写入默认
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    # 按字段容错合并，避免因单字段非法导致整体重置（例如 theme 值异常）
    result: Dict[str, Any] = DEFAULT_SETTINGS.copy()
    # 已知字段
    if isinstance(raw.get("language"), str):
        result["language"] = raw["language"]
    theme = raw.get("theme")
    if theme in {"light", "dark", "system"}:
        result["theme"] = theme
    gd = raw.get("gameDir")
    if gd is None or isinstance(gd, str):
        result["gameDir"] = gd
    enc = raw.get("encoding")
    if isinstance(enc, str):
        result["encoding"] = enc
    luc = raw.get("lastUpdateCheck")
    if luc is None or isinstance(luc, str):
        result["lastUpdateCheck"] = luc
    # 其他未知字段，尽量保留
    for k, v in raw.items():
        if k not in result:
            result[k] = v
    # 最终再做一次宽松校验（不抛出，仅保证已知字段合法）
    try:
        validate(instance=result, schema=SETTINGS_SCHEMA)
    except ValidationError:
        # 忽略校验错误（additionalProperties 或个别字段），已做字段级容错
        pass
    # 保存规范化后的设置（仅在有差异时也可以保存，这里统一保存一次）
    try:
        save_settings(result)
    except Exception:
        pass
    return result


def save_settings(data: Dict[str, Any]) -> None:
    ensure_directories()
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
