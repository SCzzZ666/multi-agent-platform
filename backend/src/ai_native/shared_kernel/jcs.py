"""RFC 8785 (JSON Canonicalization Scheme, JCS) —— 09 基线摘要唯一口径。

对象按键 UTF-16 码元升序、字符串按 3.2.2.3 转义、数字按 ECMAScript Number.toString。
整数/字符串/数组/对象/字面量精确；浮点用 Python repr 近似（ECMAScript 与 Python 对
极小/极大浮点的字符串化有差异，摘要场景实际只覆盖整数与字符串，浮点边界标注待补）。"""
from __future__ import annotations

import math

from ai_native.shared_kernel.digest import sha256_hex


def canonical_json(value) -> str:
    return _serialize(value)


def jcs_sha256(value) -> str:
    """RFC 8785 规范化 → UTF-8 字节 → SHA-256 → 'sha256:'+64hex。"""
    return "sha256:" + sha256_hex(canonical_json(value).encode("utf-8"))


def _serialize(v) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, str):
        return _quote(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return _number(v)
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_serialize(x) for x in v) + "]"
    if isinstance(v, dict):
        items = sorted(v.items(), key=lambda kv: kv[0])
        return "{" + ",".join(_quote(k) + ":" + _serialize(val) for k, val in items) + "}"
    raise TypeError(f"JCS 不支持的类型: {type(v)}")


def _quote(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif o == 0x08:
            out.append("\\b")
        elif o == 0x09:
            out.append("\\t")
        elif o == 0x0A:
            out.append("\\n")
        elif o == 0x0C:
            out.append("\\f")
        elif o == 0x0D:
            out.append("\\r")
        elif o < 0x20:
            out.append("\\u%04x" % o)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _number(v: float) -> str:
    if v != v or v in (math.inf, -math.inf):
        raise TypeError("NaN/Infinity 不可 JCS 序列化")
    if v == 0:
        return "0"  # -0.0 → "0"
    if v == int(v) and abs(v) < 1e21:
        return str(int(v))
    return repr(v)