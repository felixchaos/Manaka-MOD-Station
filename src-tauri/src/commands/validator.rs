use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct ValidationIssue {
    pub kind: String,
    pub message: String,
    pub line: Option<u32>,
    pub column: Option<u32>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ValidationResult {
    pub valid: bool,
    pub issues: Vec<ValidationIssue>,
}

#[tauri::command]
pub fn validate_mission_json(content: String) -> ValidationResult {
    // Step 1: Syntax check
    let obj: serde_json::Value = match serde_json::from_str(&content) {
        Ok(v) => v,
        Err(e) => {
            return ValidationResult {
                valid: false,
                issues: vec![ValidationIssue {
                    kind: "syntax".to_string(),
                    message: e.to_string(),
                    line: Some(e.line() as u32),
                    column: Some(e.column() as u32),
                }],
            };
        }
    };

    let mut issues = vec![];

    // Step 2: Structure validation
    let obj = match obj.as_object() {
        Some(o) => o,
        None => {
            return ValidationResult {
                valid: false,
                issues: vec![ValidationIssue {
                    kind: "schema".to_string(),
                    message: "顶层必须是对象".to_string(),
                    line: None,
                    column: None,
                }],
            };
        }
    };

    // title required
    match obj.get("title").and_then(|v| v.as_str()) {
        Some(t) if !t.trim().is_empty() => {}
        _ => issues.push(ValidationIssue {
            kind: "schema".to_string(),
            message: "缺少必填字段 title 或为空".to_string(),
            line: None,
            column: None,
        }),
    }

    // zones required
    match obj.get("zones").and_then(|v| v.as_array()) {
        Some(zones) if !zones.is_empty() => {
            let mut zone_ids = std::collections::HashSet::new();
            for z in zones {
                if let Some(id) = z.get("id").and_then(|v| v.as_str()) {
                    if !zone_ids.insert(id.to_string()) {
                        issues.push(ValidationIssue {
                            kind: "schema".to_string(),
                            message: format!("zone id '{}' 重复", id),
                            line: None,
                            column: None,
                        });
                    }
                }
                if let Some(areas) = z.get("areas").and_then(|v| v.as_array()) {
                    for a in areas {
                        if a.get("stage").and_then(|v| v.as_str()).is_none() {
                            issues.push(ValidationIssue {
                                kind: "schema".to_string(),
                                message: format!(
                                    "zone '{}' 的 area 缺少 stage",
                                    z.get("id").and_then(|v| v.as_str()).unwrap_or("?")
                                ),
                                line: None,
                                column: None,
                            });
                        }
                        match a.get("r").and_then(|v| v.as_f64()) {
                            Some(r) if r > 0.0 => {}
                            _ => issues.push(ValidationIssue {
                                kind: "schema".to_string(),
                                message: format!(
                                    "zone '{}' 的 area.r 必须 > 0",
                                    z.get("id").and_then(|v| v.as_str()).unwrap_or("?")
                                ),
                                line: None,
                                column: None,
                            }),
                        }
                    }
                } else {
                    issues.push(ValidationIssue {
                        kind: "schema".to_string(),
                        message: format!(
                            "zone '{}' 缺少 areas",
                            z.get("id").and_then(|v| v.as_str()).unwrap_or("?")
                        ),
                        line: None,
                        column: None,
                    });
                }
            }
        }
        _ => issues.push(ValidationIssue {
            kind: "schema".to_string(),
            message: "zones 至少包含 1 个元素".to_string(),
            line: None,
            column: None,
        }),
    }

    // checkpoints required
    match obj.get("checkpoints").and_then(|v| v.as_array()) {
        Some(cps) if !cps.is_empty() => {}
        _ => issues.push(ValidationIssue {
            kind: "schema".to_string(),
            message: "checkpoints 至少包含 1 个元素".to_string(),
            line: None,
            column: None,
        }),
    }

    ValidationResult {
        valid: issues.is_empty(),
        issues,
    }
}

#[tauri::command]
pub fn format_json(content: String) -> Result<String, String> {
    let val: serde_json::Value = serde_json::from_str(&content).map_err(|e| e.to_string())?;
    serde_json::to_string_pretty(&val).map_err(|e| e.to_string())
}
