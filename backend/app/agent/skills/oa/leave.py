from agent.skills.base import Skill, SkillDefinition


leave_skill = Skill(
    SkillDefinition(
        name="oa.leave",
        description="处理员工请假、休假和请假申请相关任务",
        triggers=("请假", "休假"),
        tool_names=("search_employee", "query_leave_records", "create_leave_draft", "submit_leave_request"),
        priority=10,
    )
)
