"""End-to-end policy invariants; no submitted programs, models or Harbor run."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import audit_unified as unified
import test_audit_standard_with_waivers as fixtures


class UnifiedReviewTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.StandardWaiverTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root
        self.counter=0

    def worksheet(self):
        return {'context':{'mode':'standard','provider':'innerfield-maso-v1','package_stage':'source'},
            'standard':copy.deepcopy(self.fixture.sr),
            'format':{**copy.deepcopy(self.fixture.lr),'stage':'format_repair'}}

    def audit(self,w=None):
        self.counter+=1
        return unified.assess(self.root,w,out=self.fixture.base/('unified-'+str(self.counter)))

    def test_all_modules_run_without_worksheet_and_never_claim_pass(self):
        result=self.audit()
        self.assertEqual(result['coverage_counts'],{'core':31,'format':7,'current_standard':3,'supplement':49})
        self.assertNotIn(result['decision'],{'PASS','PASS_WITH_WAIVERS'})
        self.assertFalse(result['task_code_executed'])
        algorithm=result['sections']['supplement']['algorithm_output']
        self.assertLessEqual(len(algorithm['main_conclusion']),100)
        self.assertNotEqual(algorithm['conclusion'],'no_must_modify')
        self.assertFalse(algorithm['difficulty']['acceptance_gate'])
        self.assertIn('算法A单题主结论',unified.render(result))

    def test_g01_failure_does_not_short_circuit_remaining_review(self):
        w=self.worksheet()
        g=next(r for r in w['standard']['content_gates']['checks'] if r['id']=='G01')
        g.update(status='fail',summary='The supplied guard only accepts numeric constants.',
            remediation='Open an executable method interface.',acceptance_evidence='Consistent executable interface and instruction.')
        result=self.audit(w)
        self.assertEqual(result['decision'],'FAIL')
        core={r['id']:r for r in result['sections']['core']['checks']}
        self.assertEqual(core['G01']['status'],'fail')
        self.assertEqual(core['QA21']['status'],'pass')
        self.assertNotIn('H06',core)
        self.assertIn('H05',core)
        self.assertEqual(len(result['sections']['supplement']['checks']),49)

    def test_malformed_core_review_cannot_hide_new_confirmed_failure(self):
        w=self.worksheet();w['standard']['overview']={}
        p=self.root/'current/verifier';p.mkdir(parents=True)
        (p/'reward.txt').write_text('0.4');(p/'reward.json').write_text('{"reward":NaN}')
        w['current_standard']={'reward_runs':[{'files':['current/verifier/reward.txt','current/verifier/reward.json']}]}
        result=self.audit(w)
        self.assertEqual(result['decision'],'FAIL')
        self.assertTrue(result['summary']['unfinished_count'])
        self.assertEqual(next(r for r in result['sections']['current_standard']['checks'] if r['id']=='CS04')['status'],'fail')
        self.assertEqual(result['coverage_counts']['supplement'],49)

    def test_inspection_does_not_execute_or_modify_submission(self):
        sentinel=self.root/'DO_NOT_CREATE'
        program=self.root/'environment/unsafe_candidate.py'
        program.write_text('from pathlib import Path\nPath('+repr(str(sentinel))+').write_text("executed")\n')
        before={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.audit()
        after={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        self.assertFalse(sentinel.exists())

    def test_context_conflict_is_not_silently_relabelled(self):
        with self.assertRaises(ValueError):
            unified.context({'context':{'provider':'innerfield-maso-v1'}},provider='mido-2026-11-03')

    def test_unknown_provider_not_silently_maso(self):
        w=self.worksheet();w['context']['provider']='unknown'
        w['standard']['harbor'].pop('deployment_profile',None)
        result=self.audit(w)
        self.assertNotIn(result['decision'],{'PASS','PASS_WITH_WAIVERS'})
        deployment=result['sections']['core'].get('components',{}).get('harbor',{}).get('deployment_contract',{})
        self.assertEqual(deployment.get('profile'),'unknown')

    def test_current_proof_waiver_cannot_clear_confirmed_fail(self):
        current={'checks':[{'id':'CS05','status':'fail','summary':'Complete current timeout has 20 responses.'}]}
        w={'current_resolutions':[{'id':'CS05','waiver_reason':'legacy_runtime_proof_gap','scope':'historical_records_only',
            'content_review_complete':True,'new_record_requirement_only':True,'summary':'Historical proof gap only.','evidence':['instruction.md']}]}
        unified.apply_current_waivers(self.root,current,w,{'mode':'legacy-waiver'})
        self.assertEqual(current['checks'][0]['status'],'fail')
        self.assertTrue(current['errors'])

    def test_standard_cannot_apply_legacy_resolution(self):
        current={'checks':[{'id':'CS05','status':'review'}]}
        unified.apply_current_waivers(self.root,current,{'current_resolutions':[{'id':'CS05'}]},{'mode':'standard'})
        self.assertEqual(current['checks'][0]['status'],'review')
        self.assertTrue(current['errors'])

    def test_platform_failure_is_separate_from_expert_repair(self):
        result={'decision':'FAIL','context':{'mode':'standard'},'sections':{},
            'summary':{'failed_checks':[{'section':'supplement','id':'B-P12','summary':'Platform must repair selected build context.',
                'responsibility':'platform','remediation':'Repair platform packaging.','evidence':['task.toml']}]}}
        result['actions']=unified.classified_actions(result)
        text=unified.expert_text(result)
        self.assertIn('专家需返修：\n无已确认事项。',text)
        self.assertIn('平台需处理：\nsupplement/B-P12',text)

    def test_confirmed_csr_failure_not_lost_when_owner_unknown(self):
        result={'decision':'FAIL','context':{'mode':'standard'},'sections':{},
            'summary':{'failed_checks':[{'section':'current_standard','id':'CS04','summary':'Current reward is not finite.',
                'responsibility':'reviewer','remediation':'Repair the real invalid score.','evidence':['task.toml']}]}}
        result['actions']=unified.classified_actions(result)
        text=unified.expert_text(result)
        self.assertIn('双方协调：\ncurrent_standard/CS04',text)
        self.assertIn('Current reward is not finite.',text)

    def test_human_report_keeps_formal_values_and_methods(self):
        result=self.audit(self.worksheet())
        text=unified.render(result)
        comparison=result['sections']['core']['raw']['overview']['baseline_reference']
        self.assertIn(comparison['baseline_method'],text)
        self.assertIn(comparison['reference_method'],text)
        for pair in comparison['paired_runs']:
            line=next(line for line in text.splitlines() if line.startswith('| '+str(pair['seed'])+' |'))
            fields=[value.strip() for value in line.split('|')]
            self.assertEqual(float(fields[2]),pair['baseline'])
            self.assertEqual(float(fields[3]),pair['reference'])
        self.assertNotIn('H06 |',text)
        self.assertNotIn('NOP 自检记录',text)

    def test_nonblocking_platform_coverage_is_not_silently_runtime_pass(self):
        sections={'one':{'complete':True,'checks':[{'id':'B-P01','status':'review','required_for_static_completion':False,
            'summary':'Platform has not executed this stage.'}]}}
        result=unified.summarize(sections,mode='standard')
        self.assertEqual(result['decision'],'PASS')
        self.assertEqual(sections['one']['checks'][0]['status'],'review')

    def test_incomplete_coverage_cannot_be_counted_as_pass(self):
        result=unified.summarize({'one':{'complete':False,'checks':[{'id':'A03','status':'pass'}]}},mode='standard')
        self.assertEqual(result['decision'],'REVIEW_INCOMPLETE')

    def test_runtime_missing_published_image_is_platform_not_expert(self):
        w=self.worksheet()
        w['context'].update(provider='mido-2026-11-03',package_stage='runtime')
        result=self.audit(w)
        self.assertTrue(any(r.get('code')=='published_image_required' for r in result['actions']['platform']))
        self.assertFalse(any('已发布镜像' in r['summary'] for r in result['actions']['author']))
        # The actual runtime preparation defect is owned by format/F06. A
        # source/core row need not duplicate that provider-specific failure.
        self.assertTrue(any('format/F06' in r.get('related_checks',[]) for r in result['actions']['platform'] if r.get('code')=='published_image_required'))

    def test_bad_standard_object_does_not_prevent_other_modules(self):
        w=self.worksheet();w['standard']=[]
        result=self.audit(w)
        self.assertEqual(result['coverage_counts'],{'core':31,'format':7,'current_standard':3,'supplement':49})
        self.assertNotIn(result['decision'],{'PASS','PASS_WITH_WAIVERS'})

    def test_format_reuses_same_reviewed_gpu_selection(self):
        w=self.worksheet();w['format']['task_type']='gpu'
        with (self.root/'task.toml').open('a') as stream:
            stream.write('\n[environment]\ngpus=1\ngpu_types=["H20","A100"]\n')
        choice={'runner_supports_candidates':True,'project_accepts_candidates':True,'selected_type':'H20',
            'fallback_types':[],'summary':'Existing reviewed target selects H20 only.','evidence':['task.toml']}
        w['standard']['harbor']['gpu_selection']={'agent':choice,'verifier':copy.deepcopy(choice)}
        result=unified.format_review(self.root,w,w['context'])
        self.assertFalse(any(r['code']=='GPU_CANDIDATE_SELECTION' for r in result['scan']['semantic_observations']))
        self.assertNotIn('gpu_selection',w['format'])




class ReviewCompletionPresentationTests(unittest.TestCase):
    def result(self, decision, summary_complete=None, final_complete=None):
        r={'decision':decision,'context':{'mode':'legacy-waiver'},'sections':{},'summary':{}}
        if summary_complete is not None:r['summary']['review_complete']=summary_complete
        if final_complete is not None:r['automation_final']={'review_process_complete':final_complete}
        return r

    def test_confirmed_fail_does_not_claim_unread_checks_complete(self):
        r=self.result('FAIL',False,False)
        self.assertIn('检查尚未完成',unified.render(r))
        txt=unified.expert_text(r)
        self.assertIn('FAIL',txt)
        self.assertIn('其他检查尚未完成',txt)
        self.assertIn('自动检查未完成',txt)
        self.assertNotIn('范围：完整静态审查',txt)

    def test_one_false_completion_flag_wins(self):
        for flags in [(True,False),(False,True),(None,False)]:
            with self.subTest(flags=flags):
                r=self.result('FAIL',*flags)
                self.assertFalse(unified.review_completion(r))
                self.assertIn('自动检查未完成',unified.expert_text(r))

    def test_completed_failure_and_material_gap_are_not_unread(self):
        for decision in ['FAIL','MATERIALS_INCOMPLETE']:
            with self.subTest(decision=decision):
                r=self.result(decision,True,True)
                self.assertTrue(unified.review_completion(r))
                self.assertNotIn('自动检查未完成',unified.expert_text(r))
                self.assertIn('本轮材料审阅已完成',unified.render(r))

    def test_missing_flags_are_unknown_and_not_invented_complete(self):
        self.assertIsNone(unified.review_completion(self.result('FAIL')))

class EngineeringIntegrationTests(unittest.TestCase):
    def result(self):
        return {'context':{'mode':'legacy-waiver','package_stage':'source'},'sections':{
            'core':{'complete':True,'checks':[{'id':key,'status':'pass','summary':'Existing content reviewed',
                'evidence':['tests/test.sh:1']} for key in unified.CORE_IDS], 'errors':[]}}}

    def group(self, name='score_paths', owner='H04', **changes):
        row={'name':name,'owner_id':owner,'status':'pass','review_complete':True,
            'required_for_static_completion':True,'summary':'Existing trusted source paths were reviewed',
            'evidence':['tests/test.sh:1'],'problems':[],'related_checks':['QA06']}
        row.update(changes)
        return row

    def apply(self, result, *groups, claims=None):
        unified.apply_engineering(result,{'checks':list(groups),'errors':[], 'claims':claims or {},'observations':[]})
        result['summary']=unified.summarize(result['sections'],mode='legacy-waiver')
        result['decision']=result['summary']['decision']
        return {r['id']:r for r in result['sections']['core']['checks']}

    def test_new_current_defect_cannot_inherit_old_waiver(self):
        result=self.result()
        original=next(r for r in result['sections']['core']['checks'] if r['id']=='H04')
        original.update(status='pass_with_waivers',waiver={'scope':'historical_records_only'})
        problem={'reason':'Trusted asset failure is converted into a completed candidate grade',
            'remediation':'Classify trusted fault separately before formal result commit',
            'code':'trusted_failure_grade','evidence':['tests/test.sh:1'],'related_checks':['QA06']}
        rows=self.apply(result,self.group(status='fail',problems=[problem]))
        self.assertEqual(rows['H04']['status'],'fail')
        self.assertEqual(rows['H04']['before_engineering']['status'],'pass_with_waivers')
        self.assertEqual(result['decision'],'FAIL')
        self.assertEqual(len(rows),31)
        self.assertEqual(rows['QA06']['status'],'pass')  # Independent fact/judgment retained.
        actions=unified.classified_actions(result)
        self.assertEqual(len(actions['author']),1)
        self.assertIn('QA06',actions['author'][0]['related_checks'])

    def test_unreviewed_is_internal_incomplete_not_material_gap(self):
        result=self.result()
        rows=self.apply(result,self.group(status='unreviewed',review_complete=False))
        self.assertEqual(rows['H04']['status'],'manual')
        self.assertFalse(rows['H04']['review_complete'])
        self.assertFalse(result['sections']['core']['complete'])
        self.assertEqual(result['decision'],'REVIEW_INCOMPLETE')

    def test_read_material_limitation_keeps_gap_disposition_possible(self):
        result=self.result()
        rows=self.apply(result,self.group(status='evidence_limited',review_complete=True))
        self.assertEqual(rows['H04']['status'],'manual')
        self.assertTrue(rows['H04']['review_complete'])

    def test_score_and_formal_eligibility_delivery_are_separate(self):
        result=self.result()
        note={'reason':'QC is attached to the earlier selected Trial',
            'remediation':'Platform should update the selected formal Trial binding','evidence':['tests/test.sh:1']}
        rows=self.apply(result,self.group(),self.group('delivery_lineage','QA21',status='fail',
            delivery_notes_only=True,required_for_static_completion=False,problems=[note],advisories=[note]),
            claims={'has_score':True,'score_valid':True,'formal_adoption':False})
        self.assertEqual(result['decision'],'PASS')
        self.assertEqual(rows['QA21']['status'],'pass')
        self.assertFalse(unified.classified_actions(result)['author'])
        self.assertTrue(result['sections']['core']['engineering_review']['claims']['score_valid'])

    def test_confirmed_fail_survives_unreviewed_other_group(self):
        result=self.result()
        row=next(r for r in result['sections']['core']['checks'] if r['id']=='QA05')
        row.update(status='fail',summary='A necessary stated control is absent')
        rows=self.apply(result,self.group('controls_logs','QA05',status='unreviewed',review_complete=False))
        self.assertEqual(result['decision'],'FAIL')
        self.assertFalse(result['summary']['review_complete'])
        self.assertEqual(rows['QA05']['status'],'fail')

    def test_provided_delivery_schema_error_is_internal_not_author_failure(self):
        result=self.result()
        unified.apply_engineering(result,{'checks':[self.group('delivery_lineage','QA21',
            required_for_static_completion=False,delivery_notes_only=True,status='unreviewed',review_complete=False)],
            'errors':[{'group':'delivery_lineage','required':True,'error':'Selected existing ledger evidence is unreadable'}]})
        summary=unified.summarize(result['sections'],mode='legacy-waiver')
        self.assertEqual(summary['decision'],'REVIEW_INCOMPLETE')
        self.assertFalse(summary['failed_checks'])
        self.assertTrue(result['sections']['core']['errors'])

    def test_shared_root_cause_does_not_duplicate_author_actions(self):
        result=self.result()
        finding={'summary':'Trusted fault shares candidate penalty','code':'engineering.common',
            'evidence':['tests/test.sh:1'],'remediation':'Separate the trusted error result'}
        for key in ('H04','QA06'):
            row=next(r for r in result['sections']['core']['checks'] if r['id']==key)
            row.update(status='fail',engineering_findings=[copy.deepcopy(finding)])
        result['summary']=unified.summarize(result['sections'],mode='legacy-waiver')
        actions=unified.classified_actions(result)['author']
        self.assertEqual(len(actions),1)
        self.assertEqual(actions[0]['related_checks'],['core/QA06','core/H04'])

    def test_complete_engineering_preserves_full90_finalization(self):
        import automation_final
        import engineering_review
        import test_engineering_review
        fixture=test_engineering_review.EngineeringReviewTests();fixture.setUp()
        try:
            result=self.result()
            for name, ids in automation_final.EXPECTED.items():
                result['sections'][name]={'complete':True,'errors':[], 'checks':[
                    {'id':key,'status':'pass','summary':'Existing source was read','evidence':['tests/test.sh:1']}
                    for key in sorted(ids)]}
            engineering=engineering_review.audit(fixture.root,fixture.review())
            unified.apply_engineering(result,engineering)
            final=automation_final.finalize(result,{'automation':{'content_read_complete':True,'material_gaps':[]}},fixture.root)
            self.assertEqual(final['decision'],'PASS')
            self.assertEqual(sum(len(s['checks']) for s in final['sections'].values()),90)
            # A bad explicitly selected existing run is reviewer work, not an
            # author failure or an invented statement that no score exists.
            review=fixture.review();review['reward_runs']=[{'files':['absent/reward.json']}]
            engineering=engineering_review.audit(fixture.root,review)
            self.assertIsNone(engineering['claims']['has_score'])
            unified.apply_engineering(result,engineering)
            final=automation_final.finalize(result,{'automation':{'content_read_complete':True,'material_gaps':[]}},fixture.root)
            self.assertEqual(final['decision'],'REVIEW_INCOMPLETE')
            self.assertFalse(final['summary']['failed_checks'])
        finally:
            fixture.doCleanups()

    def test_format_inventory_computed_once_and_actual_facts_used(self):
        f=fixtures.StandardWaiverTests();f.setUp()
        try:
            w={'context':{'mode':'standard','provider':'innerfield-maso-v1','package_stage':'source'},
                'standard':f.sr,'format':{**f.lr,'stage':'format_repair'}}
            with mock.patch.object(unified.fmt,'inventory',wraps=unified.fmt.inventory) as scan:
                result=unified.format_review(f.root,w,w['context'])
            self.assertEqual(scan.call_count,1)
            self.assertIn('config',result['scan'])
            self.assertEqual(len(result['checks']),7)
            self.assertNotIn('_inventory',result)
        finally:
            f.doCleanups()

if __name__=='__main__':
    unittest.main()
