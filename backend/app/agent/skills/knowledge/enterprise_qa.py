from agent.skills.base import Skill, SkillDefinition


enterprise_qa_skill = Skill(
    SkillDefinition(
        name="enterprise.knowledge",
        description="检索企业制度、员工手册和知识库内容",
        triggers=("制度", "员工手册", "公司规定", "知识库"),
        tool_names=("search_handbook",),
        priority=10,
    )
)
