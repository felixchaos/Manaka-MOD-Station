"""
Minimal update checker using GitHub Releases (or any service exposing a releases/latest JSON)
Contract:
- check_for_updates(remote_api_url: str, current_version: str) -> dict
  returns { "update_available": bool, "latest_version": str, "assets": [{"name":..., "browser_download_url":...}], "message": ... }
- download_asset(url: str, dest: Path) -> Path

This module is small, synchronous, and uses only the standard library.
"""
from __future__ import annotations

import json
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ReleaseAsset:
    name: str
    url: str


def _fetch_json(url: str, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "PracticeApp-UpdateChecker/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return json.loads(raw.decode("utf-8"))


def _parse_semver(v: Optional[str]) -> List[int]:
    if not v:
        return [0, 0, 0]
    # strip leading v
    if v.startswith("v") or v.startswith("V"):
        v = v[1:]
    parts = v.split(".")
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except Exception:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return nums[:3]


def _is_newer(latest: str, current: str) -> bool:
    return _parse_semver(latest) > _parse_semver(current)


def check_for_updates_github(repo: str, current_version: str, timeout: int = 10) -> dict:
    """
    Check GitHub releases for updates.
    repo: "owner/repo"
    returns: {update_available, latest_version, assets}
    """
    api = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        data = _fetch_json(api, timeout=timeout)
    except Exception as e:
        return {"update_available": False, "latest_version": current_version, "assets": [], "error": str(e)}

    latest_tag = data.get("tag_name") or data.get("name")
    assets = []
    for a in data.get("assets", []):
        assets.append(ReleaseAsset(name=a.get("name"), url=a.get("browser_download_url")))

    update_available = _is_newer(latest_tag, current_version)
    return {"update_available": update_available, "latest_version": latest_tag, "assets": assets}


def download_asset(url: str, dest: Path, timeout: int = 30) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "PracticeApp-UpdateChecker/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as out:
        shutil.copyfileobj(resp, out)
    tmp.replace(dest)
    return dest


if __name__ == "__main__":
    # Simple manual test
    import sys

    if len(sys.argv) < 3:
        print("Usage: update_checker.py owner/repo current_version")
        raise SystemExit(2)
    repo = sys.argv[1]
    cur = sys.argv[2]
    res = check_for_updates_github(repo, cur)
    print(res)
