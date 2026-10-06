import unittest

from agent.skills import SkillRegistry


class AgentStructureTest(unittest.TestCase):
    def test_default_skills_route_by_message(self):
        registry = SkillRegistry.default()
        self.assertEqual(registry.select("请查询我的请假记录").definition.name, "oa.leave")
        self.assertEqual(registry.select("员工手册中的年假规定").definition.name, "enterprise.knowledge")
        self.assertIsNone(registry.select("今天天气怎么样"))

if __name__ == "__main__":
    unittest.main()
