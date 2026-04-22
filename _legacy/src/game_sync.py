from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Iterable, Tuple

from .config import CUSTOM_MISSIONS_DIR


def compute_sha256(p: Path, buf_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        while True:
            b = f.read(buf_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def get_game_custom_dir(game_dir: str | Path) -> Path:
    base = Path(game_dir) if isinstance(game_dir, (str, Path)) else Path(str(game_dir))
    return base / 'CustomMissions'


def ensure_game_custom_dir(game_dir: str | Path) -> Path:
    d = get_game_custom_dir(game_dir)
    d.mkdir(parents=True, exist_ok=True)
    return d


def iter_workspace_jsons() -> Iterable[Path]:
    yield from sorted(CUSTOM_MISSIONS_DIR.glob('*.json'))


def iter_game_jsons(game_dir: str | Path) -> Iterable[Path]:
    d = get_game_custom_dir(game_dir)
    if not d.exists():
        return []
    return sorted(d.glob('*.json'))


def sync_game_to_workspace(game_dir: str | Path) -> Tuple[int, int, int]:
    """Copy JSONs from game CustomMissions to workspace.
    If same name exists: compare sha256; if same -> skip; if diff -> rename as name.N.json
    Returns: (copied, skipped_same, renamed)
    """
    copied = skipped = renamed = 0
    gdir = get_game_custom_dir(game_dir)
    if not gdir.exists():
        return (0, 0, 0)
    for src in iter_game_jsons(game_dir):
        dst = CUSTOM_MISSIONS_DIR / src.name
        if not dst.exists():
            shutil.copy2(src, dst)
            copied += 1
        else:
            try:
                if compute_sha256(src) == compute_sha256(dst):
                    skipped += 1
                else:
                    # rename as filename.N.json
                    stem = dst.stem
                    suffix = dst.suffix
                    n = 1
                    while True:
                        cand = CUSTOM_MISSIONS_DIR / f"{stem}.{n}{suffix}"
                        if not cand.exists():
                            shutil.copy2(src, cand)
                            renamed += 1
                            break
                        n += 1
            except Exception:
                # best effort fallback: copy with .copy suffix
                cand = CUSTOM_MISSIONS_DIR / f"{dst.stem}.copy{dst.suffix}"
                shutil.copy2(src, cand)
                renamed += 1
    return (copied, skipped, renamed)


def is_enabled_in_game(filename: str, game_dir: str | Path) -> bool:
    return (get_game_custom_dir(game_dir) / filename).exists()


def enable_mod(filename: str, game_dir: str | Path) -> bool:
    src = CUSTOM_MISSIONS_DIR / filename
    if not src.exists():
        return False
    try:
        dst_dir = ensure_game_custom_dir(game_dir)
        shutil.copy2(src, dst_dir / filename)
        return True
    except Exception:
        return False


def disable_mod(filename: str, game_dir: str | Path) -> bool:
    try:
        target = get_game_custom_dir(game_dir) / filename
        if target.exists():
            target.unlink()
        return True
    except Exception:
        return False
