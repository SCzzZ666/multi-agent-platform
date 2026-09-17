"""确定性 transform / condition 注册表（不调模型、无副作用，05 基线 transform 语义）。

v1：condition 恒返回 EXECUTE；接入 PlanValidator 后由确定性校验结果替换（三态落库项）。
"""
from __future__ import annotations


def _normalize(data: dict) -> dict:
    return {**data, "normalized_input": str(data.get("input", "")).strip()}


def _validate_plan(data: dict) -> dict:
    # v1 确定性通过；真实校验接 runtime/plan_validator 后据 verdict 落 route
    return {**data, "plan_valid": True, "route": "EXECUTE"}


TRANSFORM_REGISTRY: dict[str, object] = {
    "input.normalize": _normalize,
    "plan.validate": _validate_plan,
}


def _route_execute(data: dict) -> str:
    return data.get("route", "EXECUTE")


CONDITION_REGISTRY: dict[str, object] = {
    "plan.route": _route_execute,
}

# role_ref → 系统提示（首版简版，完整 profile_json 后续落地）
ROLE_PROMPTS: dict[str, str] = {
    "planner": "你是规划者(planner)。基于输入拆解任务，只输出简洁的执行计划。",
    "architect": "你是架构师(architect)。基于输入给出技术方案设计。",
    "engineer": "你是工程师(engineer)。基于输入产出交付内容(实现说明)。",
    "validator": "你是独立验证者(validator)。检查结果质量，输出 PASS 或 REWORK+理由。",
    "researcher": "你是研究员(researcher)。基于输入收集整理资料与来源。",
    "analyst": "你是分析师(analyst)。基于输入做数据分析并给出结论。",
    "writer": "你是撰写者(writer)。基于已验证内容形成报告。",
    "skill_maintainer": "你是技能维护者(skill_maintainer)。规范化并维护 Skill 包。",
}


def role_prompt(role_ref: str) -> str:
    return ROLE_PROMPTS.get(role_ref, f"你是 {role_ref} 角色，基于上下文完成职责。")