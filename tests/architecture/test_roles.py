"""固定 8 角色 + 三层称谓映射不变式（第 1 周完成条件 #4）。

真实口径：8 个角色身份与「指挥官—专家—验证者」映射被机器断言守住，
任何新增 commander、合并 validator 职责、让 planner 宣布通过的改动都会在此失败。
"""
from __future__ import annotations

from ai_native.modules.catalog_registry.domain.roles import (
    ROLE_CATALOG,
    ROLE_IDS,
    commander_roles,
    is_fixed_role,
    roles_of_layer,
    validator_roles,
)

EXPECTED_IDS = [
    "planner",
    "architect",
    "engineer",
    "researcher",
    "analyst",
    "writer",
    "skill_maintainer",
    "validator",
]


def test_exactly_eight_roles() -> None:
    assert sorted(ROLE_IDS) == sorted(EXPECTED_IDS)
    assert len(set(ROLE_IDS)) == 8
    assert "commander" not in ROLE_IDS, "三层称谓是口语分层，不新增 commander 角色"


def test_planner_is_sole_coordinator() -> None:
    assert commander_roles() == ["planner"]


def test_validator_is_independent_gate() -> None:
    assert validator_roles() == ["validator"]
    assert roles_of_layer("validator") != roles_of_layer("commander")


def test_expert_layer_is_six_roles() -> None:
    assert sorted(roles_of_layer("expert")) == sorted(
        ["architect", "engineer", "researcher", "analyst", "writer", "skill_maintainer"]
    )


def test_fixed_role_checker() -> None:
    for rid in EXPECTED_IDS:
        assert is_fixed_role(rid)
    assert not is_fixed_role("commander")
    assert not is_fixed_role("supervisor")