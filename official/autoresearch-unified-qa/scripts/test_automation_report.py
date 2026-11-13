import unittest

import audit_unified


class AutomationReportTests(unittest.TestCase):
    def result(self):
        return {
            'decision': 'MATERIALS_INCOMPLETE',
            'context': {'mode': 'standard'},
            'sections': {},
            'summary': {'scope': '完整已交材料的静态审查', 'failed_checks': []},
            'missing_materials': [
                {'check_id': 'QA18', 'missing_material': '用于确认当前候选身份的原始结果',
                 'why_needed': '两份现有记录无法建立同一候选关联。',
                 'reviewed_evidence': ['evidence/summary.json'],
                 'next_action': '提供已有候选关联记录。', 'owner': 'author'},
                {'check_id': 'H03', 'missing_material': '运行包发布镜像身份',
                 'why_needed': '运行包需要有效镜像。',
                 'reviewed_evidence': ['task.toml'],
                 'next_action': '平台补充实际发布镜像。', 'owner': 'platform'},
            ],
        }

    def test_missing_materials_are_explicitly_not_passed(self):
        text = audit_unified.render(self.result())
        self.assertIn('材料不完整，未通过', text)
        self.assertIn('用于确认当前候选身份的原始结果', text)
        self.assertIn('运行包发布镜像身份', text)
        self.assertNotIn('待人工', text)

    def test_platform_gap_is_not_sent_as_author_submission(self):
        text = audit_unified.expert_text(self.result())
        author_part = text.split('平台材料缺口')[0]
        self.assertIn('用于确认当前候选身份的原始结果', author_part)
        self.assertNotIn('运行包发布镜像身份', author_part)
        self.assertIn('平台材料缺口（不要求专家补内部运行材料）', text)

    def test_tool_error_stays_internal_and_never_calls_it_materials_missing(self):
        result = self.result()
        result['decision'] = 'REVIEW_INCOMPLETE'
        result['missing_materials'] = []
        text = audit_unified.expert_text(result)
        self.assertIn('自动检查未完成', text)
        self.assertNotIn('质检员仍需', text)
        self.assertNotIn('待人工', text)
        self.assertNotIn('材料不完整，未通过', text)

    def test_expert_actions_use_concrete_legacy_finding_remediation(self):
        result = self.result()
        result['decision'] = 'FAIL'
        result['summary']['failed_checks'] = [{
            'section': 'core', 'id': 'QA06', 'status': 'fail',
            'summary': '入口仅输出常量。', 'evidence': ['tests/test.sh'],
            'findings': [{'kind': 'substantive', 'effect': 'unwaived', 'final_effect': 'blocking',
                'summary': '未读取候选。', 'evidence': ['tests/test.sh'],
                'remediation': '入口调用真实候选评测函数。', 'acceptance_evidence': '候选指标与正式主分一致。'}],
        }]
        text = audit_unified.expert_text(result)
        self.assertIn('入口调用真实候选评测函数。', text)
        self.assertIn('复检依据：候选指标与正式主分一致。', text)
        self.assertNotIn('按已确认问题定位修改位置', text)

    def test_derived_failure_displays_its_actual_cause_not_old_pass_summary(self):
        row = {'id': 'H03', 'status': 'fail', 'summary': '原路径静态通过。',
               'format_root_causes': [{'owner': 'F05', 'summary': '公开Dev入口缺失。'}]}
        self.assertEqual(audit_unified.row_summary(row), '关联格式检查失败：公开Dev入口缺失。')


if __name__ == '__main__':
    unittest.main()
