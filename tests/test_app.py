"""Deterministic ledger and schedule tests; all match data here is test-only."""
import copy
import importlib.util
import json
import tempfile
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'server.py'
sys.path.insert(0, str(APP.parent))
spec = importlib.util.spec_from_file_location('nexus', APP)
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = n.Store(self.temp.name)
        # These are explicit test fixtures, never the application's live seed data.
        room = self.store.get()
        room.update(matches=[], bets=[], activity=[], requests=[])
        for i, (a, b, oa, ob) in enumerate([
            ('T1', 'BLG', 185, 195), ('GEN', 'HLE', 160, 235),
            ('G2', 'TES', 220, 170), ('WBG', 'DK', 190, 190)
        ]):
            room['matches'].append({
                'id': 'fixture-' + str(i), 'team_a': a, 'team_b': b,
                'stage': '测试对局', 'format': 'BO3', 'starts_at': '2099-10-24T18:00:00+08:00',
                'odds_a': oa, 'odds_b': ob, 'status': 'open', 'winner': None,
                'demo': True, 'created_at': n.now()
            })
        with self.store.connect() as db:
            db.execute('UPDATE room SET content=? WHERE id=1', (json.dumps(room),))
        self.match_id = 'fixture-0'

    def tearDown(self):
        self.temp.cleanup()

    def act(self, action, **kwargs):
        return self.store.mutate(action, kwargs)

    def bet(self, player='p1', stake=100, side='a', match_id=None, request_id=None):
        return self.act('place_bet', player_id=player, stake=stake, side=side,
                        match_id=match_id or self.match_id,
                        expected_odds=185 if side == 'a' else 195,
                        request_id=request_id or n.uid())

    def stats(self, player='p1'):
        return n.player_stats(self.store.get(), player)

    def test_initial_balance(self):
        self.assertEqual(self.stats()['balance'], 1000)

    def test_stake_locks_balance_and_preserves_assets(self):
        self.bet()
        self.assertEqual(self.stats()['balance'], 900)
        self.assertEqual(self.stats()['locked'], 100)
        self.assertEqual(self.stats()['assets'], 1000)

    def test_win_loss_and_double_settlement(self):
        self.bet()
        self.bet(player='p2', stake=200, side='b')
        self.act('settle_match', match_id=self.match_id, winner='a')
        self.assertEqual(self.stats()['balance'], 1085)
        self.assertEqual(self.stats()['profit'], 85)
        self.assertEqual(self.stats('p2')['balance'], 800)
        self.assertEqual(self.stats('p2')['losses'], 1)
        with self.assertRaises(n.RuleError):
            self.act('settle_match', match_id=self.match_id, winner='b')
        self.assertEqual(self.stats()['balance'], 1085)

    def test_odds_update_does_not_change_locked_odds(self):
        self.bet()
        m = self.store.get()['matches'][0]
        m['odds_a'] = 250
        self.act('edit_match', match_id=m['id'], **{k:m[k] for k in ('team_a','team_b','stage','format','starts_at','odds_a','odds_b')})
        self.act('settle_match', match_id=m['id'], winner='a')
        self.assertEqual(self.stats()['balance'], 1085)

    def test_stale_odds_rejected(self):
        with self.assertRaises(n.RuleError):
            self.act('place_bet', player_id='p1', stake=100, side='a', match_id=self.match_id,
                     expected_odds=250, request_id=n.uid())
        self.assertEqual(self.stats()['balance'], 1000)

    def test_balance_stake_bounds(self):
        for bad in (0, -1, 1001, 1.5, True, '100'):
            with self.assertRaises(n.RuleError):
                self.bet(stake=bad)
        self.assertEqual(self.stats()['balance'], 1000)

    def test_idempotent_submission(self):
        self.bet(request_id='test-once')
        self.bet(request_id='test-once')
        self.assertEqual(len(self.store.get()['bets']), 1)
        self.assertEqual(self.stats()['balance'], 900)

    def test_one_bet_per_player_per_match(self):
        self.bet()
        with self.assertRaises(n.RuleError):
            self.bet(side='b')
        self.bet(player='p2', side='a')
        self.assertEqual(len(self.store.get()['bets']), 2)

    def test_cancel_refunds_and_allows_replacement(self):
        self.bet()
        bid = self.store.get()['bets'][0]['id']
        self.act('cancel_bet', bet_id=bid)
        self.assertEqual(self.stats()['balance'], 1000)
        self.bet(side='b')
        self.assertEqual(self.stats()['balance'], 900)

    def test_void_refunds_and_no_win_loss(self):
        self.bet()
        self.bet(player='p2', stake=250, side='b')
        self.act('void_match', match_id=self.match_id)
        self.assertEqual(self.stats()['balance'], 1000)
        self.assertEqual(self.stats('p2')['balance'], 1000)
        self.assertEqual(self.stats()['wins'], 0)
        self.assertEqual(self.stats()['locked'], 0)

    def test_lock_stops_bets_and_cancellations(self):
        self.bet()
        self.act('toggle_lock', match_id=self.match_id)
        with self.assertRaises(n.RuleError):
            self.bet(player='p2')
        with self.assertRaises(n.RuleError):
            self.act('cancel_bet', bet_id=self.store.get()['bets'][0]['id'])

    def test_past_start_automatically_closes(self):
        m = self.store.get()['matches'][0]
        m['starts_at'] = '2020-01-01T00:00:00+00:00'
        self.act('edit_match', match_id=m['id'], **{k:m[k] for k in ('team_a','team_b','stage','format','starts_at','odds_a','odds_b')})
        with self.assertRaises(n.RuleError):
            self.bet()

    def test_undo_and_correct_result(self):
        self.bet()
        self.act('settle_match', match_id=self.match_id, winner='a')
        self.act('undo_settlement', match_id=self.match_id)
        self.assertEqual(self.stats()['balance'], 900)
        self.assertEqual(self.stats()['locked'], 100)
        self.assertEqual(self.store.get()['matches'][0]['status'], 'locked')
        self.act('settle_match', match_id=self.match_id, winner='b')
        self.assertEqual(self.stats()['balance'], 900)
        self.assertEqual(self.stats()['losses'], 1)

    def test_undo_cannot_make_balance_negative(self):
        self.bet(stake=1000)
        self.act('settle_match', match_id=self.match_id, winner='a')
        other = self.store.get()['matches'][1]
        self.act('place_bet', player_id='p1', stake=1850, side='a', match_id=other['id'],
                 expected_odds=other['odds_a'], request_id=n.uid())
        with self.assertRaises(n.RuleError):
            self.act('undo_settlement', match_id=self.match_id)
        self.assertEqual(self.stats()['balance'], 0)
        self.assertEqual(self.store.get()['matches'][0]['status'], 'settled')

    def test_rounding(self):
        self.assertEqual(n.payout(10,185), 19)
        self.assertEqual(n.payout(1,149), 1)
        self.assertEqual(n.payout(1,150), 2)

    def test_persistence(self):
        self.bet()
        reopened = n.Store(self.temp.name)
        self.assertEqual(n.player_stats(reopened.get(),'p1')['balance'], 900)

    def test_transaction_rollback_on_invalid_settings(self):
        old = self.store.get()
        with self.assertRaises(n.RuleError):
            self.act('settings', room_name='changed', p1={'name':'same'}, p2={'name':'same'})
        self.assertEqual(self.store.get(), old)

    def test_backup_roundtrip(self):
        self.bet()
        self.bet(player='p2', side='b')
        self.act('settle_match', match_id=self.match_id, winner='a')
        backup = self.store.get()
        self.act('reset_season', confirmation='RESET', initial_points=5000)
        self.act('import_backup', backup=backup)
        self.assertEqual(self.stats()['balance'], 1085)
        self.assertEqual(self.stats('p2')['balance'], 900)
        self.assertEqual(self.store.get()['room']['initial_points'], 1000)

    def test_corrupt_backup_is_rejected_atomically(self):
        self.bet()
        raw = self.store.get()
        for corrupt in (None, {}, {'version':1}, [], dict(raw,players=[])):
            with self.assertRaises(n.RuleError):
                self.act('import_backup', backup=corrupt)
            self.assertEqual(self.store.get(), raw)
        corrupt=copy.deepcopy(raw)
        corrupt['bets'][0]['payout']=9999
        with self.assertRaises(n.RuleError):
            self.act('import_backup', backup=corrupt)
        self.assertEqual(self.store.get(), raw)

    def test_concurrent_spend_and_duplicate_protection(self):
        def place(i):
            try:
                return self.bet(stake=700, request_id='concurrent-'+str(i))
            except n.RuleError:
                return None
        with ThreadPoolExecutor(max_workers=6) as executor:
            results=list(executor.map(place, range(6)))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(self.stats()['balance'],300)

    def test_clear_examples_preserves_bet_history(self):
        self.bet()
        self.act('clear_examples')
        self.assertEqual(len(self.store.get()['matches']),1)

    def test_reset_requires_exact_confirmation(self):
        with self.assertRaises(n.RuleError):
            self.act('reset_season', confirmation='reset', initial_points=1000)
        self.assertEqual(len(self.store.get()['matches']),4)

    def test_history_teams_cannot_change_even_after_withdrawal(self):
        self.bet()
        self.act('cancel_bet',bet_id=self.store.get()['bets'][0]['id'])
        m=self.store.get()['matches'][0]
        m['team_a']='OTHER'
        with self.assertRaises(n.RuleError):
            self.act('edit_match',match_id=m['id'],**{k:m[k] for k in ('team_a','team_b','stage','format','starts_at','odds_a','odds_b')})


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = n.Store(self.temp.name)
        room = self.store.get()
        room.update(matches=[], bets=[], activity=[], requests=[])
        with self.store.connect() as db:
            db.execute('UPDATE room SET content=? WHERE id=1', (json.dumps(room),))
        self.schedule = {
            'date': '2099-10-24', 'source_url': 'https://lpl.qq.com/',
            'matches': [{
                'source_id': '123', 'team_a': 'T1', 'team_b': 'BLG',
                'stage': '全球总决赛 · 瑞士轮', 'format': 'BO1',
                'starts_at': '2099-10-24T18:00:00+08:00',
                'source_status': 'upcoming', 'score_a': None, 'score_b': None
            }]
        }

    def tearDown(self):
        self.temp.cleanup()

    def sync(self, ids=None, schedule=None):
        data = schedule or self.schedule
        return self.store.mutate('sync_schedule', {
            'date': data['date'], 'source_ids': ['123'] if ids is None else ids
        }, schedule=data)

    def edit(self, match, **changes):
        fields = {k: match[k] for k in ('team_a','team_b','stage','format','starts_at','odds_a','odds_b')}
        fields.update(changes)
        return self.store.mutate('edit_match', dict(fields, match_id=match['id']))

    def bet(self, match, stake=100):
        return self.store.mutate('place_bet', {
            'player_id': 'p1', 'match_id': match['id'], 'side': 'a',
            'stake': stake, 'expected_odds': match['odds_a'], 'request_id': n.uid()
        })

    def first(self):
        return self.store.get()['matches'][0]

    def test_fresh_seed_has_no_invented_schedule(self):
        self.assertEqual(n.seed()['matches'], [])
        self.assertEqual(n.seed()['bets'], [])

    def test_manual_match_can_be_saved_without_odds(self):
        fields = {
            'team_a': '主队', 'team_b': '好友队', 'stage': '友谊赛', 'format': 'BO3',
            'starts_at': '2099-10-24T18:00:00+08:00', 'odds_a': None, 'odds_b': None
        }
        self.store.mutate('create_match', fields)
        self.assertIsNone(self.first()['odds_a'])
        self.assertIsNone(self.first()['odds_b'])
        before = self.store.get()
        with self.assertRaises(n.RuleError):
            self.bet(self.first())
        self.assertEqual(self.store.get(), before)

    def test_only_one_odds_value_is_rejected_atomically(self):
        fields = {
            'team_a': '主队', 'team_b': '好友队', 'stage': '友谊赛', 'format': 'BO3',
            'starts_at': '2099-10-24T18:00:00+08:00', 'odds_a': 185, 'odds_b': None
        }
        before = self.store.get()
        with self.assertRaises(n.RuleError):
            self.store.mutate('create_match', fields)
        self.assertEqual(self.store.get(), before)

    def test_sync_imports_selected_match_with_no_odds_or_result(self):
        response = self.sync()
        match = self.first()
        self.assertEqual(len(self.store.get()['matches']), 1)
        self.assertIsNone(match['odds_a'])
        self.assertIsNone(match['odds_b'])
        self.assertIsNone(match['winner'])
        self.assertEqual(match['source_id'], '123')
        self.assertEqual(match['source_status'], 'upcoming')
        self.assertIn('sync_result', response)
        self.assertEqual(response['sync_result']['added'], 1)

    def test_sync_cannot_bet_until_user_sets_both_odds(self):
        self.sync()
        before = self.store.get()
        with self.assertRaises(n.RuleError):
            self.bet(self.first())
        self.assertEqual(self.store.get(), before)
        self.edit(self.first(), odds_a=210, odds_b=170)
        self.bet(self.first())
        self.assertEqual(n.player_stats(self.store.get(), 'p1')['balance'], 900)

    def test_duplicate_sync_does_not_add_duplicate_or_override_odds(self):
        self.sync()
        self.edit(self.first(), odds_a=210, odds_b=170)
        self.sync()
        self.assertEqual(len(self.store.get()['matches']), 1)
        self.assertEqual(self.first()['odds_a'], 210)
        self.assertEqual(self.first()['odds_b'], 170)

    def test_duplicate_sync_preserves_locked_bet_odds(self):
        self.sync()
        self.edit(self.first(), odds_a=210, odds_b=170)
        self.bet(self.first())
        self.edit(self.first(), odds_a=300, odds_b=140)
        self.sync()
        room = self.store.get()
        self.assertEqual(room['bets'][0]['odds'], 210)
        self.assertEqual(self.first()['odds_a'], 300)
        self.store.mutate('settle_match', {'match_id': self.first()['id'], 'winner': 'a'})
        self.assertEqual(n.player_stats(self.store.get(), 'p1')['balance'], 1110)

    def test_import_selection_does_not_import_other_rows(self):
        schedule = copy.deepcopy(self.schedule)
        second = copy.deepcopy(schedule['matches'][0])
        second.update(source_id='456', team_a='GEN', team_b='HLE')
        schedule['matches'].append(second)
        self.sync(ids=['456'], schedule=schedule)
        self.assertEqual(len(self.store.get()['matches']), 1)
        self.assertEqual(self.first()['source_id'], '456')

    def test_stale_or_unknown_selection_is_rejected_without_writes(self):
        before = self.store.get()
        with self.assertRaises(n.RuleError):
            self.sync(ids=['missing'])
        self.assertEqual(self.store.get(), before)

    def test_empty_selection_is_rejected_without_writes(self):
        before = self.store.get()
        with self.assertRaises(n.RuleError):
            self.sync(ids=[])
        self.assertEqual(self.store.get(), before)

    def test_finished_official_game_does_not_auto_settle(self):
        schedule = copy.deepcopy(self.schedule)
        schedule['matches'][0].update(source_status='finished', score_a=1, score_b=0)
        self.sync(schedule=schedule)
        match = self.first()
        self.assertEqual(match['status'], 'locked')
        self.assertIsNone(match['winner'])
        self.assertEqual(len(self.store.get()['bets']), 0)
        self.assertEqual(n.player_stats(self.store.get(), 'p1')['balance'], 1000)

    def test_unknown_format_requires_user_confirmation_before_betting(self):
        schedule = copy.deepcopy(self.schedule)
        schedule['matches'][0]['format'] = '待确认'
        self.sync(schedule=schedule)
        with self.assertRaises(n.RuleError):
            self.bet(self.first())
        self.edit(self.first(), format='BO3', odds_a=185, odds_b=195)
        self.bet(self.first())
        self.assertEqual(n.player_stats(self.store.get(), 'p1')['balance'], 900)

    def test_unknown_format_is_blocked_even_if_odds_are_present(self):
        schedule = copy.deepcopy(self.schedule)
        schedule['matches'][0]['format'] = '待确认'
        self.sync(schedule=schedule)
        self.edit(self.first(), odds_a=185, odds_b=195)
        before = self.store.get()
        with self.assertRaises(n.RuleError):
            self.bet(self.first())
        self.assertEqual(self.store.get(), before)

    def test_odds_never_come_from_upstream_schedule(self):
        schedule = copy.deepcopy(self.schedule)
        schedule['matches'][0].update(odds_a=999, odds_b=888)
        self.sync(schedule=schedule)
        self.assertIsNone(self.first()['odds_a'])
        self.assertIsNone(self.first()['odds_b'])

    def test_scored_official_update_does_not_settle_existing_prediction(self):
        self.sync()
        self.edit(self.first(), odds_a=185, odds_b=195)
        self.bet(self.first())
        schedule = copy.deepcopy(self.schedule)
        schedule['matches'][0].update(source_status='finished', score_a=1, score_b=0)
        self.sync(schedule=schedule)
        room = self.store.get()
        self.assertEqual(room['bets'][0]['status'], 'pending')
        self.assertEqual(room['bets'][0]['payout'], 0)
        self.assertIsNone(self.first()['winner'])
        self.assertEqual(self.first()['status'], 'locked')
        self.assertEqual(n.player_stats(room, 'p1')['profit'], 0)

    def test_rescheduled_game_does_not_reopen_manual_lock(self):
        self.sync()
        self.edit(self.first(), odds_a=185, odds_b=195)
        self.store.mutate('toggle_lock', {'match_id': self.first()['id']})
        schedule = copy.deepcopy(self.schedule)
        schedule['matches'][0]['starts_at'] = '2099-10-24T20:00:00+08:00'
        self.sync(schedule=schedule)
        self.assertEqual(self.first()['status'], 'locked')

    def test_source_identity_correction_does_not_relabel_existing_bet(self):
        self.sync()
        self.edit(self.first(), odds_a=185, odds_b=195)
        self.bet(self.first())
        schedule = copy.deepcopy(self.schedule)
        schedule['matches'][0]['team_a'] = 'OTHER'
        result = self.sync(schedule=schedule)
        self.assertEqual(self.first()['team_a'], 'T1')
        self.assertEqual(result['sync_result']['skipped'], 1)

    def test_prepared_schedule_must_match_selected_date(self):
        before = self.store.get()
        with self.assertRaises(n.RuleError):
            self.store.mutate('sync_schedule', {
                'date': '2099-10-25', 'source_ids': ['123']
            }, schedule=self.schedule)
        self.assertEqual(self.store.get(), before)

    def test_official_source_and_nullable_odds_backup_roundtrip(self):
        self.sync()
        before = self.first()
        backup = self.store.get()
        self.store.mutate('reset_season', {'confirmation': 'RESET', 'initial_points': 5000})
        self.store.mutate('import_backup', {'backup': backup})
        restored = self.first()
        for key in ('source_id', 'source_url', 'source_status'):
            self.assertEqual(restored[key], before[key])
        self.assertIsNone(restored['odds_a'])
        self.assertIsNone(restored['odds_b'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
