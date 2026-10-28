#!/usr/bin/env python3
"""Nexus Picks: a two-player, local-only prediction room. Python standard library only."""
import argparse
import errno
import copy
import json
import os
import re
import sqlite3
import sys
import time
import uuid
import webbrowser
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from lpl_schedule import ScheduleError, fetch_schedule, validate_date

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
DATA = Path(os.environ.get('NEXUS_DATA_DIR', str(ROOT / 'data')))
MAX_POINTS = 1_000_000
MAX_COMMENTS = 2000
MAX_MATCH_COMMENTS = 200
APP_VERSION = '1.2.0'


class RuleError(Exception):
    pass


def uid():
    return uuid.uuid4().hex[:16]


def now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.timestamp()
    except (ValueError, TypeError, OverflowError):
        raise RuleError('请选择有效的开赛时间。')


def integer(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise RuleError('%s须为 %s–%s 之间的整数。' % (label, low, high))
    return value


def label(value, maximum, field):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise RuleError('%s不能为空，且不能超过 %s 个字符。' % (field, maximum))
    return value.strip()


def payout(stake, odds):
    # Odds use hundredths; integer arithmetic rounds returns to the nearest point.
    return (stake * odds + 50) // 100


def is_open(match):
    return match['status'] == 'open' and timestamp(match['starts_at']) > time.time()


def odds_ready(match):
    return all(type(match.get('odds_' + side)) is int and 101 <= match['odds_' + side] <= 10000
               for side in ('a', 'b')) and match.get('format') in ('BO1', 'BO3', 'BO5')


def add_log(state, message, kind='system'):
    state['activity'].insert(0, {'id': uid(), 'at': now(), 'message': message, 'kind': kind})
    state['activity'] = state['activity'][:400]


def seed():
    state = {'version': 1, 'revision': 1,
             'room': {'name': '我们的世界赛', 'initial_points': 1000},
             'players': [{'id': 'p1', 'name': '我', 'favorite': 'T1'},
                         {'id': 'p2', 'name': '好朋友', 'favorite': 'BLG'}],
             'matches': [], 'bets': [], 'comments': [], 'activity': [], 'requests': []}
    add_log(state, '房间已就绪，每人获得 1,000 初始积分。同步官方赛程后，由你手动设置赔率。')
    return state


def player_stats(state, player_id):
    balance = state['room']['initial_points']
    locked = profit = wins = losses = 0
    for bet in state['bets']:
        if bet['player_id'] != player_id:
            continue
        balance += bet['payout'] - bet['stake']
        if bet['status'] == 'pending':
            locked += bet['stake']
        if bet['status'] in ('won', 'lost'):
            profit += bet['payout'] - bet['stake']
            wins += int(bet['status'] == 'won')
            losses += int(bet['status'] == 'lost')
    return {'balance': balance, 'locked': locked, 'profit': profit,
            'wins': wins, 'losses': losses, 'assets': balance + locked,
            'hit_rate': round(wins / (wins + losses) * 100) if wins + losses else None}


def public_state(state):
    result = copy.deepcopy(state)
    result.setdefault('comments', [])
    result.pop('requests', None)
    result['server_time'] = now()
    result['app_version'] = APP_VERSION
    for player in result['players']:
        player.update(player_stats(state, player['id']))
    return result


def find(items, item_id, description):
    for item in items:
        if item['id'] == item_id:
            return item
    raise RuleError('%s不存在，可能已被另一窗口更新。' % description)


def match_input(payload):
    a = label(payload.get('team_a'), 24, '队伍 A')
    b = label(payload.get('team_b'), 24, '队伍 B')
    if a.casefold() == b.casefold():
        raise RuleError('请选择两支不同的队伍。')
    starts = payload.get('starts_at')
    timestamp(starts)
    fmt = payload.get('format')
    if fmt not in ('BO1', 'BO3', 'BO5', '待确认'):
        raise RuleError('请选择 BO1、BO3 或 BO5。')
    oa, ob = payload.get('odds_a'), payload.get('odds_b')
    if (oa is None) != (ob is None):
        raise RuleError('请同时填写双方赔率，或将双方都留空，稍后再设置。')
    if oa is not None:
        oa = integer(oa, 101, 10000, 'A 方赔率（百分位）')
        ob = integer(ob, 101, 10000, 'B 方赔率（百分位）')
    return {'team_a': a, 'team_b': b, 'stage': label(payload.get('stage'), 48, '赛事阶段'),
            'format': fmt, 'starts_at': starts,
            'odds_a': oa, 'odds_b': ob}


def source_metadata(raw):
    """Whitelist official provenance; backup files cannot introduce fetchable URLs."""
    if not raw.get('source_id'):
        return {}
    source_id = label(raw['source_id'], 80, '官方比赛编号')
    source_url = str(raw.get('source_url') or 'https://lpl.qq.com/')
    parsed = urlparse(source_url)
    if parsed.scheme != 'https' or parsed.hostname != 'lpl.qq.com' or parsed.username or parsed.port:
        raise RuleError('官方赛程来源链接无效。')
    meta = {'source': 'lpl.qq.com', 'source_id': source_id, 'source_url': source_url,
            'source_status': raw.get('source_status', 'unknown')}
    if meta['source_status'] not in ('upcoming', 'ongoing', 'finished', 'unknown'):
        raise RuleError('官方赛程状态无效。')
    if raw.get('source_date'):
        try:
            meta['source_date'] = validate_date(raw['source_date'])
        except ScheduleError as error:
            raise RuleError(str(error))
    if raw.get('last_synced_at'):
        timestamp(raw['last_synced_at'])
        meta['last_synced_at'] = raw['last_synced_at']
    for key in ('source_score_a', 'source_score_b'):
        if raw.get(key) is not None:
            meta[key] = integer(raw[key], 0, 99, '官方比分')
        else:
            meta[key] = None
    return meta


def sync_into_state(state, payload, schedule):
    if not isinstance(schedule, dict) or schedule.get('date') != payload.get('date'):
        raise RuleError('请先选择日期并预览官方赛程。')
    ids = payload.get('source_ids')
    if not isinstance(ids, list) or not 1 <= len(ids) <= 100 or any(not isinstance(i, str) for i in ids):
        raise RuleError('请选择 1–100 场官方比赛。')
    ids = list(dict.fromkeys(ids))
    available = {m['source_id']: m for m in schedule['matches']}
    if any(i not in available for i in ids):
        raise RuleError('所选对阵已发生变化或尚未公布，请重新预览赛程。')
    existing = {m['source_id']: m for m in state['matches'] if m.get('source_id')}
    if len(state['matches']) + sum(i not in existing for i in ids) > 1000:
        raise RuleError('当前最多支持 1,000 场比赛，请备份后开启新赛季。')
    added = updated = skipped = 0
    for source_id in ids:
        official = available[source_id]
        fields = match_input(dict(official, odds_a=None, odds_b=None))
        metadata = source_metadata(dict(source='lpl.qq.com', source_id=source_id,
            source_url=schedule.get('source_url', 'https://lpl.qq.com/'), source_date=schedule['date'],
            source_status=official.get('source_status', 'unknown'), last_synced_at=now(),
            source_score_a=official.get('score_a'), source_score_b=official.get('score_b')))
        if source_id in existing:
            match = existing[source_id]
            if match['status'] in ('settled', 'void'):
                skipped += 1
                continue
            has_history = any(b['match_id'] == match['id'] for b in state['bets'] + state.get('comments', []))
            if has_history and any(fields[k] != match[k] for k in ('team_a', 'team_b', 'format', 'stage')):
                skipped += 1
                continue
            # Never reopen a previously closed market because of a changed official time.
            keep_locked = not is_open(match) or official.get('source_status') in ('ongoing', 'finished')
            for key in ('team_a', 'team_b', 'format', 'stage', 'starts_at'):
                match[key] = fields[key]
            match.update(metadata)
            if keep_locked:
                match['status'] = 'locked'
            updated += 1
        else:
            status = 'locked' if timestamp(fields['starts_at']) <= time.time() or official.get('source_status') in ('ongoing', 'finished') else 'open'
            match = dict(fields, id=uid(), status=status, winner=None, demo=False, created_at=now(), **metadata)
            state['matches'].append(match)
            existing[source_id] = match
            added += 1
    add_log(state, '同步 %s 官方赛程：新增 %s 场，更新 %s 场，跳过 %s 场；赔率由你手动设置。' %
            (schedule['date'], added, updated, skipped), 'sync')
    return {'added': added, 'updated': updated, 'skipped': skipped}


def apply_action(state, action, payload, schedule=None):
    if not isinstance(payload, dict):
        raise RuleError('请求格式无效。')
    state.setdefault('comments', [])
    if action == 'place_bet':
        request_id = label(payload.get('request_id'), 80, '请求编号')
        if request_id in state['requests']:
            return
        match = find(state['matches'], payload.get('match_id'), '比赛')
        player = find(state['players'], payload.get('player_id'), '玩家')
        if not is_open(match):
            raise RuleError('这场比赛已封盘，不能再预测。')
        if not odds_ready(match):
            raise RuleError('这场比赛尚未设置双方赔率或确认赛制，请先在赛程管理中设置。')
        side = payload.get('side')
        if side not in ('a', 'b'):
            raise RuleError('请先选择支持的队伍。')
        if any(b['match_id'] == match['id'] and b['player_id'] == player['id']
               and b['status'] != 'cancelled' for b in state['bets']):
            raise RuleError('你已经预测过这场比赛。开赛前可在「我的预测」撤回后重新选择。')
        stake = integer(payload.get('stake'), 1, MAX_POINTS, '预测积分')
        if stake > player_stats(state, player['id'])['balance']:
            raise RuleError('可用积分不足，请减少预测积分。')
        odds = match['odds_' + side]
        if payload.get('expected_odds') != odds:
            raise RuleError('赔率刚刚更新，请查看新赔率后重新确认。')
        bet = {'id': uid(), 'match_id': match['id'], 'player_id': player['id'],
               'side': side, 'stake': stake, 'odds': odds, 'payout': 0,
               'status': 'pending', 'created_at': now(), 'settled_at': None}
        state['bets'].insert(0, bet)
        state['requests'].append(request_id)
        state['requests'] = state['requests'][-5000:]
        add_log(state, '%s 用 %s 积分支持 %s，锁定赔率 %.2f。' %
                (player['name'], stake, match['team_' + side], odds / 100), 'bet')
    elif action == 'sync_schedule':
        return sync_into_state(state, payload, schedule)
    elif action == 'add_comment':
        request_id = 'comment:' + label(payload.get('request_id'), 80, '请求编号')
        if request_id in state['requests']:
            return
        match = find(state['matches'], payload.get('match_id'), '比赛')
        player = find(state['players'], payload.get('player_id'), '玩家')
        if match['status'] not in ('settled', 'void'):
            raise RuleError('请先确认比赛结果，再参与赛后讨论。赛果撤销期间暂停新增留言。')
        text = label(payload.get('text'), 500, '留言')
        if len(state['comments']) >= MAX_COMMENTS or sum(c['match_id'] == match['id'] for c in state['comments']) >= MAX_MATCH_COMMENTS:
            raise RuleError('留言数量已达上限（每场 200 条、房间共 2,000 条）。请先备份，再整理自己的留言。')
        state['comments'].append({'id': uid(), 'match_id': match['id'], 'player_id': player['id'],
                                  'text': text, 'created_at': now(),
                                  'result': match['winner'] if match['status'] == 'settled' else 'void'})
        state['requests'].append(request_id)
        state['requests'] = state['requests'][-5000:]
    elif action == 'delete_comment':
        player = find(state['players'], payload.get('player_id'), '玩家')
        comment = find(state['comments'], payload.get('comment_id'), '留言')
        if comment['player_id'] != player['id']:
            raise RuleError('只能撤回当前玩家自己的留言。')
        state['comments'].remove(comment)
    elif action == 'cancel_bet':
        bet = find(state['bets'], payload.get('bet_id'), '预测')
        match = find(state['matches'], bet['match_id'], '比赛')
        if bet['status'] != 'pending' or not is_open(match):
            raise RuleError('只有尚未封盘的待结算预测可以撤回。')
        bet.update(status='cancelled', payout=bet['stake'], settled_at=now())
        player = find(state['players'], bet['player_id'], '玩家')
        add_log(state, '%s 撤回了对 %s vs %s 的预测，返还 %s 积分。' %
                (player['name'], match['team_a'], match['team_b'], bet['stake']), 'refund')
    elif action in ('create_match', 'edit_match'):
        fields = match_input(payload)
        if action == 'create_match':
            if len(state['matches']) >= 1000:
                raise RuleError('当前最多支持 1,000 场比赛，请备份后开启新赛季。')
            state['matches'].append(dict(fields, id=uid(), status='open', winner=None, demo=False, created_at=now()))
            add_log(state, '新增比赛：%s vs %s。' % (fields['team_a'], fields['team_b']))
        else:
            match = find(state['matches'], payload.get('match_id'), '比赛')
            if match['status'] in ('settled', 'void'):
                raise RuleError('已结束的比赛不可编辑；如需更正赛果，请先撤销结算。')
            has_history = any(b['match_id'] == match['id'] for b in state['bets'] + state['comments'])
            if has_history and any(fields[k] != match[k] for k in ('team_a', 'team_b', 'format', 'stage')):
                raise RuleError('已有预测或讨论时不能改变对阵、阶段和赛制，可修改开赛时间和后续赔率。')
            # A postponement must not implicitly reopen an automatically closed market.
            if not is_open(match):
                match['status'] = 'locked'
            match.update(fields)
            match['demo'] = False
            add_log(state, '更新了 %s vs %s；已有预测仍按原赔率结算。' % (match['team_a'], match['team_b']))
    elif action == 'toggle_lock':
        match = find(state['matches'], payload.get('match_id'), '比赛')
        if match['status'] not in ('open', 'locked'):
            raise RuleError('已结束的比赛不能重新开放。')
        if match['status'] == 'locked' and timestamp(match['starts_at']) <= time.time():
            raise RuleError('开赛时间已过。如比赛延期，请先编辑开赛时间，再开放预测。')
        if match['status'] == 'open' and timestamp(match['starts_at']) <= time.time():
            raise RuleError('比赛已按开赛时间自动封盘。如比赛延期，请先编辑开赛时间。')
        match['status'] = 'locked' if match['status'] == 'open' else 'open'
        add_log(state, '%s vs %s %s。' % (match['team_a'], match['team_b'],
                '已封盘' if match['status'] == 'locked' else '已重新开放预测'))
    elif action in ('settle_match', 'void_match'):
        match = find(state['matches'], payload.get('match_id'), '比赛')
        if match['status'] in ('settled', 'void'):
            raise RuleError('这场比赛已结算，请勿重复操作。')
        winner = payload.get('winner')
        if action == 'settle_match' and winner not in ('a', 'b'):
            raise RuleError('请确认获胜队伍。')
        match['status'] = 'settled' if action == 'settle_match' else 'void'
        match['winner'] = winner if action == 'settle_match' else None
        for bet in state['bets']:
            if bet['match_id'] == match['id'] and bet['status'] == 'pending':
                bet['status'] = 'void' if action == 'void_match' else ('won' if bet['side'] == winner else 'lost')
                bet['payout'] = bet['stake'] if action == 'void_match' else (
                    payout(bet['stake'], bet['odds']) if bet['side'] == winner else 0)
                bet['settled_at'] = now()
        message = '%s vs %s 已取消，所有预测积分原路退回。' % (match['team_a'], match['team_b'])
        if action == 'settle_match':
            message = '%s 战胜 %s，所有预测已按锁定赔率结算。' % (match['team_' + winner], match['team_b' if winner == 'a' else 'team_a'])
        add_log(state, message, 'settlement')
    elif action == 'undo_settlement':
        match = find(state['matches'], payload.get('match_id'), '比赛')
        if match['status'] not in ('settled', 'void'):
            raise RuleError('这场比赛尚未结算。')
        for player in state['players']:
            reclaim = sum(b['payout'] for b in state['bets'] if b['match_id'] == match['id']
                          and b['player_id'] == player['id'] and b['status'] != 'cancelled')
            if reclaim > player_stats(state, player['id'])['balance']:
                raise RuleError('%s 已使用部分返还积分。请先撤回或结算其他预测，再撤销本场结算。' % player['name'])
        for bet in state['bets']:
            if bet['match_id'] == match['id'] and bet['status'] != 'cancelled':
                bet.update(status='pending', payout=0, settled_at=None)
        match.update(status='locked', winner=None)
        add_log(state, '撤销了 %s vs %s 的结算，预测恢复为待结算，比赛保持封盘。' % (match['team_a'], match['team_b']), 'refund')
    elif action == 'settings':
        state['room']['name'] = label(payload.get('room_name'), 24, '房间名称')
        names = []
        for player in state['players']:
            data = payload.get(player['id'], {})
            player['name'] = label(data.get('name'), 16, '玩家昵称')
            player['favorite'] = str(data.get('favorite', '')).strip()[:24]
            names.append(player['name'].casefold())
        if names[0] == names[1]:
            raise RuleError('两位玩家请使用不同的昵称，方便辨认。')
        add_log(state, '房间与玩家信息已更新。')
    elif action == 'clear_examples':
        removable = {m['id'] for m in state['matches'] if m['demo'] and not any(b['match_id'] == m['id'] for b in state['bets'] + state['comments'])}
        state['matches'] = [m for m in state['matches'] if m['id'] not in removable]
        add_log(state, '已移除 %s 场尚无预测或讨论的示例比赛。' % len(removable))
    elif action == 'reset_season':
        if payload.get('confirmation') != 'RESET':
            raise RuleError('请输入 RESET 确认开启新赛季。')
        points = integer(payload.get('initial_points'), 1, MAX_POINTS, '初始积分')
        state.update(matches=[], bets=[], comments=[], activity=[], requests=[])
        state['room']['initial_points'] = points
        add_log(state, '新赛季开始，每人获得 %s 初始积分。' % points)
    elif action == 'import_backup':
        imported = validate_backup(payload.get('backup'))
        revision = state['revision']
        state.clear()
        state.update(imported)
        state['revision'] = revision
        add_log(state, '已从备份恢复房间。')
    else:
        raise RuleError('不支持的操作。')


def validate_backup(raw):
    """Validate both structure and accounting before replacing any local data."""
    try:
        if not isinstance(raw, dict) or raw.get('version') != 1:
            raise RuleError('这不是 Nexus Picks v1 备份。')
        state = {'version': 1, 'revision': 1, 'room': {
            'name': label(raw['room']['name'], 24, '房间名称'),
            'initial_points': integer(raw['room']['initial_points'], 1, MAX_POINTS, '初始积分')},
            'players': [], 'matches': [], 'bets': [], 'comments': [], 'activity': [], 'requests': []}
        if len(raw['players']) != 2 or len(raw['matches']) > 1000 or len(raw['bets']) > 50000:
            raise RuleError('备份的玩家数量或记录数量无效。')
        for index, player in enumerate(raw['players']):
            if player['id'] != 'p' + str(index + 1):
                raise RuleError('备份玩家编号无效。')
            state['players'].append({'id': player['id'], 'name': label(player['name'], 16, '玩家昵称'),
                                     'favorite': str(player.get('favorite', ''))[:24]})
        if state['players'][0]['name'].casefold() == state['players'][1]['name'].casefold():
            raise RuleError('备份中的玩家昵称不能相同。')
        used = set()
        source_ids = set()
        for match in raw['matches']:
            mid = label(match['id'], 80, '比赛编号')
            if mid in used or match['status'] not in ('open', 'locked', 'settled', 'void'):
                raise RuleError('备份中存在重复比赛或无效状态。')
            used.add(mid)
            winner = match.get('winner')
            if (match['status'] == 'settled' and winner not in ('a', 'b')) or (match['status'] != 'settled' and winner is not None):
                raise RuleError('备份赛果与比赛状态不一致。')
            timestamp(match['created_at'])
            metadata = source_metadata(match)
            if metadata:
                if metadata['source_id'] in source_ids:
                    raise RuleError('备份中存在重复的官方比赛编号，已拒绝导入。')
                source_ids.add(metadata['source_id'])
            state['matches'].append(dict(match_input(match), id=mid, status=match['status'],
                                         winner=winner, demo=bool(match.get('demo')), created_at=match['created_at'],
                                         **metadata))
        used = set()
        active = set()
        for bet in raw['bets']:
            bid = label(bet['id'], 80, '预测编号')
            if bid in used or bet['player_id'] not in ('p1', 'p2') or bet['side'] not in ('a', 'b'):
                raise RuleError('备份中存在无效或重复预测。')
            used.add(bid)
            match = find(state['matches'], bet['match_id'], '备份中的比赛')
            stake = integer(bet['stake'], 1, MAX_POINTS, '预测积分')
            odds = integer(bet['odds'], 101, 10000, '赔率')
            expected_status = 'pending'
            expected_payout = 0
            if bet['status'] == 'cancelled':
                expected_status, expected_payout = 'cancelled', stake
            else:
                key = (bet['player_id'], bet['match_id'])
                if key in active:
                    raise RuleError('同一玩家在同一比赛有多条有效预测。')
                active.add(key)
                if match['status'] == 'void':
                    expected_status, expected_payout = 'void', stake
                elif match['status'] == 'settled':
                    expected_status = 'won' if bet['side'] == match['winner'] else 'lost'
                    expected_payout = payout(stake, odds) if expected_status == 'won' else 0
            if bet['status'] != expected_status or type(bet['payout']) is not int or bet['payout'] != expected_payout:
                raise RuleError('备份积分账目不一致，已拒绝导入。')
            timestamp(bet['created_at'])
            if expected_status != 'pending':
                timestamp(bet['settled_at'])
            elif bet.get('settled_at') is not None:
                raise RuleError('待结算预测不应包含结算时间。')
            state['bets'].append({k: bet[k] for k in ('id', 'match_id', 'player_id', 'side', 'stake', 'odds', 'payout', 'status', 'created_at', 'settled_at')})
        for player in state['players']:
            if player_stats(state, player['id'])['balance'] < 0:
                raise RuleError('备份中有负积分余额，已拒绝导入。')
        comments = raw.get('comments', [])
        if not isinstance(comments, list) or len(comments) > MAX_COMMENTS:
            raise RuleError('备份中的留言数量或格式无效。')
        used, counts = set(), {}
        for comment in comments:
            cid = label(comment['id'], 80, '留言编号')
            match = find(state['matches'], comment['match_id'], '留言对应的比赛')
            find(state['players'], comment['player_id'], '留言玩家')
            if cid in used or comment['result'] not in ('a', 'b', 'void'):
                raise RuleError('备份中存在重复留言或无效的留言赛果。')
            used.add(cid)
            counts[match['id']] = counts.get(match['id'], 0) + 1
            if counts[match['id']] > MAX_MATCH_COMMENTS:
                raise RuleError('备份中的单场留言超过 200 条。')
            timestamp(comment['created_at'])
            state['comments'].append({'id': cid, 'match_id': match['id'], 'player_id': comment['player_id'],
                                      'text': label(comment['text'], 500, '留言'),
                                      'created_at': comment['created_at'], 'result': comment['result']})
        return state
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
        raise RuleError('备份文件结构无效，本机数据未被修改。')


class Store:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / 'nexus.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS room (id INTEGER PRIMARY KEY CHECK(id=1), content TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO room VALUES (1, ?)', (json.dumps(seed(), ensure_ascii=False),))
            state = json.loads(db.execute('SELECT content FROM room WHERE id=1').fetchone()[0])
            if 'comments' not in state:
                state['comments'] = []
                db.execute('UPDATE room SET content=? WHERE id=1', (json.dumps(state, ensure_ascii=False),))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.path), timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self):
        with self.connect() as db:
            return json.loads(db.execute('SELECT content FROM room WHERE id=1').fetchone()[0])

    def mutate(self, action, payload, schedule=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state = json.loads(db.execute('SELECT content FROM room WHERE id=1').fetchone()[0])
            sync_result = apply_action(state, action, payload, schedule=schedule)
            state['revision'] += 1
            db.execute('UPDATE room SET content=? WHERE id=1', (json.dumps(state, ensure_ascii=False),))
            result = public_state(state)
            if action == 'sync_schedule':
                result['sync_result'] = sync_result
            return result


class Handler(BaseHTTPRequestHandler):
    server_version = 'NexusPicks/1.2'

    def log_message(self, fmt, *args):
        if args and str(args[1]) not in ('200', '304'):
            super().log_message(fmt, *args)

    def send(self, code, body, content_type='application/json; charset=utf-8', extra=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'")
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def allowed_host(self):
        host = self.headers.get('Host', '')
        return host in ('127.0.0.1:%s' % self.server.server_port, 'localhost:%s' % self.server.server_port)

    def do_GET(self):
        if not self.allowed_host():
            return self.send(403, {'error': '仅允许通过本机地址访问。'})
        path = urlparse(self.path).path
        if path == '/api/state':
            return self.send(200, public_state(self.server.store.get()))
        if path == '/api/schedule':
            try:
                dates = parse_qs(urlparse(self.path).query).get('date', [])
                if len(dates) != 1:
                    raise ScheduleError('请选择一个有效日期。', 'INVALID_DATE', 400)
                schedule = fetch_schedule(dates[0])
                existing = {m['source_id']: m['id'] for m in self.server.store.get()['matches'] if m.get('source_id')}
                schedule = copy.deepcopy(schedule)
                for match in schedule['matches']:
                    match['existing_id'] = existing.get(match['source_id'])
                return self.send(200, schedule)
            except ScheduleError as error:
                return self.send(error.http_status, {'error': str(error), 'code': error.code})
        if path == '/api/backup':
            state = self.server.store.get()
            state.pop('requests', None)
            return self.send(200, state, extra={'Content-Disposition': 'attachment; filename="nexus-picks-backup.json"'})
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'application/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8'),
                 '/favicon.svg': ('favicon.svg', 'image/svg+xml')}
        if path not in files:
            return self.send(404, {'error': '页面不存在。'})
        filename, mime = files[path]
        self.send(200, (PUBLIC / filename).read_bytes(), mime)

    def do_POST(self):
        if not self.allowed_host() or self.headers.get('X-Nexus-Local') != '1':
            return self.send(403, {'error': '请从本机 Nexus Picks 页面操作。'})
        origin = self.headers.get('Origin')
        if origin and origin not in ('http://127.0.0.1:%s' % self.server.server_port, 'http://localhost:%s' % self.server.server_port):
            return self.send(403, {'error': '请求来源无效。'})
        if urlparse(self.path).path != '/api/action':
            return self.send(404, {'error': '接口不存在。'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 10_000_000:
                raise RuleError('请求为空或文件过大（最大 10 MB）。')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise RuleError('请求格式无效。')
            payload = data.get('payload', {})
            schedule = None
            if data.get('action') == 'sync_schedule':
                if not isinstance(payload, dict):
                    raise RuleError('请求格式无效。')
                # Fetch before beginning the database transaction, so network I/O cannot block bets.
                schedule = fetch_schedule(payload.get('date'))
            result = self.server.store.mutate(data.get('action'), payload, schedule=schedule)
            self.send(200, result)
        except ScheduleError as error:
            self.send(error.http_status, {'error': str(error), 'code': error.code})
        except RuleError as error:
            self.send(400, {'error': str(error)})
        except (ValueError, UnicodeDecodeError, RecursionError):
            self.send(400, {'error': '请求格式无效，请刷新重试。'})
        except Exception:
            import traceback
            traceback.print_exc()
            self.send(500, {'error': '保存失败，本次操作未生效。请检查本机磁盘并重试。'})


def main():
    parser = argparse.ArgumentParser(description='Nexus Picks 本地积分预测房')
    parser.add_argument('--port', type=int, default=None)
    parser.add_argument('--open', action='store_true', dest='open_browser')
    args = parser.parse_args()
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error('端口须在 1–65535 之间。')
    server = None
    for port in ([args.port] if args.port is not None else range(8765, 8776)):
        try:
            server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            break
        except OSError as error:
            if error.errno == errno.EADDRINUSE and args.port is None:
                continue
            print('无法在端口 %s 启动本地服务：%s' % (port, error))
            print('可使用 python3 server.py --port 8776 --open 选择其他端口。')
            return 1
    if server is None:
        print('默认端口均被占用，请使用 --port 指定其他端口。')
        return 1
    server.store = Store(DATA)
    url = 'http://127.0.0.1:%s' % server.server_port
    print('\n  NEXUS PICKS / 观赛搭子\n  %s\n  数据保存在：%s\n  按 Control + C 关闭服务。\n' % (url, DATA), flush=True)
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n已关闭。积分和预测记录已保存在本机。')
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
