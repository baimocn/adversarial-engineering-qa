"""Profile and owner integration regressions; no submitted task is executed."""
import copy
import unittest

import audit_unified as unified
import audit_auto as auto
import automation_final


class DialogueIntegrationTests(unittest.TestCase):
    def report(self):
        return {'context':{'mode':'legacy-waiver','package_stage':'source'},'sections':{
            name:{'complete':True,'errors':[],'checks':[
                {'id':key,'status':'pass','summary':'Existing actual materials reviewed','evidence':['tests/test.sh:1']}
                for key in sorted(ids)]} for name,ids in automation_final.EXPECTED.items()}}

    def group(self, name, owner, **changes):
        row={'name':name,'owner_id':owner,'status':'pass','summary':'Read actual task constraints and selected scoring contract',
            'evidence':['tests/test.sh:1'],'required_for_static_completion':True,'review_complete':True,
            'problems':[],'advisories':[]}
        row.update(changes)
        return row

    def test_future_intake_cannot_inherit_legacy_waivers(self):
        with self.assertRaises(ValueError):
            unified.context(None,intake_cohort='new_1104')
        ctx=unified.context(None,mode='standard',intake_cohort='new_1104')
        self.assertEqual(ctx['intake_cohort'],'new_1104')

    def test_historical_no_score_route_is_narrow(self):
        for cohort in ('unspecified','new_1104',None):
            with self.subTest(cohort=cohort),self.assertRaises(ValueError):
                unified.context(None,mode='standard',intake_cohort=cohort,rollout_policy='historical_1h')
        ctx=unified.context(None,intake_cohort='legacy_831',rollout_policy='historical_1h')
        self.assertEqual(ctx['rollout_policy'],'historical_1h')

    def test_declared_profile_conflict_is_not_silently_relabelled(self):
        with self.assertRaises(ValueError):
            unified.context({'context':{'intake_cohort':'legacy_831'}},mode='standard',intake_cohort='new_1104')
        with self.assertRaises(ValueError):
            unified.context({'context':{'target_level':'L1'}},target_level='L2')

    def test_automatic_reviewer_cannot_invent_an_admission_exception(self):
        ctx={'mode':'standard','provider':'unknown','package_stage':'runtime'}
        for change in ({'intake_cohort':'legacy_831'},{'rollout_policy':'historical_1h'},{'target_level':'L1'}):
            with self.subTest(change=change),self.assertRaises(ValueError):
                auto.freeze_review_context({'context':{**ctx,**change}},ctx)
        frozen={**ctx,'intake_cohort':'new_1104','rollout_policy':'scored_required','target_level':'L1'}
        self.assertEqual(auto.freeze_review_context({'context':copy.deepcopy(frozen)},frozen),frozen)

    def test_current_normalization_defect_survives_historical_disposition(self):
        report=self.report()
        owner=next(r for r in report['sections']['core']['checks'] if r['id']=='QA02')
        owner['status']='pass_with_waivers'
        problem={'code':'target_anchor_mismatch','reason':'Latency uses a different-hardware constant as the formal zero anchor',
            'remediation':'Calibrate the affected formal anchor under the target protocol',
            'evidence':['tests/test.sh:1'],'related_checks':['QA13','QA15']}
        unified.apply_engineering(report,{'checks':[self.group('normalization_anchors','QA02',status='fail',problems=[problem])],
            'errors':[],'claims':{}},shared_key='delivery_contract_review')
        self.assertEqual(owner['status'],'fail')
        self.assertEqual(sum(len(s['checks']) for s in report['sections'].values()),90)
        summary=unified.summarize(report['sections'],mode='legacy-waiver')
        self.assertEqual(summary['decision'],'FAIL')
        report['summary']=summary
        self.assertEqual(len(unified.classified_actions(report)['author']),1)

    def test_read_material_gap_and_unread_review_remain_distinct(self):
        for complete in (True,False):
            with self.subTest(complete=complete):
                report=self.report()
                unified.apply_engineering(report,{'checks':[self.group('batch_acceptance','H04',
                    status='evidence_limited' if complete else 'unreviewed',review_complete=complete)],
                    'errors':[]},shared_key='delivery_contract_review')
                owner=next(r for r in report['sections']['core']['checks'] if r['id']=='H04')
                self.assertEqual(owner['status'],'manual')
                self.assertIs(owner['review_complete'],complete)

    def test_high_priority_image_note_is_visible_without_size_gate(self):
        report=self.report()
        note={'priority':'high','reason':'The fixed CPU role has an unused CUDA devel base stack',
            'remediation':'Choose a compatible lighter base after dependency review','evidence':['tests/test.sh:1']}
        unified.apply_engineering(report,{'checks':[self.group('image_dependency_fit','QA15',advisories=[note])],
            'errors':[],'claims':{}},shared_key='delivery_contract_review')
        report['summary']=unified.summarize(report['sections'],mode='legacy-waiver')
        report['decision']=report['summary']['decision']
        self.assertEqual(report['decision'],'PASS')
        self.assertEqual(len(unified.high_priority_advisories(report)),1)
        self.assertIn(note['reason'],unified.expert_text(report))

    def test_new_shared_facts_do_not_overwrite_previous_engineering(self):
        report=self.report()
        first={'checks':[self.group('score_paths','H04')],'errors':[],'claims':{'has_score':True}}
        second={'checks':[self.group('batch_acceptance','H04')],'errors':[],'claims':{'runtime_verified':False}}
        unified.apply_engineering(report,first)
        unified.apply_engineering(report,second,shared_key='delivery_contract_review')
        self.assertTrue(report['sections']['core']['engineering_review']['claims']['has_score'])
        self.assertFalse(report['sections']['core']['delivery_contract_review']['claims']['runtime_verified'])

    def test_unfinished_new_review_cannot_hide_earlier_confirmed_failure(self):
        report=self.report()
        owner=next(r for r in report['sections']['core']['checks'] if r['id']=='QA11')
        owner.update(status='fail',summary='A legitimate shape is rejected by an undisclosed bound')
        unified.apply_engineering(report,{'checks':[self.group('task_contract','QA11',status='unreviewed',review_complete=False)],
            'errors':[]},shared_key='delivery_contract_review')
        self.assertEqual(owner['status'],'fail')
        summary=unified.summarize(report['sections'],mode='legacy-waiver')
        self.assertEqual(summary['decision'],'FAIL')
        self.assertFalse(summary['review_complete'])


if __name__=='__main__':
    unittest.main()
