from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ValidationIssue:
    kind: str  # "syntax" | "schema"
    message: str
    line: Optional[int] = None
    column: Optional[int] = None


def _json_syntax_check(text: str) -> Tuple[list[ValidationIssue], Optional[Any]]:
    try:
        data = json.loads(text)
        return ([], data)
    except json.JSONDecodeError as e:
        return ([ValidationIssue("syntax", e.msg, e.lineno, e.colno)], None)


def _collect_ids(items: Any, key: str) -> set[str]:
    ids: set[str] = set()
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                v = it.get(key)
                if isinstance(v, str):
                    ids.add(v)
    return ids


def validate_mission_structure(obj: Any) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    if not isinstance(obj, dict):
        return [ValidationIssue("schema", "顶层必须是对象")]

    title = obj.get("title")
    if not isinstance(title, str) or not title.strip():
        issues.append(ValidationIssue("schema", "缺少必填字段 title 或为空"))

    zones = obj.get("zones")
    if not isinstance(zones, list) or not zones:
        issues.append(ValidationIssue("schema", "zones 至少包含 1 个元素"))
    else:
        zone_ids = _collect_ids(zones, "id")
        if len(zone_ids) != sum(1 for z in zones if isinstance(z, dict) and isinstance(z.get("id"), str)):
            issues.append(ValidationIssue("schema", "zones.id 必须全局唯一且为字符串"))
        # 基础 area 校验
        for z in zones:
            if not isinstance(z, dict):
                continue
            areas = z.get("areas")
            if not isinstance(areas, list) or not areas:
                issues.append(ValidationIssue("schema", f"zone '{z.get('id','?')}' 缺少 areas 或为空"))
            else:
                for a in areas:
                    if not isinstance(a, dict):
                        continue
                    if not isinstance(a.get("stage"), str):
                        issues.append(ValidationIssue("schema", f"zone '{z.get('id','?')}' 的 area 缺少 stage"))
                    r = a.get("r")
                    if not isinstance(r, (int, float)) or r <= 0:
                        issues.append(ValidationIssue("schema", f"zone '{z.get('id','?')}' 的 area.r 必须 > 0"))

    subconditions = obj.get("subconditions")
    if isinstance(subconditions, list):
        sub_ids = _collect_ids(subconditions, "id")
        if len(sub_ids) != sum(1 for s in subconditions if isinstance(s, dict) and isinstance(s.get("id"), str)):
            issues.append(ValidationIssue("schema", "subconditions.id 必须全局唯一"))

    checkpoints = obj.get("checkpoints")
    if not isinstance(checkpoints, list) or not checkpoints:
        issues.append(ValidationIssue("schema", "checkpoints 至少包含 1 个元素"))
    else:
        cp_ids = _collect_ids(checkpoints, "id")
        # 唯一性（可选 id）
        if len(cp_ids) != sum(1 for c in checkpoints if isinstance(c, dict) and isinstance(c.get("id"), str)):
            issues.append(ValidationIssue("schema", "checkpoints.id 若存在需唯一"))

        # zone 引用合法性
        zone_ids = _collect_ids(zones or [], "id")
        for c in checkpoints:
            if not isinstance(c, dict):
                continue
            z = c.get("zone")
            if not isinstance(z, str) or z not in zone_ids:
                issues.append(ValidationIssue("schema", f"checkpoint '{c.get('id','?')}' 的 zone 引用不存在"))
            nxt = c.get("nextcheckpoint")
            if isinstance(nxt, dict):
                st = nxt.get("selectortype")
                if st == "SpecificId":
                    cid = nxt.get("id")
                    if not isinstance(cid, str) or (cp_ids and cid not in cp_ids):
                        issues.append(ValidationIssue("schema", f"nextcheckpoint.id '{cid}' 不存在于 checkpoints.id"))
                elif st == "RandomId":
                    ids = nxt.get("ids")
                    if not isinstance(ids, list) or not ids or any(i not in cp_ids for i in ids if isinstance(i, str)):
                        issues.append(ValidationIssue("schema", "nextcheckpoint.ids 非法或包含不存在的 id"))

    return issues


def validate_text(text: str) -> List[ValidationIssue]:
    syntax_issues, data = _json_syntax_check(text)
    if data is None:
        return syntax_issues
    issues = validate_mission_structure(data)
    return syntax_issues + issues
