from agent.skills.base import Skill, SkillDefinition


approval_skill = Skill(
    SkillDefinition(
        name="oa.approval",
        description="查询和处理 OA 审批状态",
        triggers=("审批", "审核"),
        tool_names=("query_approval", "approve", "reject"),
        priority=10,
    )
)
