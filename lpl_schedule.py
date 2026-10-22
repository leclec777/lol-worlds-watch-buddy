"""Read the public schedule feed actually used by the lpl.qq.com homepage.

No odds, no prediction results, no execution of downloaded JavaScript.
The .js endpoint below contains a JSON document, not a script to evaluate.
"""
import json
import re
import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SOURCE_URL = 'https://lpl.qq.com/'
FEED_URL = 'https://lpl.qq.com/web201612/data/LOL_MATCH2_MATCH_HOMEPAGE_BMATCH_LIST.js'
CHINA_TIME = timezone(timedelta(hours=8))
MAX_BYTES = 6_000_000
CACHE_SECONDS = 30
_cache_lock = threading.Lock()
_cached_document = None
_cached_at = 0


class ScheduleError(Exception):
    def __init__(self, message, code='SOURCE_UNAVAILABLE', http_status=502):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


def validate_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ScheduleError('请选择有效日期，格式为 YYYY-MM-DD。', 'INVALID_DATE', 400)
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        raise ScheduleError('日期不存在，请重新选择。', 'INVALID_DATE', 400)
    return value


def _load_document():
    global _cached_document, _cached_at
    with _cache_lock:
        if _cached_document is not None and time.monotonic() - _cached_at < CACHE_SECONDS:
            return _cached_document
        try:
            request = Request(FEED_URL, headers={
                'User-Agent': 'Mozilla/5.0 NexusPicks/1.1 (local schedule reader)',
                'Accept': 'application/json,text/plain,*/*',
                'Referer': SOURCE_URL,
            })
            with urlopen(request, timeout=12) as response:
                data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ScheduleError('官方赛程数据超出预期大小，请稍后重试。', 'SOURCE_FORMAT_CHANGED')
            document = json.loads(data.decode('utf-8-sig'))
            if not isinstance(document, dict) or str(document.get('status')) != '0' or not isinstance(document.get('msg'), list):
                raise ScheduleError('官方赛程数据结构已变化，未导入任何比赛。', 'SOURCE_FORMAT_CHANGED')
        except ScheduleError:
            raise
        except (HTTPError, URLError, socket.timeout, TimeoutError, OSError):
            raise ScheduleError('暂时无法连接 lpl.qq.com 官方赛程。请检查网络或稍后重试，未添加任何比赛。')
        except (ValueError, UnicodeDecodeError):
            raise ScheduleError('官方赛程返回了无法识别的数据，未导入任何比赛。', 'SOURCE_FORMAT_CHANGED')
        _cached_document, _cached_at = document, time.monotonic()
        return document


def _confirmed_teams(row):
    # bMatchName is used because official TeamShortNameA is often empty.
    parts = re.split(r'\s+vs\.?\s+', str(row.get('bMatchName', '')).strip(), flags=re.IGNORECASE)
    if len(parts) != 2:
        parts = [str(row.get('TeamShortNameA', '')).strip(), str(row.get('TeamShortNameB', '')).strip()]
    a, b = [part.strip() for part in parts]
    placeholder = re.compile(r'^(?:TBD|TBC|待定|待确认|未知|\?|—|-)+$', re.IGNORECASE)
    ids = [str(row.get('TeamA', '')), str(row.get('TeamB', ''))]
    if (not a or not b or a.casefold() == b.casefold() or len(a) > 24 or len(b) > 24
            or placeholder.fullmatch(a) or placeholder.fullmatch(b)
            or any(i in ('0', '297') for i in ids)):
        return None
    return a, b


def normalize_schedule(document, date):
    date = validate_date(date)
    if not isinstance(document, dict) or str(document.get('status')) != '0' or not isinstance(document.get('msg'), list):
        raise ScheduleError('官方赛程数据结构已变化，未导入任何比赛。', 'SOURCE_FORMAT_CHANGED')
    rows = [r for r in document['msg'] if isinstance(r, dict)
            and str(r.get('MatchDate', '')).startswith(date + ' ')
            and str(r.get('isTft', '0')) != '1']
    if not rows:
        raise ScheduleError('lpl.qq.com 尚未公布 %s 的比赛，或该日无比赛。请选择其他日期后重试。' % date,
                            'NO_SCHEDULE', 400)
    matches, warnings, ids = [], [], set()
    unknown = unsupported = malformed = 0
    for row in rows:
        teams = _confirmed_teams(row)
        if teams is None:
            unknown += 1
            continue
        mode = str(row.get('GameModeName', '')).strip().upper()
        if not mode:
            mode = {'1': 'BO1', '3': 'BO3', '4': 'BO5'}.get(str(row.get('GameMode')), '待确认')
        if mode not in ('BO1', 'BO3', 'BO5', '待确认'):
            unsupported += 1
            continue
        mid = str(row.get('bMatchId') or '').strip()
        try:
            start = datetime.strptime(str(row['MatchDate']), '%Y-%m-%d %H:%M:%S').replace(tzinfo=CHINA_TIME)
            if not mid or len(mid) > 80:
                raise ValueError()
        except (ValueError, KeyError):
            malformed += 1
            continue
        if mid in ids:
            continue
        ids.add(mid)
        source_status = {'1': 'upcoming', '2': 'ongoing', '3': 'finished'}.get(str(row.get('MatchStatus')), 'unknown')
        stage_parts = [str(row.get(k) or '').strip() for k in ('GameName', 'GameTypeName', 'GameProcName')]
        stage = ' · '.join(dict.fromkeys(p for p in stage_parts if p)) or '官方比赛'
        def score(key):
            try:
                value = int(row.get(key))
                return value if 0 <= value <= 99 and source_status in ('ongoing', 'finished') else None
            except (ValueError, TypeError):
                return None
        matches.append({'source_id': mid, 'team_a': teams[0], 'team_b': teams[1],
                        'stage': stage[:48], 'format': mode, 'starts_at': start.isoformat(),
                        'source_status': source_status, 'score_a': score('ScoreA'), 'score_b': score('ScoreB'),
                        'source_url': SOURCE_URL, 'odds_a': None, 'odds_b': None})
    if not matches:
        if unknown and unknown == len(rows):
            raise ScheduleError('官方已公布 %s 的比赛时间，但完整对阵尚未公布。请等待抽签或队伍确认后再同步。' % date,
                                'NO_CONFIRMED_MATCHES', 400)
        if unsupported and unsupported + unknown == len(rows):
            raise ScheduleError('当日已公布比赛包含暂不支持的赛制（如 BO2），无法用于单场胜负预测。', 'UNSUPPORTED_FORMAT', 400)
        raise ScheduleError('当日官方赛程的对阵、时间或赛制数据不完整，未导入任何比赛。', 'SOURCE_FORMAT_CHANGED')
    if unknown:
        warnings.append('%s 场对阵尚未公布，暂不导入。' % unknown)
    if unsupported:
        warnings.append('%s 场使用暂不支持的赛制（如 BO2），暂不导入。' % unsupported)
    if malformed:
        warnings.append('%s 场官方时间或编号异常，已跳过。' % malformed)
    matches.sort(key=lambda m: (m['starts_at'], m['source_id']))
    return {'date': date, 'timezone': 'Asia/Shanghai', 'source_url': SOURCE_URL, 'source_data_url': FEED_URL,
            'source_updated_at': str(document.get('lastUpTime', '')), 'fetched_at': datetime.now(timezone.utc).isoformat(),
            'matches': matches, 'warnings': warnings}


def fetch_schedule(date):
    validate_date(date)
    return normalize_schedule(_load_document(), date)
