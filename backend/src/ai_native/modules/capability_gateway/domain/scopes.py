"""ResourceScope v1（resource-scope.schema.json）四类封闭结构 + 失败关闭的交集。

版本不同无迁移规则 → 不相交；证不出「请求是交集子集」一律 DENY（交集返回 None）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

_RESOURCE_TYPES = ("PROJECT_RESOURCE", "WORKSPACE", "EXTERNAL_DESTINATION", "TOOL_RESOURCE")


@dataclass(frozen=True)
class ResourceScope:
    resource_type: str
    actions: frozenset[str]
    resource_kind: str | None = None
    resource_ids: frozenset[str] | None = None
    directory_id: str | None = None
    paths: tuple = ()
    destination_key: str | None = None
    service_key: str | None = None
    account_ref: str | None = None
    tool_key: str | None = None
    capability_key: str | None = None
    tool_schema_digest: str | None = None
    resource_keys: frozenset[str] | None = None

    def to_dict(self) -> dict:
        d = {"scope_version": "scope.v1", "resource_type": self.resource_type, "actions": sorted(self.actions)}
        for key in (
            "resource_kind", "directory_id", "destination_key", "service_key",
            "account_ref", "tool_key", "capability_key", "tool_schema_digest",
        ):
            v = getattr(self, key)
            if v is not None:
                d[key] = v
        if self.resource_ids is not None:
            d["resource_ids"] = sorted(self.resource_ids)
        if self.resource_keys is not None:
            d["resource_keys"] = sorted(self.resource_keys)
        if self.paths:
            d["paths"] = list(self.paths)
        return d


def intersect(a: ResourceScope, b: ResourceScope) -> ResourceScope | None:
    """两 scope 交集；类型/版本/身份不可比即 None（失败关闭）。"""
    if a.resource_type != b.resource_type:
        return None
    actions = a.actions & b.actions
    if not actions:
        return None
    t = a.resource_type
    if t == "PROJECT_RESOURCE":
        if a.resource_kind != b.resource_kind:
            return None
        ids = (a.resource_ids or frozenset()) & (b.resource_ids or frozenset())
        if not ids:
            return None
        return ResourceScope(t, actions, resource_kind=a.resource_kind, resource_ids=ids)
    if t == "TOOL_RESOURCE":
        if (a.tool_key, a.capability_key, a.tool_schema_digest) != (b.tool_key, b.capability_key, b.tool_schema_digest):
            return None
        keys = (a.resource_keys or frozenset()) & (b.resource_keys or frozenset())
        if not keys:
            return None
        return ResourceScope(t, actions, tool_key=a.tool_key, capability_key=a.capability_key, tool_schema_digest=a.tool_schema_digest, resource_keys=keys)
    if t == "EXTERNAL_DESTINATION":
        if (a.destination_key, a.service_key) != (b.destination_key, b.service_key):
            return None
        if a.account_ref and b.account_ref and a.account_ref != b.account_ref:
            return None
        keys = (a.resource_keys or frozenset()) & (b.resource_keys or frozenset())
        if not keys:
            return None
        return ResourceScope(t, actions, destination_key=a.destination_key, service_key=a.service_key, resource_keys=keys)
    if t == "WORKSPACE":
        if a.directory_id != b.directory_id:
            return None
        # 保守：覆盖集可证一方为子集才相交，否则失败关闭
        p = _narrower_paths(a.paths or (), b.paths or ())
        if p is None:
            return None
        return ResourceScope(t, actions, directory_id=a.directory_id, paths=p)
    return None


def _narrower_paths(x: tuple, y: tuple) -> tuple | None:
    if not x or not y:
        return None
    if x == y:
        return x
    xs, ys = frozenset(x), frozenset(y)
    if xs <= ys:
        return x
    if ys <= xs:
        return y
    return None


def covers(granted: ResourceScope, cand: ResourceScope) -> bool:
    """cand 是否为 granted 的子集（请求 ⊆ 授权交集）。"""
    if cand.resource_type != granted.resource_type:
        return False
    if not (cand.actions <= granted.actions):
        return False
    t = cand.resource_type
    if t == "PROJECT_RESOURCE":
        return cand.resource_kind == granted.resource_kind and (cand.resource_ids or frozenset()) <= (granted.resource_ids or frozenset())
    if t == "TOOL_RESOURCE":
        return (cand.tool_key, cand.capability_key, cand.tool_schema_digest) == (granted.tool_key, granted.capability_key, granted.tool_schema_digest) and (cand.resource_keys or frozenset()) <= (granted.resource_keys or frozenset())
    # WORKSPACE / EXTERNAL_DESTINATION 简化：全等才覆盖
    return cand == granted