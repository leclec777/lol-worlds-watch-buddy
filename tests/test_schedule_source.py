"""Official LPL feed parsing, tested with a saved public feed fixture; no network."""
import copy
import json
import sys
import unittest
from datetime import timedelta, timezone, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lpl_schedule as lpl


class OfficialSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = Path(__file__).resolve().parent / 'fixtures/lpl-confirmed-and-tbd.json'
        cls.document = json.loads(fixture.read_text(encoding='utf-8'))

    def setUp(self):
        self.doc = copy.deepcopy(self.document)

    def normalize(self, date='2026-10-24'):
        return lpl.normalize_schedule(self.doc, date)

    def assert_source_error(self, date, code, status=400):
        with self.assertRaises(lpl.ScheduleError) as caught:
            self.normalize(date)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.http_status, status)

    def test_official_string_success_status_and_eight_confirmed_matches(self):
        self.assertEqual(self.doc['status'], '0')
        result = self.normalize()
        self.assertEqual(len(result['matches']), 8)
        self.assertEqual(result['timezone'], 'Asia/Shanghai')
        self.assertEqual(result['source_url'], 'https://lpl.qq.com/')
        self.assertEqual(result['source_updated_at'], '2026-10-21 00:00:07')
        self.assertEqual(result['matches'][0]['source_id'], '13621')

    def test_blank_short_names_fall_back_to_official_match_name(self):
        self.assertEqual(self.doc['msg'][0]['TeamShortNameA'], '')
        first = self.normalize()['matches'][0]
        self.assertEqual((first['team_a'], first['team_b']), ('GEN', 'IG'))
        last = self.normalize()['matches'][-1]
        self.assertEqual((last['team_a'], last['team_b']), ('TSW', 'LYON'))

    def test_china_timezone_keeps_official_date_and_exact_instant(self):
        start = self.normalize()['matches'][0]['starts_at']
        self.assertEqual(start, '2026-10-24T01:00:00+08:00')
        parsed = datetime.fromisoformat(start)
        self.assertEqual(parsed.utcoffset(), timedelta(hours=8))
        self.assertEqual(parsed.astimezone(timezone.utc).isoformat(), '2026-10-23T17:00:00+00:00')

    def test_invalid_dates_are_request_errors(self):
        for value in (None, '', '2026-02-30', '2026-2-03', '2026/10/24', '2026-10-24x', '../2026-10-24'):
            with self.subTest(value=value):
                with self.assertRaises(lpl.ScheduleError) as caught:
                    lpl.validate_date(value)
                self.assertEqual(caught.exception.code, 'INVALID_DATE')
                self.assertEqual(caught.exception.http_status, 400)

    def test_unpublished_day_returns_no_schedule_error(self):
        self.assert_source_error('2026-10-21', 'NO_SCHEDULE')

    def test_time_only_tbd_day_returns_no_confirmed_matches_error(self):
        self.assert_source_error('2026-10-25', 'NO_CONFIRMED_MATCHES')

    def test_pending_zero_or_nonzero_scores_are_not_results(self):
        self.doc['msg'][0].update(ScoreA='9', ScoreB='8', MatchWin='1')
        result = self.normalize()
        first = result['matches'][0]
        self.assertEqual(first['source_status'], 'upcoming')
        self.assertIsNone(first['score_a'])
        self.assertIsNone(first['score_b'])
        for match in result['matches']:
            self.assertIsNone(match['odds_a'])
            self.assertIsNone(match['odds_b'])
            self.assertNotIn('winner', match)

    def test_ongoing_and_finished_scores_are_source_metadata_only(self):
        self.doc['msg'][0].update(MatchStatus='2', ScoreA='1', ScoreB='0')
        self.doc['msg'][1].update(MatchStatus='3', ScoreA='0', ScoreB='1')
        first, second = self.normalize()['matches'][:2]
        self.assertEqual((first['source_status'], first['score_a'], first['score_b']), ('ongoing', 1, 0))
        self.assertEqual((second['source_status'], second['score_a'], second['score_b']), ('finished', 0, 1))
        self.assertNotIn('winner', first)
        self.assertNotIn('winner', second)

    def test_bo2_is_skipped_with_explicit_warning(self):
        row = copy.deepcopy(self.doc['msg'][0])
        row.update(bMatchId='bo2-test', GameModeName='BO2')
        self.doc['msg'].append(row)
        result = self.normalize()
        self.assertEqual(len(result['matches']), 8)
        self.assertNotIn('bo2-test', [m['source_id'] for m in result['matches']])
        self.assertTrue(any('BO2' in warning for warning in result['warnings']))

    def test_bo2_only_day_cannot_be_used_for_winner_prediction(self):
        row = self.doc['msg'][0]
        row['GameModeName'] = 'BO2'
        self.doc['msg'] = [row]
        self.assert_source_error('2026-10-24', 'UNSUPPORTED_FORMAT')

    def test_missing_unknown_format_stays_unconfirmed(self):
        row = self.doc['msg'][0]
        row.update(GameModeName='', GameMode='999')
        self.doc['msg'] = [row]
        self.assertEqual(self.normalize()['matches'][0]['format'], '待确认')

    def test_lpl_and_msi_are_kept_while_tft_is_ignored(self):
        # Official bGameId identifies tournament families, not different games:
        # 1 = international series, 5 = LPL, 8 = MSI. Only isTft marks TFT.
        row = copy.deepcopy(self.doc['msg'][0])
        row.update(bMatchId='tft-test', isTft='1', bGameId='5')
        lpl_row = copy.deepcopy(self.doc['msg'][0])
        lpl_row.update(bMatchId='lpl-test', bGameId='5', GameName='LPL测试赛程')
        msi_row = copy.deepcopy(self.doc['msg'][0])
        msi_row.update(bMatchId='msi-test', bGameId='8', GameName='MSI测试赛程')
        self.doc['msg'].extend([row, lpl_row, msi_row])
        matches = self.normalize()['matches']
        self.assertEqual(len(matches), 10)
        ids = {match['source_id'] for match in matches}
        self.assertIn('lpl-test', ids)
        self.assertIn('msi-test', ids)
        self.assertNotIn('tft-test', ids)

    def test_duplicate_official_match_id_is_not_imported_twice(self):
        self.doc['msg'].append(copy.deepcopy(self.doc['msg'][0]))
        self.assertEqual(len(self.normalize()['matches']), 8)

    def test_invalid_document_is_an_upstream_error(self):
        for value in ([], {}, {'status': '1', 'msg': []}, {'status': '0', 'msg': {}}):
            with self.subTest(value=value):
                with self.assertRaises(lpl.ScheduleError) as caught:
                    lpl.normalize_schedule(value, '2026-10-24')
                self.assertEqual(caught.exception.code, 'SOURCE_FORMAT_CHANGED')
                self.assertEqual(caught.exception.http_status, 502)

    def test_malformed_time_is_not_silently_imported(self):
        self.doc['msg'][0]['MatchDate'] = '2026-10-24 invalid'
        result = self.normalize()
        self.assertEqual(len(result['matches']), 7)
        self.assertTrue(any('时间' in warning for warning in result['warnings']))

    def test_tbd_team_identifier_wins_over_apparently_real_name(self):
        row = self.doc['msg'][0]
        row.update(TeamA='297', bMatchName='T1 vs BLG')
        self.doc['msg'] = [row]
        self.assert_source_error('2026-10-24', 'NO_CONFIRMED_MATCHES')


if __name__ == '__main__':
    unittest.main(verbosity=2)
