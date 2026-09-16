"""07/08/09 机器合同可解析 + 引用闭合（第 1 周完成条件之一）。

真实口径:pytest 绿 = 9 份合同全部可解析，且所有外部 $ref 都能解析到
「已收集的 $id」或「design-contracts 内存在的相对文件」。

冻结合同里并存两种引用风格:
- JSON Schema 之间用 $id URL（https://schemas.ai-native.local/...）；
- openapi.yaml 用相对文件路径（./problem-details.schema.json、../08_WorkflowDefinition/...）。

本测试只做解析与引用闭包，不做文档—Schema 全量校验（待引入 jsonschema 后补）。
"""
from __future__ import annotations

import json
import pathlib

import yaml

CONTRACTS = pathlib.Path(__file__).resolve().parents[2] / "design-contracts"


def _docs() -> dict[pathlib.Path, dict]:
    docs: dict[pathlib.Path, dict] = {}
    for p in sorted(CONTRACTS.rglob("*")):
        if p.suffix not in (".json", ".yaml", ".yml"):
            continue
        txt = p.read_text(encoding="utf-8")
        docs[p] = yaml.safe_load(txt) if p.suffix == ".yaml" else json.loads(txt)
    return docs


def _refs(node) -> list[str]:
    out: list[str] = []

    def walk(x) -> None:
        if isinstance(x, dict):
            if isinstance(x.get("$ref"), str):
                out.append(x["$ref"])
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(node)
    return out


def test_nine_contracts_all_parse() -> None:
    docs = _docs()
    assert len(docs) == 9, sorted(p.name for p in docs)
    schemas = [p for p in docs if p.name.endswith(".schema.json")]
    assert len(schemas) == 6, sorted(p.name for p in schemas)
    for p in schemas:
        d = docs[p]
        assert isinstance(d, dict), p.name
        assert d.get("$schema", "").startswith(
            "https://json-schema.org/draft/2020-12"
        ), f"{p.name} 不是 JSON Schema 2020-12"


def test_openapi_is_3x() -> None:
    docs = _docs()
    openapi = next(p for p in docs if p.suffix == ".yaml")
    doc = docs[openapi]
    assert doc.get("openapi", "").startswith("3."), doc.get("openapi")
    assert "paths" in doc


def test_external_refs_resolve() -> None:
    docs = _docs()
    ids = {
        doc.get("$id")
        for doc in docs.values()
        if isinstance(doc, dict) and doc.get("$id")
    }
    unresolved: list[tuple[str, str]] = []
    for p, doc in docs.items():
        for ref in _refs(doc):
            if ref.startswith("#"):
                continue  # 本地 JSON 指针，此处不深校验
            if ref.startswith("https://"):
                target = ref.split("#")[0]
                if target not in ids:
                    unresolved.append((p.name, ref))
            else:
                resolved = (p.parent / ref.split("#")[0]).resolve()
                if not resolved.exists():
                    unresolved.append((p.name, ref))
    assert not unresolved, f"外部 $ref 未闭合: {unresolved}"