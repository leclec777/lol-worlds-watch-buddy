"""Persistent match discussions, legacy rooms and backup integrity."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server as n


class DiscussionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = n.Store(self.temp.name)
        self.fields = dict(team_a='T1', team_b='BLG', stage='测试赛', format='BO3',
                           starts_at='2099-10-28T20:00:00+08:00', odds_a=185, odds_b=210)
        self.store.mutate('create_match', self.fields)
        self.mid = self.store.get()['matches'][0]['id']
        self.store.mutate('settle_match', {'match_id': self.mid, 'winner': 'a'})

    def post(self, player='p1', text='这场团战很精彩！', request_id=None):
        return self.store.mutate('add_comment', dict(match_id=self.mid, player_id=player,
                                                    text=text, request_id=request_id or n.uid()))

    def save(self, state):
        with self.store.connect() as db:
            db.execute('UPDATE room SET content=? WHERE id=1', (json.dumps(state),))

    def test_two_players_leave_persistent_comments_without_changing_points(self):
        before = self.store.get()
        self.post(text='  支持主队！\n最后一波好看。  ')
        response = self.post(player='p2', text='下场继续！')
        restored = n.Store(self.temp.name).get()
        self.assertEqual(len(response['comments']), 2)
        self.assertEqual(restored['comments'][0]['text'], '支持主队！\n最后一波好看。')
        self.assertEqual([c['player_id'] for c in restored['comments']], ['p1', 'p2'])
        self.assertEqual(restored['comments'][0]['result'], 'a')
        self.assertEqual(restored['matches'], before['matches'])
        self.assertEqual(restored['bets'], before['bets'])
        for player in ('p1', 'p2'):
            self.assertEqual(n.player_stats(restored, player), n.player_stats(before, player))

    def test_legacy_room_migrates_without_changing_ledger_or_revision(self):
        old = self.store.get()
        old.pop('comments')
        self.save(old)
        migrated = n.Store(self.temp.name).get()
        self.assertEqual(migrated, dict(old, comments=[]))
        self.post()
        self.assertEqual(len(self.store.get()['comments']), 1)

    def test_unconfirmed_results_reject_comments_atomically(self):
        self.store.mutate('undo_settlement', {'match_id': self.mid})
        for opened in (False, True):
            if opened:
                self.store.mutate('toggle_lock', {'match_id': self.mid})
            before = self.store.get()
            with self.assertRaises(n.RuleError):
                self.post()
            self.assertEqual(self.store.get(), before)

    def test_cancelled_match_has_a_discussion(self):
        self.store.mutate('undo_settlement', {'match_id': self.mid})
        self.store.mutate('void_match', {'match_id': self.mid})
        self.post()
        self.assertEqual(self.store.get()['comments'][0]['result'], 'void')

    def test_result_correction_keeps_original_comment_context(self):
        self.post()
        self.store.mutate('undo_settlement', {'match_id': self.mid})
        with self.assertRaises(n.RuleError):
            self.post()
        self.store.mutate('settle_match', {'match_id': self.mid, 'winner': 'b'})
        self.post(player='p2')
        self.assertEqual([c['result'] for c in self.store.get()['comments']], ['a', 'b'])

    def test_invalid_text_is_rejected_without_writes(self):
        for text in ('', ' \n\t', '字' * 501, None, 12, True, {}):
            before = self.store.get()
            with self.subTest(text=repr(text)[:40]), self.assertRaises(n.RuleError):
                self.post(text=text)
            self.assertEqual(self.store.get(), before)
        self.post(text='字' * 500)

    def test_unknown_match_or_player_is_rejected(self):
        before = self.store.get()
        for values in ({'player_id': 'p3', 'match_id': self.mid}, {'player_id': 'p1', 'match_id': 'missing'}):
            with self.assertRaises(n.RuleError):
                self.store.mutate('add_comment', dict(values, text='hello', request_id=n.uid()))
            self.assertEqual(self.store.get(), before)

    def test_retries_and_concurrent_submissions_do_not_duplicate_comments(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda _: self.post(request_id='same-request'), range(4)))
        self.assertEqual(len(self.store.get()['comments']), 1)

    def test_only_current_authors_own_comment_can_be_withdrawn(self):
        self.post()
        before = self.store.get()
        cid = before['comments'][0]['id']
        with self.assertRaises(n.RuleError):
            self.store.mutate('delete_comment', {'comment_id': cid, 'player_id': 'p2'})
        self.assertEqual(self.store.get(), before)
        self.store.mutate('delete_comment', {'comment_id': cid, 'player_id': 'p1'})
        self.assertEqual(self.store.get()['comments'], [])

    def test_retry_after_withdrawal_does_not_resurrect_comment(self):
        self.post(request_id='once')
        cid = self.store.get()['comments'][0]['id']
        self.store.mutate('delete_comment', {'comment_id': cid, 'player_id': 'p1'})
        self.post(request_id='once')
        self.assertEqual(self.store.get()['comments'], [])

    def test_limits_reject_additional_comments_atomically(self):
        self.post()
        for constant in ('MAX_COMMENTS', 'MAX_MATCH_COMMENTS'):
            before = self.store.get()
            with mock.patch.object(n, constant, 1), self.assertRaises(n.RuleError):
                self.post()
            self.assertEqual(self.store.get(), before)

    def test_backup_roundtrip_preserves_comments_and_historical_result(self):
        self.post()
        self.store.mutate('undo_settlement', {'match_id': self.mid})
        backup = self.store.get()
        self.store.mutate('reset_season', {'confirmation': 'RESET', 'initial_points': 1000})
        self.assertEqual(self.store.get()['comments'], [])
        self.store.mutate('import_backup', {'backup': backup})
        self.assertEqual(self.store.get()['comments'], backup['comments'])

    def test_legacy_backup_without_comments_still_restores(self):
        backup = self.store.get()
        backup.pop('comments')
        self.post()
        self.store.mutate('import_backup', {'backup': backup})
        self.assertEqual(self.store.get()['comments'], [])

    def test_corrupt_comments_in_backup_are_rejected_atomically(self):
        self.post()
        before = self.store.get()
        comment = before['comments'][0]
        variants = [None, {}, [comment, comment]]
        for field, value in [('match_id', 'missing'), ('player_id', 'p3'), ('text', ''),
                             ('text', '字' * 501), ('created_at', 'invalid'), ('result', 'pending')]:
            variants.append([dict(comment, **{field: value})])
        for comments in variants:
            backup = copy.deepcopy(before)
            backup['comments'] = comments
            with self.assertRaises(n.RuleError):
                self.store.mutate('import_backup', {'backup': backup})
            self.assertEqual(self.store.get(), before)

    def test_comments_prevent_relabeling_and_removal_of_match(self):
        self.post()
        self.store.mutate('undo_settlement', {'match_id': self.mid})
        with self.assertRaises(n.RuleError):
            self.store.mutate('edit_match', dict(self.fields, match_id=self.mid, team_a='OTHER'))
        state = self.store.get()
        state['matches'][0]['demo'] = True
        self.save(state)
        self.store.mutate('clear_examples', {})
        self.assertEqual(len(self.store.get()['matches']), 1)
        self.assertEqual(len(self.store.get()['comments']), 1)

    def test_sync_cannot_relabel_a_match_with_discussion_history(self):
        self.post()
        self.store.mutate('undo_settlement', {'match_id': self.mid})
        state = self.store.get()
        state['matches'][0].update(source_id='official-1', source_url='https://lpl.qq.com/')
        self.save(state)
        official = dict(self.fields, source_id='official-1', team_a='OTHER')
        result = self.store.mutate('sync_schedule', {'date': '2099-10-28', 'source_ids': ['official-1']},
                                   schedule={'date': '2099-10-28', 'matches': [official]})
        self.assertEqual(result['sync_result']['skipped'], 1)
        self.assertEqual(self.store.get()['matches'][0]['team_a'], 'T1')


if __name__ == '__main__':
    unittest.main()
