"""第一支架构守护测试：MAF 隔离 + domain 禁依赖框架。

对应 CODEBASE-BL-2026-09-15-01：
- D10-07 只有 runtime/maf 适配包可以直接导入 MAF；
- 6.2 依赖方向：domain 不得导入 FastAPI、Pydantic API DTO、SQLAlchemy、psycopg、MAF 或供应商 SDK。

对 backend/src/ai_native 做静态 import 扫描。包未建时测试空跑通过；
一旦有人在禁区内引入 MAF / 框架 / ORM 依赖，本测试立即拦截（第 1 周的边界就从第一天被机器守住）。
"""
from __future__ import annotations

import ast
import pathlib

BACKEND_SRC = pathlib.Path(__file__).resolve().parents[2] / "backend" / "src" / "ai_native"

MAF_IMPORT_PREFIXES = ("agent_framework", "agent_framework_core")

# domain 层禁止依赖的框架 / 基础设施顶层包名（按冻结文本 6.2 逐条对应）
DOMAIN_FORBIDDEN_PREFIXES = frozenset(
    {
        "fastapi",
        "pydantic",
        "sqlalchemy",
        "psycopg",
        "agent_framework",
        "agent_framework_core",
    }
)


def _iter_py_files(root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in root.rglob("*.py") if p.is_file()]


def _imported_top_levels(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tops: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                tops.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                tops.add(node.module.split(".")[0])
    return tops


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(BACKEND_SRC).as_posix()


def test_maf_only_importable_under_runtime_maf() -> None:
    violators = []
    for path in _iter_py_files(BACKEND_SRC):
        rel = _rel(path)
        imported = _imported_top_levels(path)
        imports_maf = sorted(imported & set(MAF_IMPORT_PREFIXES))
        if imports_maf and not rel.startswith("runtime/maf/"):
            violators.append((rel, imports_maf))
    assert not violators, f"MAF 只能在 runtime/maf 内导入，违例: {violators}"


def test_domain_layer_must_not_depend_on_frameworks() -> None:
    violators = []
    for path in _iter_py_files(BACKEND_SRC):
        rel = _rel(path)
        if "/domain/" not in rel:
            continue
        bad = sorted(_imported_top_levels(path) & DOMAIN_FORBIDDEN_PREFIXES)
        if bad:
            violators.append((rel, bad))
    assert not violators, f"domain 层不得依赖框架/ORM，违例: {violators}"