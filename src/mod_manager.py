from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .config import CUSTOM_MISSIONS_DIR, MODS_STATE_FILE, ensure_directories


@dataclass
class ModInfo:
    name: str  # display name (prefer title in JSON)
    path: Path
    enabled: bool = True
    version: Optional[str] = None
    author: Optional[str] = None
    description: Optional[str] = None
    descriptions: list[str] = field(default_factory=list)
    stage: Optional[str] = None
    is_warp: bool = False


def _load_state() -> Dict[str, bool]:
    ensure_directories()
    if not MODS_STATE_FILE.exists():
        MODS_STATE_FILE.write_text("{}", encoding="utf-8")
        return {}
    try:
        return json.loads(MODS_STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_state(state: Dict[str, bool]) -> None:
    ensure_directories()
    MODS_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_metadata(p: Path) -> dict:
    """Read mission JSON and extract metadata safely.
    Returns dict with keys: title, version, author, descriptions(list[str]).
    """
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"title": p.stem, "version": None, "author": None, "descriptions": []}

    title = obj.get("title") or p.stem
    version = obj.get("version") or obj.get("ver")
    author = obj.get("author") or obj.get("by")

    # Collect all descriptions under checkpoints[].condition/travelcondition.description
    descs: list[str] = []
    cps = obj.get("checkpoints")
    if isinstance(cps, list):
        for cp in cps:
            if not isinstance(cp, dict):
                continue
            for key in ("condition", "travelcondition"):
                blk = cp.get(key)
                if isinstance(blk, dict):
                    d = blk.get("description")
                    if isinstance(d, str) and d.strip():
                        descs.append(d.strip())

    # 提取第一个 zone 的 stage
    stage = None
    zones = obj.get("zones") if isinstance(obj, dict) else None
    if isinstance(zones, list) and zones:
        z0 = zones[0]
        if isinstance(z0, dict):
            st = z0.get("stage")
            if isinstance(st, str) and st.strip():
                stage = st.strip()

    # 若 JSON 未提供 stage，尝试由标题/文件名推断
    if not stage:
        def infer_stage_from_name(title_text: str, stem_text: str) -> Optional[str]:
            text = f"{title_text} {stem_text}".lower()
            # 统一分隔符
            text = text.replace('_', ' ').replace('-', ' ')
            # 英文关键词映射
            rules: list[tuple[list[str], str]] = [
                (["park"], "Park"),
                (["mall"], "Mall"),
                (["shop", "store"], "Shop"),
                (["res ", "res_", "res-", "residential", "resid", "resd"], "Residential"),
                (["apart", "apartment"], "Apartment"),
                (["dtown", "downtown"], "Downtown"),
                (["convenience", "convernience", "conv"], "Convenience"),
                (["bridge"], "Bridge"),
                (["toilet", "restroom", "wc"], "Toilet"),
                (["elevator", "lift"], "Elevator"),
                (["alley", "alleyway"], "Alley"),
                (["clothing"], "Clothing Store"),
                (["ch shop", "clothes shop"], "Clothing Shop"),
            ]
            # 中文关键词映射
            cn_rules: list[tuple[list[str], str]] = [
                (["公园"], "Park"),
                (["商场"], "Mall"),
                (["商店", "店"], "Shop"),
                (["住宅", "小区"], "Residential"),
                (["公寓"], "Apartment"),
                (["市中心"], "Downtown"),
                (["便利店"], "Convenience"),
                (["大桥", "桥"], "Bridge"),
                (["厕所", "洗手间", "卫生间"], "Toilet"),
                (["电梯"], "Elevator"),
                (["小巷", "巷"], "Alley"),
                (["服装", "衣服"], "Clothing Store"),
            ]
            for keys, label in rules:
                if any(k in text for k in keys):
                    return label
            for keys, label in cn_rules:
                if any(k in text for k in keys):
                    return label
            # 特例：文件以数字+空格+标识开头，如 "00 ParkMas.json"
            parts = text.split()
            if len(parts) >= 2 and parts[0].isdigit():
                # 第二个单词可能是位置名
                cand = parts[1]
                for keys, label in rules:
                    if any(cand.startswith(k.strip()) for k in keys if k.strip()):
                        return label
            return None

        title_text = str(title or "")
        stem_text = p.stem
        stage = infer_stage_from_name(title_text, stem_text)

    # 标记是否 warp 任务（标题含 warp 或任意字符串字段包含 "warp"）
    is_warp = False
    try:
        t = (title or "").lower()
        if "warp" in t:
            is_warp = True
        else:
            def any_contains_warp(x) -> bool:
                if isinstance(x, str):
                    return "warp" in x.lower()
                if isinstance(x, list):
                    return any(any_contains_warp(i) for i in x)
                if isinstance(x, dict):
                    return any(any_contains_warp(v) for v in x.values())
                return False
            is_warp = any_contains_warp(obj)
    except Exception:
        is_warp = False

    return {"title": title, "version": version, "author": author, "descriptions": descs, "stage": stage, "is_warp": is_warp}


def scan_mods() -> List[ModInfo]:
    """扫描 CustomMissions 目录下的 .json 作为 Mod。
    读取 mods_state.json 中的启用状态。
    """
    ensure_directories()
    state = _load_state()
    mods: List[ModInfo] = []
    for p in CUSTOM_MISSIONS_DIR.glob("*.json"):
        enabled = bool(state.get(p.name, True))
        meta = _parse_metadata(p)
        mods.append(
            ModInfo(
                name=str(meta.get("title") or p.stem),
                path=p,
                enabled=enabled,
                version=meta.get("version"),
                author=meta.get("author"),
                descriptions=list(meta.get("descriptions") or []),
                stage=meta.get("stage"),
                is_warp=bool(meta.get("is_warp", False)),
            )
        )
    return mods


def set_mod_enabled(filename: str, enabled: bool) -> None:
    state = _load_state()
    state[filename] = bool(enabled)
    _save_state(state)


def delete_mod(filename: str) -> bool:
    target = CUSTOM_MISSIONS_DIR / filename
    if target.exists() and target.is_file():
        target.unlink()
        # 同步状态
        state = _load_state()
        state.pop(filename, None)
        _save_state(state)
        return True
    return False
