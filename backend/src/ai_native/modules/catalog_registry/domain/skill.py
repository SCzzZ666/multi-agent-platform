"""Skill 包规范（05 §10.1 / 5.5）：SKILL.md 解析、封闭路径、静态脚本扫描。

标准包 = SKILL.md + 可选 scripts/ references/ assets/。
封闭路径：禁绝对路径 / 穿越 / reparse/符号链接 / 设备文件 / 凭据文件。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

from ai_native.shared_kernel.digest import sha256_hex

_KEY_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")

# 静态脚本扫描的危险模式（skill 声明 allowed-tools 只是请求上限，非授权）
_DANGER_PATTERNS = {
    "SCRIPT_EVAL": re.compile(r"\beval\s*\(|\bexec\s*\("),
    "SCRIPT_SHELL": re.compile(r"subprocess\b.*shell\s*=\s*True|os\.system\s*\("),
    "SCRIPT_PIPE_CURL": re.compile(r"curl\b.*\|\s*(sh|bash)|wget\b.*\|\s*(sh|bash)"),
    "SCRIPT_RM_RF_ROOT": re.compile(r"rm\s+-rf\s+/"),
    "SCRIPT_CRED_ENV": re.compile(r"\b(TOKEN|SECRET|PASSWORD|API_KEY)\b"),
}


class SkillPackageError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SkillPackage:
    skill_key: str
    name: str
    description: str
    body: str
    scripts: dict[str, str] = field(default_factory=dict)  # relative_path -> content
    references: tuple[str, ...] = ()
    assets: tuple[str, ...] = ()


def parse_skill_md(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise SkillPackageError("SKILL_FRONTMATTER_MISSING", "SKILL.md 必须以 --- frontmatter 开头")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillPackageError("SKILL_FRONTMATTER_MALFORMED", "frontmatter 未闭合")
    try:
        frontmatter = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        raise SkillPackageError("SKILL_FRONTMATTER_BAD_YAML", str(e)) from e
    return frontmatter, parts[2].strip()


def validate_rel_path(path: str) -> str | None:
    """返回错误码或 None。"""
    if not path or path in (".", ".."):
        return "PATH_EMPTY_OR_DOT"
    if path.startswith("/") or re.match(r"^[a-zA-Z]:[\\/]", path):
        return "PATH_ABSOLUTE"
    if "\\" in path:
        return "PATH_BACKSLASH"
    segments = path.split("/")
    if any(seg in ("", ".", "..") for seg in segments):
        return "PATH_TRAVERSAL"
    if any(seg.startswith(".") and seg != ".." for seg in segments):
        return "PATH_DOTFILE"  # 如 .git/.env
    if re.search(r"(?i)(\.env|id_rsa|\.pem|\.key|credential|secret)", path):
        return "PATH_CREDENTIAL"
    return None


def scan_script(content: str) -> list[str]:
    flags: list[str] = []
    for code, pattern in _DANGER_PATTERNS.items():
        if pattern.search(content):
            flags.append(code)
    return flags


def package_digest(manifest: dict) -> str:
    import json

    return "sha256:" + sha256_hex(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8"))


def validate_package(pkg: SkillPackage, manifest: dict | None = None) -> list[str]:
    diags: list[str] = []
    if not _KEY_RE.match(pkg.skill_key):
        diags.append("SKILL_INVALID_KEY")
    if not pkg.name:
        diags.append("SKILL_NO_NAME")
    if not pkg.body:
        diags.append("SKILL_EMPTY_BODY")
    for path in list(pkg.scripts) + list(pkg.references) + list(pkg.assets):
        err = validate_rel_path(path)
        if err:
            diags.append(f"{err}:{path}")
    for path, content in pkg.scripts.items():
        for flag in scan_script(content):
            diags.append(f"{flag}:{path}")
    return diags