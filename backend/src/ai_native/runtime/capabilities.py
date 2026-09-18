"""确定性能力注册表（tool 节点经 Gateway 派发到此处执行）。

真实确定性函数（无网络、无外部副作用）；tool 节点只能引用已登记能力，
发现≠授权、连接成功≠授权——授权由 Gateway 的 PDP/Intent/Receipt 链承担。
"""
from __future__ import annotations

from typing import Callable


def _artifact_summarize(data: dict) -> dict:
    return {"summary": {"chars": len(str(data)), "kind": "text"}}


def _text_uppercase(data: dict) -> dict:
    src = data.get("text", str(data)) if isinstance(data, dict) else str(data)
    return {"uppercased": str(src).upper()[:200]}


TOOL_REGISTRY: dict[str, Callable[[dict], dict]] = {
    "artifact.summarize": _artifact_summarize,
    "text.uppercase": _text_uppercase,
}