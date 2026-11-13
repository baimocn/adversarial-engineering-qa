import copy
import unittest

import audit_legacy_task as legacy
import audit_format_repair as format_review
import test_audit_standard_with_waivers as fixtures


class UnknownDirectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.StandardWaiverTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.overview = copy.deepcopy(self.fixture.lr['overview'])

    def test_legacy_strict_input_still_rejects_an_unknown_direction(self):
        self.overview['baseline_reference']['direction'] = None
        with self.assertRaises(format_review.ReviewError):
            legacy.validate_overview(self.fixture.root, self.overview)

    def test_automatic_missing_direction_remains_unknown_not_invented(self):
        self.overview['baseline_reference']['direction'] = None
        result = legacy.validate_overview(self.fixture.root, self.overview, allow_unknown_direction=True)
        self.assertIsNone(result['baseline_reference']['direction'])
        self.assertEqual(result['baseline_reference']['paired_runs'], self.overview['baseline_reference']['paired_runs'])

    def test_automatic_mode_does_not_accept_an_arbitrary_direction(self):
        self.overview['baseline_reference']['direction'] = 'anything'
        with self.assertRaises(format_review.ReviewError):
            legacy.validate_overview(self.fixture.root, self.overview, allow_unknown_direction=True)


if __name__ == '__main__':
    unittest.main()
