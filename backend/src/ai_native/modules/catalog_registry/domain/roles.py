"""固定 8 角色目录（运行配置，不是 8 个服务）—— 05 基线冻结，不可新增/重定义。

「指挥官—专家—验证者」只是口语协作分层（12 基线 D12-03）：
- 指挥官 = planner（唯一协调规划）
- 专家 = architect / engineer / researcher / analyst / writer / skill_maintainer
- 验证者 = validator（独立质量门）

不可变不变量：不得新增 commander 角色、不得合并 Validator 职责、不得让 Planner 宣布质量通过。
完整 role_definition.profile_json（I/O 合同、model_policy_ref、能力上限）后续按 05 基线落地；
本模块先固化 8 角色身份与分层映射。
"""
from __future__ import annotations

from dataclasses import dataclass

COMMANDER = "commander"
EXPERT = "expert"
VALIDATOR = "validator"


@dataclass(frozen=True)
class RoleDefinition:
    role_id: str
    title: str
    layer: str
    unique_coordinator: bool = False


ROLE_CATALOG: tuple[RoleDefinition, ...] = (
    RoleDefinition("planner", "规划者", COMMANDER, unique_coordinator=True),
    RoleDefinition("architect", "架构师", EXPERT),
    RoleDefinition("engineer", "工程师", EXPERT),
    RoleDefinition("researcher", "研究员", EXPERT),
    RoleDefinition("analyst", "分析师", EXPERT),
    RoleDefinition("writer", "撰写者", EXPERT),
    RoleDefinition("skill_maintainer", "技能维护者", EXPERT),
    RoleDefinition("validator", "验证者", VALIDATOR),
)

ROLE_IDS: list[str] = [r.role_id for r in ROLE_CATALOG]


def is_fixed_role(role_id: str) -> bool:
    return role_id in ROLE_IDS


def roles_of_layer(layer: str) -> list[str]:
    return [r.role_id for r in ROLE_CATALOG if r.layer == layer]


def commander_roles() -> list[str]:
    return roles_of_layer(COMMANDER)


def validator_roles() -> list[str]:
    return roles_of_layer(VALIDATOR)