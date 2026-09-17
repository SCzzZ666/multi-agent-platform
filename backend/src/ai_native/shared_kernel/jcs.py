"""RFC 8785 JCS 规范化 + SHA-256 摘要（09 基线 §9.4 摘要顺序的前置）。

MVP 说明：键按 code point 排序（RFC8785 用 UTF-16 code unit，对非 BMP 键有细微差异）、
float 用 Python repr（与 ECMAScript NumberToString 有边界差异）；本实现内部一致、
服务端两侧同代码重算，满足「授权一律用服务端重算摘要」的确定性要求。
"""
from __future__ import annotations

import hashlib
import math


def _escape(s: str) -> str:
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif o < 0x20:
            out.append(f"\\u{o:04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _number(n) -> str:
    if isinstance(n, bool):
        raise TypeError("bool 不是 JCS number")
    if isinstance(n, int):
        return str(n)
    if isinstance(n, float):
        if not math.isfinite(n):
            raise ValueError("非有限数不能 JCS 规范化")
        return repr(n)
    raise TypeError(f"不支持的类型: {type(n)}")


def canonicalize(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return _escape(value)
    if isinstance(value, (int, float)):
        return _number(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonicalize(v) for v in value) + "]"
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda kv: kv[0])
        return "{" + ",".join(_escape(k) + ":" + canonicalize(v) for k, v in items) + "}"
    raise TypeError(f"不支持的类型: {type(value)}")


def jcs_digest(value) -> str:
    """按 JCS 规范化出 UTF-8 规范字节 → SHA-256 → 'sha256:64hex'。"""
    raw = canonicalize(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()