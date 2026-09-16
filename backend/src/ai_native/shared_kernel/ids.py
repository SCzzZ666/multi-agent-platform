"""应用侧 UUIDv7(存 uuid，约束版本位；不靠 UUID 排序表达业务序)。

对应 04 基线 6.1：公开主键用应用侧 UUIDv7 存 uuid。
"""
from __future__ import annotations

import time
import uuid


def uuid7() -> uuid.UUID:
    """RFC 9562 风格的 UUIDv7（48-bit unix 毫秒 + 随机位），单调性由调用方约束。"""
    ts_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rnd = bytearray(uuid.uuid4().bytes)
    # 版本位 = 0b0111（byte 6 高 4 位）
    rnd[6] = (rnd[6] & 0x0F) | 0x70
    # 变体位 = 0b10（byte 8 高 2 位）
    rnd[8] = (rnd[8] & 0x3F) | 0x80
    # 时间戳覆盖前 6 字节
    rnd[0:6] = ts_ms.to_bytes(6, "big")
    return uuid.UUID(bytes=bytes(rnd))


def new_id() -> str:
    return str(uuid7())