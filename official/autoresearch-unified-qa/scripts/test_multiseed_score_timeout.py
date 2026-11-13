"""QA15 time-only regression tests; synthetic evidence, no task execution."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import implementation_review as qa
import resource_review as rr
from test_runtime_integrity import complete_resources_fixture


class MultiSeedScoreTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "instruction.md").write_text("Synthetic evidence only")
        (self.root / "task.toml").write_text('[verifier]\nenvironment_mode="separate"\n')

    def tearDown(self):
        self.tmp.cleanup()

    def assess(self, review):
        files = [p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file()]
        return rr.apply_review(rr.collect(self.root, files), review, self.root, qa.review_evidence)

    def multi(self, seconds, seeds=(1, 2, 3, 4, 5)):
        r = complete_resources_fixture()
        r['runs'][0].update(score_seconds=seconds, evaluation_seeds=list(seeds),
                            time_accounting="Same candidate; all declared seeds summed")
        return r

    def formal(self, seconds, roles=('baseline', 'reference')):
        r = complete_resources_fixture(); r['runs'] = []
        for role in roles:
            for i, elapsed in enumerate(seconds, 1):
                ref = f'optimization_evidence/{role}_runs/seed_{i}/result.json'
                p = self.root / ref; p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps({'role': role, 'seed': i}))
                r['runs'].append({'run_id': f'{role}-{i}', 'scope': 'score', 'source_path': ref,
                                  'score_seconds': elapsed, 'gpu_count': 0, 'cpu_cores': 1,
                                  'time_accounting': 'One seed', 'evidence': [ref]})
        return r

    def test_single_seed_boundary_is_unchanged(self):
        r = complete_resources_fixture(); r['runs'][0]['score_seconds'] = 7200
        self.assertEqual(self.assess(r)['status'], 'pass')
        r['runs'][0]['score_seconds'] = 7201
        self.assertEqual(self.assess(r)['status'], 'fail')

    def test_multi_seed_total_boundary(self):
        self.assertEqual(self.assess(self.multi(28800))['status'], 'pass')
        self.assertEqual(self.assess(self.multi(28801))['status'], 'fail')

    def test_multi_seed_above_old_limit_now_passes(self):
        actual = self.assess(self.multi(24000))
        self.assertEqual(actual['status'], 'pass')
        self.assertEqual(actual['estimate_score_time_budget']['limit_seconds'], 28800)

    def test_complete_summary_is_usable_when_formal_per_seed_files_exist(self):
        self.formal([4000]*5)
        actual = self.assess(self.multi(24000))
        self.assertEqual(actual['status'], 'pass')
        self.assertEqual(actual['estimate']['score_seconds'], 24000)

    def test_missing_single_seed_time_is_not_hidden_by_another_record(self):
        r = complete_resources_fixture()
        r['runs'].append({**r['runs'][0], 'run_id': 'missing-time', 'score_seconds': None})
        self.assertEqual(self.assess(r)['status'], 'manual')

    def test_explicit_multi_seed_estimate(self):
        r = complete_resources_fixture(); r['runs'] = []
        r['estimate'] = {**self.multi(28800)['runs'][0], 'basis': 'Existing protocol and logs'}
        self.assertEqual(self.assess(r)['status'], 'pass')
        r['estimate']['score_seconds'] = 28801
        self.assertEqual(self.assess(r)['status'], 'fail')

    def test_seed_list_must_be_actual_distinct_values(self):
        for seeds in ([], [1, 1], [True, 2], [None, 2], 'five', [1, '1']):
            r = self.multi(24000); r['runs'][0]['evaluation_seeds'] = seeds
            with self.subTest(seeds=seeds), self.assertRaises(ValueError):
                self.assess(r)

    def test_one_seed_list_still_has_two_hour_limit(self):
        self.assertEqual(self.assess(self.multi(7201, seeds=(1,)))['status'], 'fail')

    def test_separate_baseline_reference_totals_are_not_added(self):
        actual = self.assess(self.formal([4000]*5))
        self.assertEqual(actual['status'], 'pass')
        self.assertEqual([t['score_seconds'] for t in actual['formal_seed_totals']], [20000, 20000])
        self.assertEqual(actual['estimate']['score_seconds'], 20000)
        self.assertEqual(actual['estimate']['cpu_cores'], 1)

    def test_formal_total_keeps_existing_gpu_metadata_and_peak_counts(self):
        r = self.formal([4000]*5)
        for row in r['runs']:
            row.update(gpu_count=1, gpu_type='H20', cpu_cores=1)
        r['hardware_review'].update(task_type='gpu', score_comparability='same_hardware')
        cfg = {'environment': {'gpus': 1, 'gpu_types': ['H20'], 'cpus': 1},
               'verifier': {'environment_mode': 'separate',
                            'environment': {'gpus': 1, 'gpu_types': ['H20'], 'cpus': 1}}}
        files = [p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file()]
        actual = rr.apply_review(rr.collect(self.root, files, config=cfg), r, self.root, qa.review_evidence)
        self.assertEqual(actual['status'], 'pass', actual['gaps'])
        self.assertEqual(actual['estimate']['gpu_type'], 'H20')
        self.assertEqual(actual['estimate']['gpu_count'], 1)
        self.assertEqual(actual['estimate']['cpu_cores'], 1)
        self.assertEqual(actual['estimate']['score_seconds'], 20000)

    def test_complete_seed_total_can_fail_when_each_seed_passes(self):
        actual = self.assess(self.formal([6000]*5))
        self.assertEqual(actual['status'], 'fail')
        self.assertTrue(any('30000' in p and '28800' in p for p in actual['problems']))

    def test_formal_total_boundary(self):
        self.assertEqual(self.assess(self.formal([5760]*5))['status'], 'pass')
        actual = self.assess(self.formal([5760]*4+[5761]))
        self.assertEqual(actual['status'], 'fail')

    def test_per_seed_overrun_is_not_hidden_by_multi_seed_total(self):
        actual = self.assess(self.formal([7500, 1000]))
        self.assertEqual(actual['status'], 'fail')
        self.assertTrue(any('7200' in p for p in actual['problems']))

    def test_per_seed_record_cannot_be_relabelled_multi_seed(self):
        r = self.formal([4000]*5)
        r['runs'][0]['evaluation_seeds'] = [1, 2, 3, 4, 5]
        with self.assertRaises(ValueError):
            self.assess(r)

    def test_retries_are_not_summed_into_a_fake_complete_protocol(self):
        r = self.formal([4000]*5)
        r['runs'].append(copy.deepcopy(r['runs'][0]))
        actual = self.assess(r)
        self.assertEqual(len(actual['formal_seed_totals']), 2)
        self.assertEqual([t['score_seconds'] for t in actual['formal_seed_totals']], [20000, 20000])

    def test_duplicate_observation_cannot_hide_cumulative_overrun(self):
        r = self.formal([7000]*5)
        r['runs'].append(copy.deepcopy(r['runs'][0]))
        actual = self.assess(r)
        self.assertEqual(actual['status'], 'fail')
        self.assertEqual([t['score_seconds'] for t in actual['formal_seed_totals']], [35000, 35000])

    def test_conflicting_retries_do_not_silently_pass(self):
        r = self.formal([4000]*5)
        r['runs'].append({**r['runs'][0], 'score_seconds': 5000})
        actual = self.assess(r)
        self.assertEqual(actual['status'], 'manual')
        self.assertIsNone(actual['formal_seed_totals'][0]['score_seconds'])

    def estimated_formal(self, runs, seconds):
        runs['estimate'] = {**self.multi(seconds)['runs'][0], 'basis': 'Existing complete seed protocol and logs'}
        return runs

    def test_unknown_duplicate_order_cannot_hide_known_overrun(self):
        for first in (True, False):
            with self.subTest(null_first=first):
                r = self.estimated_formal(self.formal([7000]*5, roles=('baseline',)), 28000)
                unknown = {**r['runs'][0], 'score_seconds': None}
                r['runs'].insert(0 if first else len(r['runs']), unknown)
                actual = self.assess(r)
                self.assertEqual(actual['status'], 'fail')
                self.assertEqual(actual['formal_seed_totals'][0]['score_seconds'], 35000)

    def test_unknown_duplicate_does_not_invent_conflict_with_known_time(self):
        r = self.estimated_formal(self.formal([4000]*5, roles=('baseline',)), 20000)
        r['runs'].insert(0, {**r['runs'][0], 'score_seconds': None})
        actual = self.assess(r)
        self.assertEqual(actual['status'], 'pass')
        self.assertEqual(actual['formal_seed_totals'][0]['timing_conflicts'], [])

    def test_conflict_reconciliation_cannot_erase_proven_cumulative_overrun(self):
        for first in (True, False):
            with self.subTest(conflict_first=first):
                r = self.estimated_formal(self.formal([7000]*5, roles=('baseline',)), 28000)
                r['runs'].insert(0 if first else len(r['runs']), {**r['runs'][0], 'score_seconds': 6000})
                r['estimate']['observation_reconciliation'] = {
                    'summary': 'Synthetic duplicate observations reviewed; retain their measured alternatives',
                    'evidence': ['instruction.md']}
                actual = self.assess(r)
                self.assertEqual(actual['status'], 'fail')
                self.assertIsNone(actual['formal_seed_totals'][0]['score_seconds'])
                self.assertEqual(actual['formal_seed_totals'][0]['score_seconds_lower_bound'], 34000)
                self.assertTrue(any('34000' in p and '28800' in p for p in actual['problems']))

    def test_conflict_within_budget_keeps_existing_reconciliation_path(self):
        r = self.estimated_formal(self.formal([4000]*5, roles=('baseline',)), 21000)
        r['runs'].append({**r['runs'][0], 'score_seconds': 5000})
        r['estimate']['observation_reconciliation'] = {
            'summary': 'Synthetic known alternatives are both within the supported complete estimate',
            'evidence': ['instruction.md']}
        actual = self.assess(r)
        self.assertEqual(actual['status'], 'pass')
        self.assertEqual(actual['formal_seed_totals'][0]['score_seconds_lower_bound'], 20000)

    def test_unknown_seed_count_does_not_implicitly_get_eight_hours(self):
        r = complete_resources_fixture(); r['runs'][0]['score_seconds'] = 24000
        self.assertEqual(self.assess(r)['status'], 'fail')

    def test_agent_wallclock_is_not_a_multi_seed_score(self):
        r = self.multi(36000); r['runs'][0]['scope'] = 'agent_run'
        actual = self.assess(r)
        self.assertEqual(actual['problems'], [])
        self.assertEqual(actual['status'], 'manual')

    def test_cpu_gpu_limits_are_not_relaxed(self):
        r = self.multi(24000); r['runs'][0]['cpu_cores'] = 65
        self.assertEqual(self.assess(r)['status'], 'fail')
        r = self.multi(24000); r['runs'][0]['gpu_count'] = 9
        self.assertEqual(self.assess(r)['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
