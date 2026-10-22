/* Offline tests for public/app.js. No browser, HTTP connection, or production dependency. */
(function () {
  'use strict';
  var isNode = typeof process !== 'undefined' && process.versions && process.versions.node;
  var appPath = isNode ? process.argv[2] : globalThis.arguments[0];
  var readText = isNode ? function (path) { return require('fs').readFileSync(path, 'utf8'); } : readFile;
  var output = isNode ? function (message) { console.log(message); } : print;
  if (!appPath) throw new Error('Pass the absolute path to public/app.js.');
  var appSource = readText(appPath);
  if (!/\nrefresh\(\);\s*$/.test(appSource)) throw new Error('Application startup marker changed; update this offline harness explicitly.');
  appSource = appSource.replace(/\nrefresh\(\);\s*$/, '\n');

  var listeners = {}, nodes = new Map(), dynamicIds = new Set(), checkboxes = [], requests = [], responses = [];
  var uuidCounter = 0;
  function Node(id) {
    this.id = id || ''; this.value = ''; this.textContent = ''; this.disabled = false; this.checked = false;
    this.indeterminate = false; this.style = {}; this.dataset = {}; this._html = ''; this.fields = {};
    this.isConnected = true;
  }
  Node.prototype.addEventListener = function () {};
  Node.prototype.focus = function () { document.activeElement = this; };
  Node.prototype.setSelectionRange = function () {};
  Node.prototype.getClientRects = function () { return [1]; };
  Node.prototype.matches = function (selector) { return selector === '[data-source-id]' && Boolean(this.dataset.sourceId); };
  Node.prototype.querySelector = function (selector) { return nodes.get(selector) || null; };
  Node.prototype.querySelectorAll = function (selector) {
    if (selector.indexOf('[data-source-id]') === 0) {
      return checkboxes.filter(function (input) {
        return (selector.indexOf(':checked') === -1 || input.checked) &&
          (selector.indexOf(':not(:disabled)') === -1 || !input.disabled);
      });
    }
    return [];
  };
  Object.defineProperty(Node.prototype, 'innerHTML', {
    get: function () { return this._html; },
    set: function (html) {
      this._html = String(html);
      if (this.id === 'modal-root') {
        dynamicIds.forEach(function (key) { nodes.delete(key); }); dynamicIds.clear();
      }
      if (this.id === 'modal-root' || this.id === 'sync-preview') {
        var tags = this._html.match(/<(?:input|button|div|form|section)[^>]*\bid="[^"]+"[^>]*>/g) || [];
        tags.forEach(function (tag) {
          var id = /\bid="([^"]+)"/.exec(tag)[1], node = new Node(id);
          var value = /\bvalue="([^"]*)"/.exec(tag);
          node.value = value ? value[1] : ''; node.disabled = /\sdisabled(?:\s|>|=)/.test(tag);
          nodes.set('#' + id, node); dynamicIds.add('#' + id);
        });
      }
      if (this.id === 'sync-preview') {
        checkboxes = (this._html.match(/<input[^>]*data-source-id="[^"]+"[^>]*>/g) || []).map(function (tag) {
          var input = new Node(); input.dataset.sourceId = /data-source-id="([^"]+)"/.exec(tag)[1];
          input.checked = /\schecked(?:\s|>|=)/.test(tag); input.disabled = /\sdisabled(?:\s|>|=)/.test(tag);
          return input;
        });
      }
    }
  });
  ['app', 'modal-root', 'toast-root', 'backup-file'].forEach(function (id) { nodes.set('#' + id, new Node(id)); });
  var document = {
    activeElement: new Node('body'), body: new Node('body'), hidden: false,
    querySelector: Node.prototype.querySelector, querySelectorAll: Node.prototype.querySelectorAll,
    addEventListener: function (type, listener) { (listeners[type] || (listeners[type] = [])).push(listener); }
  };
  var window = {addEventListener: function () {}, scrollTo: function () {}};
  var location = {hash: ''}, localStorage = {getItem: function () { return null; }, setItem: function () {}};
  var crypto = {randomUUID: function () { return 'offline-test-' + (++uuidCounter); }};
  var AbortSignal = {timeout: function (ms) { return {timeoutMs: ms}; }};
  var setInterval = function () { return 1; }, setTimeout = function () { return 1; }, clearTimeout = function () {};
  function FormData(form) { this.fields = form.fields || {}; }
  FormData.prototype[Symbol.iterator] = function () { return Object.entries(this.fields)[Symbol.iterator](); };
  function fetch(url, options) {
    requests.push({url: url, options: options || {}});
    if (!responses.length) throw new Error('Unexpected fetch: networking is forbidden in offline tests.');
    var response = responses.shift();
    return typeof response === 'function' ? response() : Promise.resolve(response);
  }
  function reply(ok, data) { return {ok: ok, json: function () { return Promise.resolve(data); }}; }
  function queueReply(ok, data) { responses.push(reply(ok, data)); }
  function assert(condition, message) { if (!condition) throw new Error(message); }
  function eq(actual, expected, message) {
    assert(actual === expected, message + ' (expected ' + JSON.stringify(expected) + ', received ' + JSON.stringify(actual) + ')');
  }
  function contains(html, text, message) { assert(html.indexOf(text) !== -1, message || ('Missing ' + text)); }
  function absent(html, text, message) { assert(html.indexOf(text) === -1, message || ('Unexpected ' + text)); }

  var suite = async function () {
    var tests = [], passed = 0;
    function test(name, body) { tests.push({name: name, body: body}); }
    function baseState() {
      return {room: {name: 'Offline room', initial_points: 1000}, revision: 1,
        players: [{id: 'p1', name: 'Me', favorite: 'T1', balance: 1000, assets: 1000, locked: 0, profit: 0, wins: 0, losses: 0, hit_rate: null},
          {id: 'p2', name: 'Friend', favorite: 'BLG', balance: 1000, assets: 1000, locked: 0, profit: 0, wins: 0, losses: 0, hit_rate: null}],
        matches: [], bets: [], activity: []};
    }
    function fixture(overrides) {
      return Object.assign({id: 'm1', source_id: 'source-1', source: 'lpl.qq.com', source_status: 'upcoming',
        source_url: 'https://lpl.qq.com/', team_a: 'T1', team_b: 'BLG', stage: 'Worlds', format: 'BO3',
        starts_at: new Date(Date.now() + 86400000).toISOString(), status: 'open', winner: null,
        odds_a: null, odds_b: null, demo: false}, overrides || {});
    }
    function syncDate(date) {
      showScheduleSync(); nodes.get('#sync-date').value = date;
    }
    async function changedDate(date) {
      var input = nodes.get('#sync-date'); input.value = date;
      for (var handler of listeners.change) await handler({target: input});
    }
    test('empty room invites official sync and manual creation without fake fixtures', function () {
      var html = renderLobby(); contains(html, 'sync-schedule'); contains(html, 'new-match');
      contains(html, '从这里开始'); absent(html, 'class="match-card');
    });
    test('official fixture renders its source and no automatic odds', function () {
      var html = renderMatch(fixture()); contains(html, '官方赛程'); contains(html, '设置赔率');
      absent(html, 'data-pick='); absent(html, '0.00'); absent(html, '1.85');
    });
    test('one-sided odds remain unavailable for predictions', function () {
      var match = fixture({odds_a: 185}); eq(readyOdds(match), false, 'Both odds required');
      absent(renderMatch(match), 'data-pick=');
    });
    test('unknown format remains unavailable even if odds are present', function () {
      var match = fixture({format: '待确认', odds_a: 185, odds_b: 210});
      eq(readyOdds(match), false, 'Confirmed format required'); absent(renderMatch(match), 'data-pick=');
      state.matches = [match]; showMatchEditor(match.id);
      contains(nodes.get('#modal-root').innerHTML, '官方未公布，请确认赛制');
      contains(nodes.get('#modal-root').innerHTML, 'name="format" required');
    });
    test('configured odds expose exact decimal prices and pick controls', function () {
      var match = fixture({odds_a: 185, odds_b: 210}); eq(readyOdds(match), true, 'Odds available');
      var html = renderMatch(match); contains(html, '1.85'); contains(html, '2.10'); contains(html, 'data-pick="m1"');
    });
    test('past and locked fixtures disable prediction controls', function () {
      var match = fixture({starts_at: '2020-01-01T00:00:00+08:00', odds_a: 185, odds_b: 210});
      eq(effectiveStatus(match), 'locked', 'Automatic cutoff');
      assert((renderMatch(match).match(/disabled/g) || []).length >= 2, 'Both picks disabled');
    });
    test('favorite labels match player teams without case sensitivity', function () {
      state.players[0].favorite = 't1'; var html = renderMatch(fixture());
      contains(html, '你的主队'); contains(html, '搭子主队');
      state.players[1].favorite = 'T1'; contains(renderMatch(fixture()), '共同主队');
    });
    test('favorite quick filter excludes unrelated fixtures', function () {
      state.matches = [fixture({odds_a: 185, odds_b: 210}), fixture({id: 'm2', source_id: 'source-2', team_a: 'GEN', team_b: 'HLE', odds_a: 150, odds_b: 230})];
      onlyFavorite = true; var html = renderLobby(); contains(html, 'data-pick="m1"'); absent(html, 'data-pick="m2"');
    });
    test('team search excludes nonmatching fixtures', function () {
      state.matches = [fixture({odds_a: 185, odds_b: 210}), fixture({id: 'm2', source_id: 'source-2', team_a: 'GEN', team_b: 'HLE', odds_a: 150, odds_b: 230})];
      searchTerm = 'gen'; var html = renderLobby(); absent(html, 'data-pick="m1"'); contains(html, 'data-pick="m2"');
    });
    test('UTC+8 day grouping handles UTC day boundaries', function () {
      eq(dayKey('2026-10-23T16:00:00Z'), '2026-10-24', 'UTC+8 day');
      eq(clockTime('2026-10-23T16:00:00Z'), '00:00', 'UTC+8 time');
    });
    test('status filters distinguish setup, available, and ended fixtures', function () {
      var match = fixture(); eq(matchesFilter(match, 'setup'), true, 'Setup matches'); eq(matchesFilter(match, 'open'), false, 'Unset odds unavailable');
      match.odds_a = 185; match.odds_b = 210; eq(matchesFilter(match, 'open'), true, 'Configured match available');
      match.status = 'settled'; eq(matchesFilter(match, 'ended'), true, 'Ended match');
    });
    test('fixture fields are escaped before rendering', function () {
      var html = renderMatch(fixture({team_a: '<script>alert(1)</script>', stage: '<img src=x>'}));
      absent(html, '<script>alert'); absent(html, '<img src=x>'); contains(html, '&lt;script&gt;');
    });
    test('sync preview selects only new upcoming fixtures by default and escapes warnings', function () {
      var html = syncResultsHtml({date: '2026-10-24', warnings: ['<unconfirmed>'], matches: [fixture(),
        fixture({source_id: 'existing', existing_id: 'm2'}), fixture({source_id: 'past', starts_at: '2020-01-01T00:00:00+08:00'})]});
      contains(html, 'data-source-id="source-1" checked'); contains(html, 'data-source-id="existing" disabled');
      absent(html, 'data-source-id="past" checked'); contains(html, '&lt;unconfirmed&gt;');
    });
    test('sync form begins on the selected UTC+8 date with import disabled', function () {
      scheduleDate = '2026-10-24'; showScheduleSync();
      eq(nodes.get('#sync-date').value, '2026-10-24', 'Selected date retained'); eq(nodes.get('#sync-import').disabled, true, 'Import disabled before fetching');
    });
    test('official error keeps the date, displays error, and enables retry', async function () {
      syncDate('2026-10-21'); queueReply(false, {error: '官方尚未公布当日赛程', code: 'NO_SCHEDULE'});
      await fetchOfficialSchedule('2026-10-21');
      eq(nodes.get('#sync-date').value, '2026-10-21', 'Error must retain selected date');
      contains(nodes.get('#modal-error').textContent, '官方尚未公布'); eq(nodes.get('#sync-fetch').disabled, false, 'Retry enabled');
      eq(nodes.get('#sync-import').disabled, true, 'No import on error'); eq(state.matches.length, 0, 'Room unchanged');
    });
    test('changing sync date clears stale results, errors, and selected imports', async function () {
      syncDate('2026-10-21'); modal.loadedDate = '2026-10-21'; modal.results = [fixture()];
      nodes.get('#modal-error').textContent = 'old error';
      await changedDate('2026-10-24');
      eq(nodes.get('#sync-date').value, '2026-10-24', 'New date kept'); eq(modal.loadedDate, null, 'Old loaded date cleared');
      eq(nodes.get('#modal-error').textContent, '', 'Old error cleared'); eq(nodes.get('#sync-import').disabled, true, 'Old selection cannot import');
    });
    test('successful official preview uses selected date and a 20 second timeout', async function () {
      syncDate('2026-10-24'); queueReply(true, {date: '2026-10-24', matches: [fixture()]});
      await fetchOfficialSchedule('2026-10-24');
      eq(modal.loadedDate, '2026-10-24', 'Loaded date'); eq(modal.results.length, 1, 'Preview populated');
      eq(nodes.get('#sync-import').disabled, false, 'Selected new fixture can import');
      var request = requests[requests.length - 1]; eq(request.url, '/api/schedule?date=2026-10-24', 'Date request');
      eq(request.options.signal.timeoutMs, 20000, 'Preview timeout'); eq(state.matches.length, 0, 'Preview does not import');
    });
    test('empty successful response becomes an error without synthetic fixtures', async function () {
      syncDate('2026-10-21'); queueReply(true, {date: '2026-10-21', matches: []});
      await fetchOfficialSchedule('2026-10-21'); contains(nodes.get('#modal-error').textContent, '官方尚未公布');
      eq(nodes.get('#sync-date').value, '2026-10-21', 'Date retained'); eq(state.matches.length, 0, 'No fallback fixtures');
    });
    test('timeout keeps selected date and leaves import disabled', async function () {
      syncDate('2026-10-21'); responses.push(function () { var error = new Error('timeout'); error.name = 'TimeoutError'; return Promise.reject(error); });
      await fetchOfficialSchedule('2026-10-21'); contains(nodes.get('#modal-error').textContent, '超时');
      eq(nodes.get('#sync-date').value, '2026-10-21', 'Date retained'); eq(nodes.get('#sync-import').disabled, true, 'Import disabled');
    });
    test('date change while a request is pending rejects the stale response', async function () {
      syncDate('2026-10-21'); var resolveResponse;
      responses.push(function () { return new Promise(function (resolve) { resolveResponse = resolve; }); });
      var pending = fetchOfficialSchedule('2026-10-21'); await changedDate('2026-10-24');
      resolveResponse(reply(true, {date: '2026-10-21', matches: [fixture()]})); await pending;
      eq(nodes.get('#sync-date').value, '2026-10-24', 'New date remains'); eq(modal.loadedDate, null, 'Stale date not loaded');
      contains(nodes.get('#sync-preview').innerHTML, '日期已更改');
    });
    test('closing a sync dialog ignores a late response', async function () {
      syncDate('2026-10-24'); var resolveResponse;
      responses.push(function () { return new Promise(function (resolve) { resolveResponse = resolve; }); });
      var pending = fetchOfficialSchedule('2026-10-24'); closeModal();
      resolveResponse(reply(true, {date: '2026-10-24', matches: [fixture()]})); await pending;
      eq(modal, null, 'Closed dialog must remain closed'); eq(state.matches.length, 0, 'No import after close');
    });
    test('manual creation leaves both odds empty', function () {
      showMatchEditor(); eq(nodes.get('#odds-a').value, '', 'No automatic side A odds'); eq(nodes.get('#odds-b').value, '', 'No automatic side B odds');
    });
    test('one-sided manual odds are rejected before mutation', async function () {
      showMatchEditor(); var before = requests.length;
      await listeners.submit[0]({preventDefault: function () {}, target: {id: 'match-form', fields: {team_a: 'T1', team_b: 'BLG', stage: 'Worlds', format: 'BO3', starts_at: '2026-10-24T20:00', odds_a: '1.85', odds_b: ''}}});
      contains(nodes.get('#modal-error').textContent, '同时填写双方赔率'); eq(requests.length, before, 'No network mutation');
    });
    test('both empty manual odds are submitted as null', async function () {
      showMatchEditor(); var capture, originalMutate = mutate;
      mutate = async function (action, payload) { capture = {action: action, payload: payload}; return true; };
      try {
        await listeners.submit[0]({preventDefault: function () {}, target: {id: 'match-form', fields: {team_a: 'T1', team_b: 'BLG', stage: 'Worlds', format: 'BO3', starts_at: '2026-10-24T20:00', odds_a: '', odds_b: ''}}});
      } finally { mutate = originalMutate; }
      eq(capture.action, 'create_match', 'Manual action'); eq(capture.payload.odds_a, null, 'Side A null'); eq(capture.payload.odds_b, null, 'Side B null');
    });
    test('sync import sends only checked source IDs and the loaded date', async function () {
      syncDate('2026-10-24'); modal.loadedDate = '2026-10-24';
      nodes.get('#sync-preview').innerHTML = syncResultsHtml({date: '2026-10-24', matches: [fixture(), fixture({source_id: 'existing', existing_id: 'm2'})]});
      var capture, originalMutate = mutate; mutate = async function (action, payload) { capture = {action: action, payload: payload}; return true; };
      try {
        var button = {dataset: {action: 'sync-import'}, closest: function () { return this; }};
        await listeners.click[0]({target: button});
      } finally { mutate = originalMutate; }
      eq(capture.action, 'sync_schedule', 'Import action'); eq(capture.payload.date, '2026-10-24', 'Loaded date');
      eq(capture.payload.source_ids.join(','), 'source-1', 'Existing fixture excluded');
    });

    for (var item of tests) {
      state = baseState(); selected = null; activeId = 'p1'; filter = 'all'; betFilter = 'all';
      scheduleDate = 'all'; searchTerm = ''; onlyFavorite = false; busy = false; serverOffset = 0;
      closeModal(); checkboxes = []; responses = []; requests = []; document.activeElement = document.body;
      try { await item.body(); passed++; output('PASS ' + item.name); }
      catch (error) { throw new Error('FAIL ' + item.name + '\n' + (error.stack || error)); }
      assert(responses.length === 0, 'Fixture response was not consumed by: ' + item.name);
    }
    output('\n' + passed + '/' + tests.length + ' offline frontend tests passed. No browser or network used.');
  };
  var result = eval(appSource + '\n(' + suite.toString() + ')();');
  result.catch(function (error) {
    output(error.stack || String(error));
    if (isNode) process.exitCode = 1;
    else quit(1);
  });
}());
