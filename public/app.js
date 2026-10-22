'use strict';
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num = n => Number(n).toLocaleString('zh-CN');
const signed = n => `${n > 0 ? '+' : ''}${num(n)}`;
const odds = n => Number.isInteger(n) && n >= 101 ? (n / 100).toFixed(2) : '—';
const readyOdds = m => Number.isInteger(m.odds_a) && m.odds_a >= 101 && Number.isInteger(m.odds_b) && m.odds_b >= 101 && ['BO1','BO3','BO5'].includes(m.format);
const officialMatch = m => Boolean(m.source_id || m.source === 'lpl.qq.com');
const dayKey = value => new Date(new Date(value).getTime() + 28800000).toISOString().slice(0,10);
const todayKey = () => dayKey(Date.now() + serverOffset);
const dayLabel = value => fmt(value+'T12:00:00+08:00',{month:'long',day:'numeric',weekday:'short',timeZone:'Asia/Shanghai'});
const returns = (stake, rate) => Math.floor((stake * rate + 50) / 100);
const fmt = (date, options) => new Intl.DateTimeFormat('zh-CN', options).format(new Date(date));
const dateTime = date => fmt(date, {month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hour12:false,timeZone:'Asia/Shanghai'});
const clockTime = date => fmt(date, {hour:'2-digit', minute:'2-digit', hour12:false,timeZone:'Asia/Shanghai'});
const rid = () => crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const paths = {
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  ticket:'<path d="M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v3a2 2 0 0 0 0 4v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3a2 2 0 0 0 0-4z"/><path d="M15 5v3m0 3v2m0 3v3"/>',
  trophy:'<path d="M8 3h8v5c0 5-1.5 7-4 7S8 13 8 8zM8 5H4v3a4 4 0 0 0 4 4m8-7h4v3a4 4 0 0 1-4 4M12 15v5m-4 1h8"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 11h18m-13 4h2m4 0h2m-8 3h2"/>',
  settings:'<path d="m9 3-1 3-3 1-2 3 2 2-1 3 2 3 3-1 2 3h3l1-3 3-1 2-3-2-2 1-3-2-3-3 1-2-3z"/><circle cx="11.5" cy="11.5" r="3"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2-3 4m.1 3h.01"/>',
  chevron:'<path d="m9 5 7 7-7 7"/>',
  down:'<path d="m7 10 5 5 5-5"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  up:'<path d="m4 16 6-6 4 4 6-10m-5 0h5v5"/>',
  wallet:'<path d="M20 7H5a2 2 0 0 1 0-4h13v4M5 7H3v12a2 2 0 0 0 2 2h15V7z"/><path d="M20 11h-6v6h6m-3-3h.01"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4m-4 5v2"/>',
  target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  users:'<circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6m2 3a6 6 0 0 1 3 5v2"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  shield:'<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6z"/><path d="m8 12 3 3 5-6"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  upload:'<path d="M12 16V4m-5 5 5-5 5 5M4 16v5h16v-5"/>',
  spark:'<path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5z"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  refresh:'<path d="M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5m-4 8a8 8 0 0 0 14 3l3-3m0 5v-5h-5"/>'
};
const icon = (name, size=18) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.spark}</svg>`;
const TEAM = {
  T1:{color:'#f2777e',region:'LCK',name:'T1'}, BLG:{color:'#80d3e5',region:'LPL',name:'Bilibili Gaming'},
  GEN:{color:'#ddc27c',region:'LCK',name:'Gen.G'}, HLE:{color:'#ff9f65',region:'LCK',name:'Hanwha Life'},
  G2:{color:'#dedfe4',region:'LEC',name:'G2 Esports'}, TES:{color:'#ef8a7a',region:'LPL',name:'Top Esports'},
  WBG:{color:'#e3ac70',region:'LPL',name:'Weibo Gaming'}, DK:{color:'#81d8b1',region:'LCK',name:'Dplus KIA'}
};
const team = name => TEAM[name.toUpperCase()] || {color:'#a9b5db',region:'TEAM',name};
const teamBadge = name => `<span class="team-badge" style="--team-color:${team(name).color}" aria-hidden="true">${esc(name.slice(0,3))}</span>`;
const avatar = (p, size='') => `<span class="avatar ${p.id === 'p2' ? 'p2' : ''} ${size}" aria-hidden="true">${esc([...p.name].slice(0,2).join(''))}</span>`;
const stateLabel = {pending:'待结算',won:'预测命中',lost:'未命中',void:'比赛取消',cancelled:'已撤回'};
let state, selected = null, page = ['lobby','predictions','leaderboard','manage','settings'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'lobby';
let activeId = 'p1';
try { activeId = localStorage.getItem('nexus-active-player') === 'p2' ? 'p2' : 'p1'; } catch (_) {}
let filter = 'all', betFilter = 'all', busy = false, modal = null, modalTrigger = null, toastTimer, online = true;
let serverOffset = 0, lastTimeKey = '', scheduleDate = 'all', searchTerm = '', onlyFavorite = false;
let refreshRequest = 0;
const me = () => state.players.find(p => p.id === activeId);
const matchById = id => state.matches.find(m => m.id === id);
const effectiveStatus = m => m.status === 'open' && Date.parse(m.starts_at) <= Date.now() + serverOffset ? 'locked' : m.status;
const myBet = m => state.bets.find(b => b.match_id === m.id && b.player_id === activeId && b.status !== 'cancelled');
const statusHtml = m => { const s = effectiveStatus(m), pending=s==='open'&&!readyOdds(m); return `<span class="status ${pending?'needs-odds':s}"><i class="dot"></i>${pending?(m.format==='待确认'?'待确认赛制':'待设赔率'):{open:'可预测',locked:'已封盘',settled:'已结算',void:'已取消'}[s]}</span>`; };
const matchesFilter = (m, selectedFilter=filter) => selectedFilter==='all'||(selectedFilter==='open'?effectiveStatus(m)==='open'&&readyOdds(m):selectedFilter==='setup'?effectiveStatus(m)==='open'&&!readyOdds(m):selectedFilter==='locked'?effectiveStatus(m)==='locked':['settled','void'].includes(effectiveStatus(m)));
const matchesFavorite = m => [m.team_a,m.team_b].some(t=>t.trim().toLowerCase()===me().favorite.trim().toLowerCase());
const favoriteTag = name => {const ids=state.players.filter(p=>p.favorite.trim().toLowerCase()===name.trim().toLowerCase()).map(p=>p.id);return ids.length?`<span class="favorite-tag ${ids.includes(activeId)?'mine':'friend'}">${icon('spark',9)}${ids.length===2?'共同主队':ids.includes(activeId)?'你的主队':'搭子主队'}</span>`:'';};
const sourceCaption = m => officialMatch(m)?'<span class="source-tag">'+icon('check',9)+'官方赛程</span>':m.demo?'<span class="demo-tag">旧版示例</span>':'<span class="manual-tag">手动添加</span>';

function trophyArt() {
  return `<svg class="hero-art" viewBox="0 0 260 230" fill="none" aria-hidden="true"><defs><linearGradient id="metal" x1="60" y1="30" x2="190" y2="190" gradientUnits="userSpaceOnUse"><stop stop-color="#d8efb9"/><stop offset=".4" stop-color="#70875b"/><stop offset="1" stop-color="#2b412e"/></linearGradient><linearGradient id="shine" x1="120" y1="20" x2="145" y2="200"><stop stop-color="#d9f9ab"/><stop offset="1" stop-color="#30462c"/></linearGradient></defs><circle cx="145" cy="110" r="85" stroke="#8caf5f" stroke-opacity=".14"/><circle cx="145" cy="110" r="69" stroke="#8caf5f" stroke-opacity=".10"/><path d="M44 169 218 39M56 190 231 60" stroke="#a1c67d" stroke-opacity=".15"/><path d="m99 44 45-18 47 19-12 75-35 32-33-33z" fill="url(#metal)" fill-opacity=".8" stroke="#a0bb7c" stroke-width=".6"/><path d="m99 44 45 21 47-20-47-19z" fill="#b5d796" fill-opacity=".33"/><path d="m144 65 0 86-20-27-7-69z" fill="url(#shine)"/><path d="m150 64 27-12-11 64-16 22z" fill="#253d29"/><path d="m100 57-21-7 7 50 26 20m76-62 22-8-8 49-25 21" stroke="url(#metal)" stroke-width="9"/><path d="m139 147-4 33h21l-9-33" fill="url(#metal)"/><path d="m118 179 44-1 17 14-76 1z" fill="#718b56"/><path d="m103 193 76-1v9l-76 1z" fill="#32472c"/><path d="m113 204 56-1" stroke="#c5f16d" stroke-opacity=".35"/><path d="m144 71-9 20 9-5 9 5z" fill="#d3efa9"/><path d="m144 87-9 10 9 19 9-19z" fill="#b5d18b"/><path d="M66 75h8m-4-4v8m137 77h10m-5-5v10M192 19h7m-3-3v6" stroke="#94b472" stroke-opacity=".6"/></svg>`;
}

function shell() {
  const names = {lobby:'比赛大厅',predictions:'我的预测',leaderboard:'双人排行榜',manage:'赛程管理',settings:'房间设置'};
  const pending = state.bets.filter(b => b.status === 'pending' && b.player_id === activeId).length;
  return `<div class="shell"><aside class="sidebar"><a class="brand" href="#lobby" aria-label="Nexus Picks 首页"><img src="/favicon.svg" alt=""><div><strong>NEXUS PICKS</strong><span>观赛搭子</span></div></a><div class="side-label">YOUR PLAYGROUND</div><nav class="nav" aria-label="主导航">${[['lobby','grid','比赛大厅'],['predictions','ticket','我的预测'],['leaderboard','trophy','双人排行榜'],['manage','calendar','赛程管理']].map(([id,ic,name])=>`<button data-page="${id}" class="${page===id?'active':''}" ${page===id?'aria-current="page"':''}>${icon(ic,17)}${name}${id==='predictions'&&pending?`<span class="badge">${pending}</span>`:''}</button>`).join('')}</nav><div class="season-card"><div class="eyebrow">LEAGUE OF LEGENDS</div><strong>世界赛，一起看。</strong><p>好朋友，也可以是好对手。</p></div><div class="sidebar-bottom"><button data-page="settings">${icon('settings',16)}房间设置</button><button data-action="rules">${icon('help',16)}玩法与积分规则</button><div class="local-badge"><i class="dot"></i><span>本地房间 · 数据已保存</span></div></div></aside><div class="workspace"><header class="topbar"><div class="breadcrumb"><div class="mobile-brand"><img src="/favicon.svg" alt="">NEXUS</div>${icon('grid',15)}<span>好友预测房</span><span class="slash">/</span><strong>${esc(state.room.name)}</strong></div><div class="top-actions"><span class="local-pill">LOCAL ONLY</span><button class="player-switch" data-action="switch-player" aria-label="当前玩家 ${esc(me().name)}，点击切换">${avatar(me())}<div><span class="caption">当前玩家</span><strong>${esc(me().name)}</strong></div>${icon('down',14)}</button></div></header><main class="main" id="main-content"><div class="page-heading"><div><h1>${names[page]}</h1><p>${{lobby:'为主队站队，和搭子比眼光。',predictions:'每一次坚定的选择，都记在这里。',leaderboard:'赛场有胜负，友谊不掉分。',manage:'同步官方对阵，亲自设置赔率，再一起确认赛果。',settings:'让这间预测房，有你们自己的样子。'}[page]}</p></div>${['lobby','manage'].includes(page)?`<div class="toolbar"><button class="secondary-button" data-action="new-match">${icon('plus',15)}手动添加</button><button class="primary-button" data-action="sync-schedule">${icon('refresh',15)}同步官方赛程</button></div>`:`<div class="date-badge">${icon('calendar',15)}${esc(fmt(new Date(),{year:'numeric',month:'long',day:'numeric',weekday:'short'}))}</div>`}</div>${{lobby:renderLobby,predictions:renderPredictions,leaderboard:renderLeaderboard,manage:renderManage,settings:renderSettings}[page]()}<footer class="page-footer"><span>${icon('shield',12)}仅虚拟积分 · 主队对决 · 本机保存</span><span>NEXUS PICKS <span class="muted">/</span><a href="https://lolesports.com/en-GB/lolesports/pickems" target="_blank" rel="noopener noreferrer">官方 Pick’Em ${icon('arrow',10)}</a></span></footer></main></div></div>${!online?'<div class="offline-banner">本地服务暂未连接，正在重试。请保持启动窗口开启。</div>':''}`;
}

function statsHtml() {
  const p=me();
  return `<div class="stats-grid">${[
    ['可用积分',num(p.balance),'PTS','下注时扣除，结算后自动返还','wallet',''],
    ['待结算积分',num(p.locked),'PTS',`${state.bets.filter(b=>b.player_id===p.id&&b.status==='pending').length} 场预测等待揭晓`,'lock',''],
    ['累计净收益',signed(p.profit),'PTS','仅统计已结算的有效预测','up',p.profit>0?'positive':p.profit<0?'negative':''],
    ['预测命中率',p.hit_rate===null?'—':p.hit_rate+'%','',`${p.wins} 胜 / ${p.losses} 负 · ${p.wins+p.losses} 场已结算`,'target','']
  ].map(([label,value,unit,foot,ic,cls])=>`<div class="stat-card"><div class="stat-label">${label}</div><span class="stat-icon">${icon(ic,17)}</span><div class="stat-value mono ${cls}">${value}<span class="stat-unit">${unit}</span></div><div class="stat-foot">${foot}</div></div>`).join('')}</div>`;
}

function renderSlip() {
  const m=selected&&matchById(selected.matchId);
  if (!m || effectiveStatus(m)!=='open' || !readyOdds(m) || myBet(m)) selected=null;
  const rate=selected&&m['odds_'+selected.side];
  return `<section class="bet-slip" aria-label="预测单"><div class="slip-header">${icon('ticket',16)}我的预测单<span class="counter">${selected?1:0}</span></div><div class="slip-body">${selected?`<div class="slip-player">${avatar(me())}<strong>${esc(me().name)}</strong>的本次预测</div><div class="slip-selection"><button data-action="clear-slip" aria-label="移除选择">${icon('close',13)}</button><p class="slip-match">${esc(m.team_a)} <span class="muted">vs</span> ${esc(m.team_b)}</p><div class="slip-pick"><i class="dot"></i>${esc(m['team_'+selected.side])} 获胜<strong class="mono">${odds(rate)}</strong></div><p class="slip-note">${esc(m.stage)} · ${m.format} · 单场胜负</p></div><form id="bet-form"><label class="field-label" for="stake">投入积分<span>可用 ${num(me().balance)}</span></label><div class="stake-input"><input id="stake" name="stake" type="number" inputmode="numeric" min="1" max="${me().balance}" step="1" value="${selected.stake}" autocomplete="off" required><span>PTS</span></div><div class="quick-stakes">${[50,100,200].map(n=>`<button type="button" data-stake="${n}">+${n}</button>`).join('')}<button type="button" data-stake="max">全部</button></div><div id="slip-calculation">${slipCalculation()}</div><button class="primary-button full" type="submit" id="place-button" ${!validStake()?'disabled':''}>确认预测 ${icon('arrow',15)}</button><p class="slip-disclaimer">提交即扣除积分并锁定当前赔率<br>开赛自动封盘 · 每人每场一单</p></form>`:`<div class="slip-empty"><div class="empty-symbol">${icon('ticket',26)}</div><h3>你的眼光，值得下注。</h3><p>点击比赛卡片中的赔率<br>选择你支持的队伍，开始预测。</p></div>`}</div><div class="slip-education"><strong>${icon('info',13)}赔率怎么看？</strong><p>用 100 积分预测，赔率为 1.85<br>猜中返还 <b>185 积分</b>，净赚 85 积分。<br>返还包含本金，结果四舍五入到整数。</p></div></section>`;
}
function validStake() { return selected && Number.isInteger(selected.stake) && selected.stake>0 && selected.stake<=me().balance; }
function slipCalculation() {
  const m=selected&&matchById(selected.matchId), stake=validStake()?selected.stake:0;
  const gross=m?returns(stake,m['odds_'+selected.side]):0;
  return `<div class="slip-totals"><div><span>猜中净收益</span><strong class="positive mono">+${num(gross-stake)} PTS</strong></div><div class="expected"><span>预计总返还</span><strong class="mono">${num(gross)}<span class="stat-unit"> PTS</span></strong></div></div>${selected&&!validStake()?'<p class="inline-error">请输入不超过可用余额的正整数积分。</p>':''}`;
}
function renderActivity(count=5) {
  return `<section class="activity-card"><h3>房间动态</h3>${state.activity.slice(0,count).map(a=>`<div class="activity-row"><span class="activity-dot"></span><div>${esc(a.message)}<small>${esc(dateTime(a.at))}</small></div></div>`).join('') || '<p class="muted">还没有动态</p>'}</section>`;
}
function emptyState(ic,title,description,action,button) { return `<div class="empty-state">${icon(ic,28)}<h3>${title}</h3><p>${description}</p>${action?`<button class="secondary-button" data-action="${action}">${button}</button>`:''}</div>`; }

function renderPredictions() {
  const bets=state.bets.filter(b=>b.player_id===activeId&&(betFilter==='all'||(betFilter==='pending'?b.status==='pending':['won','lost','void','cancelled'].includes(b.status))));
  return `${statsHtml()}<div class="prediction-summary"><div class="filters" role="group" aria-label="预测筛选">${[['all','全部预测'],['pending','待结算'],['ended','已结束']].map(([id,name])=>`<button data-bet-filter="${id}" class="filter ${betFilter===id?'active':''}" aria-pressed="${betFilter===id}">${name}</button>`).join('')}</div><span>${esc(me().name)} 的 ${bets.length} 条记录</span></div>${bets.length?`<div class="table-wrap"><table><thead><tr><th>比赛 / 预测时间</th><th>你的选择</th><th>锁定赔率</th><th>投入积分</th><th>状态</th><th>返还 / 净收益</th><th></th></tr></thead><tbody>${bets.map(b=>{const m=matchById(b.match_id);return `<tr><td><strong>${esc(m.team_a)} vs ${esc(m.team_b)}</strong><small>${esc(dateTime(b.created_at))} · ${esc(m.stage)}</small></td><td>${esc(m['team_'+b.side])} 胜</td><td class="mono">${odds(b.odds)}</td><td class="mono">${num(b.stake)}</td><td><span class="row-status ${b.status}">${stateLabel[b.status]}</span></td><td class="mono">${b.status==='pending'?`<span class="muted">待结算</span><small>猜中返还 ${num(returns(b.stake,b.odds))}</small>`:`<strong>${num(b.payout)}</strong><small class="${b.status==='won'?'positive':b.status==='lost'?'negative':''}">${signed(b.payout-b.stake)} PTS</small>`}</td><td>${b.status==='pending'&&effectiveStatus(m)==='open'?`<button class="small-button" data-cancel-bet="${b.id}">撤回</button>`:''}</td></tr>`;}).join('')}</tbody></table></div>`:emptyState('ticket','还没有预测记录','看好哪支队伍？去比赛大厅亮出你的立场。','go-lobby','去预测')}${renderActivity(5)}`;
}

function renderLeaderboard() {
  const ranked=[...state.players].sort((a,b)=>b.assets-a.assets);
  const tied=ranked[0].assets===ranked[1].assets;
  return `<div class="info-strip">${icon('info',16)}排名按总积分比较：可用积分 + 待结算本金。预测暂未揭晓时，已投入积分仍计入总积分。</div><div class="leader-grid">${ranked.map((p,i)=>`<section class="leader-card ${i===0?'leading':''}"><div class="leader-top"><div class="leader-identity">${avatar(p)}<div><h3>${esc(p.name)}</h3><small>${p.favorite?'本命战队 · '+esc(p.favorite):'还没选本命战队'}</small></div></div><span class="leader-rank">${tied?'=1':'0'+(i+1)}</span></div><div class="leader-total mono">${num(p.assets)}<small>总积分</small></div><div class="leader-details"><div><span>累计净收益</span><strong class="mono ${p.profit>0?'positive':p.profit<0?'negative':''}">${signed(p.profit)}</strong></div><div><span>命中率</span><strong class="mono">${p.hit_rate===null?'—':p.hit_rate+'%'}</strong></div><div><span>胜 / 负</span><strong class="mono">${p.wins} / ${p.losses}</strong></div></div></section>`).join('')}</div><section class="chart-card"><div class="chart-header"><h3>积分走势</h3><div class="chart-legend">${state.players.map((p,i)=>`<span><i class="legend-dot ${i?'blue':''}"></i>${esc(p.name)}</span>`).join('')}</div></div>${renderChart()}<p class="chart-caption">以每次有效结算后的总积分绘制。取消或撤回不计胜负；撤销结算后走势同步重算。</p></section><div class="ledger-box"><div class="section-title"><h2>一起见证的每一次选择</h2><span class="eyebrow">ROOM ACTIVITY</span></div>${renderActivity(10)}</div>`;
}
function renderChart() {
  const events=state.matches.filter(m=>m.status==='settled'&&state.bets.some(b=>b.match_id===m.id&&['won','lost'].includes(b.status))).map(m=>({id:m.id,time:Math.max(...state.bets.filter(b=>b.match_id===m.id&&b.settled_at).map(b=>Date.parse(b.settled_at)))})).sort((a,b)=>a.time-b.time);
  const series=state.players.map(p=>{let total=state.room.initial_points;return [total,...events.map(e=>{total+=state.bets.filter(b=>b.player_id===p.id&&b.match_id===e.id&&['won','lost'].includes(b.status)).reduce((s,b)=>s+b.payout-b.stake,0);return total;})];});
  const all=series.flat(), padding=Math.max(100,Math.round((Math.max(...all)-Math.min(...all))*.2));
  const min=Math.max(0,Math.min(...all)-padding), max=Math.max(...all)+padding;
  const x=i=>55+(i/Math.max(1,events.length))*790,y=v=>190-((v-min)/(max-min))*170;
  let lines='';for(let i=0;i<5;i++){const value=min+(max-min)*i/4,yy=y(value);lines+=`<line x1="55" x2="845" y1="${yy}" y2="${yy}" stroke="#2a313b" stroke-dasharray="3 5"/><text x="43" y="${yy+3}" fill="#657584" text-anchor="end" font-size="10">${num(Math.round(value))}</text>`;}
  return `<svg class="chart" viewBox="0 0 870 225" role="img" aria-label="两位玩家的积分走势；当前 ${esc(state.players.map(p=>p.name+' '+p.assets+' 积分').join('，'))}">${lines}${series.map((values,i)=>`<polyline points="${values.length===1?`${x(0)},${y(values[0])} ${x(1)},${y(values[0])}`:values.map((v,j)=>`${x(j)},${y(v)}`).join(' ')}" fill="none" stroke="${i?'#91b3f2':'#c5f16d'}" stroke-width="2.5" ${!events.length&&i?'stroke-dasharray="7 7"':''}/>${values.map((v,j)=>`<circle cx="${x(j)}" cy="${y(v)}" r="3.5" fill="${i?'#91b3f2':'#c5f16d'}"><title>${esc(state.players[i].name)}：${num(v)} 积分</title></circle>`).join('')}`).join('')}<text x="55" y="217" fill="#657584" font-size="10">初始积分</text><text x="845" y="217" fill="#657584" text-anchor="end" font-size="10">${events.length?'已结算 '+events.length+' 场':'等待第一场赛果'}</text></svg>`;
}

function renderSettings() {
  return `<div class="settings-grid"><section class="panel"><h2>房间与玩家</h2><p>一个本地房间，两位观赛搭子。顶部可以随时切换当前玩家。</p><form id="settings-form"><div class="form-group"><label for="room-name">房间名称</label><input id="room-name" name="room_name" value="${esc(state.room.name)}" maxlength="24" required></div>${state.players.map(p=>`<div class="form-divider"></div><div class="settings-subtitle">${avatar(p)}玩家 ${p.id==='p1'?'01':'02'}</div><div class="form-grid"><div class="form-group"><label for="name-${p.id}">昵称</label><input id="name-${p.id}" name="name_${p.id}" value="${esc(p.name)}" maxlength="16" required></div><div class="form-group"><label for="favorite-${p.id}">本命战队</label><input id="favorite-${p.id}" name="favorite_${p.id}" value="${esc(p.favorite)}" placeholder="例如 T1" maxlength="24"></div></div>`).join('')}<div id="settings-error" class="inline-error"></div><button class="primary-button" type="submit">${icon('check',15)}保存设置</button></form></section><div><section class="panel"><h2>把回忆留好</h2><p>所有记录保存在此电脑的 data 文件夹。导出备份后，可以在另一台电脑上恢复整个房间。</p><div class="backup-buttons"><a class="secondary-button" href="/api/backup" download>${icon('download',15)}导出备份</a><button class="secondary-button" data-action="import-backup">${icon('upload',15)}导入备份</button></div><div class="form-divider"></div><div class="settings-subtitle">当前赛季</div><p class="muted">每人初始 ${num(state.room.initial_points)} 积分<br>${state.matches.length} 场比赛 · ${state.bets.length} 条预测记录</p></section><section class="panel danger-panel"><h2>开启新赛季</h2><p>清空比赛和预测记录，保留玩家昵称与本命战队。开启前建议先导出备份。</p><button class="danger-button" data-action="reset-season">${icon('refresh',14)}重置积分与赛程</button></section></div></div>`;
}

function render() {
  if (!state) return;
  const focused=$('#stake')===document.activeElement, position=focused?$('#stake').value:null;
  const searchFocused=$('#match-search')===document.activeElement, searchCursor=searchFocused?$('#match-search').selectionStart:null;
  $('#app').innerHTML=shell();
  if (focused&&$('#stake')) { $('#stake').focus({preventScroll:true});if(position!==null)$('#stake').value=position; }
  if(searchFocused&&$('#match-search')){$('#match-search').focus({preventScroll:true});if(searchCursor!==null)$('#match-search').setSelectionRange(searchCursor,searchCursor);}
  lastTimeKey=state.matches.map(m=>m.id+effectiveStatus(m)).join('');
}
function toast(message,error=false) {
  clearTimeout(toastTimer);$('#toast-root').innerHTML=`<div class="toast ${error?'error':''}">${esc(message)}</div>`;
  toastTimer=setTimeout(()=>$('#toast-root').innerHTML='',error?6500:3500);
}
function closeModal() { $('#modal-root').innerHTML='';modal=null;document.body.style.overflow='';if(modalTrigger?.isConnected)modalTrigger.focus({preventScroll:true}); }
function openModal(title,body,footer='',kind='generic') {
  modalTrigger=document.activeElement;
  modal={kind};
  $('#modal-root').innerHTML=`<div class="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><header class="modal-header"><h2 id="modal-title">${title}</h2><button class="modal-close" data-action="close-modal" aria-label="关闭">${icon('close',18)}</button></header><div class="modal-content">${body}<div class="inline-error" id="modal-error" role="alert"></div></div>${footer?`<div class="modal-actions">${footer}</div>`:''}</section></div>`;
  document.body.style.overflow='hidden';
  setTimeout(()=>{const input=$('input:not([readonly]), select, .player-choice', $('#modal-root'));(input||$('.modal-close'))?.focus({preventScroll:true});},0);
}
const modalCancel = '<button class="secondary-button" data-action="close-modal">取消</button>';
function confirmAction(title,description,action,payload,label='确认',danger=false) {
  openModal(title,`<p class="modal-description">${description}</p>`,`${modalCancel}<button class="${danger?'danger-button':'primary-button'}" data-action="confirm-mutation">${label}</button>`);
  modal.action=action;modal.payload=payload;
}
function showPlayers() {
  openModal('这次轮到谁预测？',`<p class="modal-description">两位玩家共用本机数据。这是好友互信房间，切换玩家无需密码。</p>${state.players.map(p=>`<button class="player-choice" data-player="${p.id}">${avatar(p)}<div><strong>${esc(p.name)} ${p.id===activeId?'✓':''}</strong><small>${p.favorite?'本命 · '+esc(p.favorite):'选择你的主场'}</small></div><div class="choice-points mono">${num(p.balance)}<small>可用积分</small></div></button>`).join('')}<div class="backup-buttons"><button class="text-button" data-page="settings">${icon('settings',14)}房间与玩家设置</button><button class="text-button" data-action="rules">${icon('help',14)}玩法规则</button></div>`);
}
function showRules() {
  openModal('玩得明白，赢得漂亮。',`<div class="help-content"><div><h3>01 / 选边，再选积分</h3><p>在顶部选择当前玩家，点击比赛赔率，输入投入的整数积分。每位玩家每场比赛只能有一条有效预测。提交时立即扣除积分。</p></div><div><h3>02 / 赔率在提交时锁定</h3><p>使用十进制赔率，可设置 1.01–100.00。后续调整赔率不会影响已提交预测。开赛时间一到自动封盘；也可以提前手动封盘。</p></div><div class="help-example">例如：投入 <strong>100</strong> 积分，赔率 <strong>1.85</strong><br>猜中 → 返还 <strong>185</strong>，净赚 <strong>85</strong><br>猜错 → 返还 0，净收益 −100<br>返还包含本金，四舍五入至整数。</div><div><h3>03 / 你们确认赛果，系统计算积分</h3><p>在「赛程管理」选择获胜队伍并结算。取消比赛会退还所有投入；封盘前可以撤回自己的预测。结算可撤销，但已返还的积分必须仍有足够余额收回。</p></div><div><h3>04 / 好友房间的约定</h3><p>积分由本地系统发放和结算，不要求双方选择不同队伍，也不从另一玩家账户扣除奖金。两位玩家均可管理赛程和切换身份；仅支持同一台电脑本机访问。同步官方赛程需要联网，其余预测与结算可离线使用。</p></div><div><h3>05 / 记录保存在你的电脑</h3><p>关闭页面或重启后记录仍会保留。服务启动窗口须保持开启，在房间设置里可以导出和恢复备份。赛程按北京时间（UTC+8）同步；来源未公布当日赛程时会明确报错，不生成虚构对阵。</p></div><div><h3>06 / 名称与图标从哪里来</h3><p>「NEXUS PICKS · 观赛搭子」和 N 字图标是为这个项目临时原创的文字与图形，不是现成赛事平台的品牌，也不代表 Riot 或腾讯官方。官方赛程标记仅表示对阵数据来源。</p></div></div>`);
}
function showSettlement(id) {
  const m=matchById(id);
  openModal('确认比赛结果',`<p class="modal-description">${esc(m.team_a)} vs ${esc(m.team_b)} · ${esc(m.stage)}<br>请选择实际获胜队伍。确认后将结算本场所有预测。</p><div class="settle-choices">${['a','b'].map(side=>`<button class="settle-choice" data-winner="${side}">${teamBadge(m['team_'+side])}<strong>${esc(m['team_'+side])}</strong><span>这支队伍获胜</span></button>`).join('')}</div><div class="settle-preview" id="settle-preview">请先选择获胜队伍，查看积分结算预览。</div>`,`${modalCancel}<button class="primary-button" id="settle-confirm" data-action="settle-confirm" disabled>确认赛果并结算</button>`,'settlement');
  modal.matchId=id;
}
function showReset() {
  openModal('准备开始新的赛季？',`<p class="modal-description">这会清空所有比赛、预测和积分动态。玩家信息保留。请先导出备份；清空后只能通过备份恢复。</p><a class="secondary-button" href="/api/backup" download>${icon('download',15)}先导出备份</a><form id="reset-form"><div class="form-divider"></div><div class="form-group"><label for="new-points">每位玩家的初始积分</label><input id="new-points" name="initial_points" type="number" min="1" max="1000000" step="1" value="1000" required></div><div class="form-group"><label for="reset-confirmation">输入 RESET 确认清空</label><input id="reset-confirmation" name="confirmation" placeholder="RESET" pattern="RESET" autocomplete="off" required></div></form>`,`${modalCancel}<button class="danger-button" type="submit" form="reset-form">清空并开启新赛季</button>`);
}

async function refresh(force=false) {
  const request = ++refreshRequest;
  try {
    const response=await fetch('/api/state',{cache:'no-store',signal:AbortSignal.timeout(8000)});
    if(!response.ok)throw new Error();
    const incoming=await response.json();
    if(request!==refreshRequest)return;
    const changed=!state||incoming.revision!==state.revision||!online;
    state=incoming;serverOffset=Date.parse(state.server_time)-Date.now();online=true;
    if(changed||force)render();
  } catch (_) {
    if(request!==refreshRequest)return;
    if(online){online=false;if(state)render();else $('#app').innerHTML='<div class="boot"><p>本地服务未连接。请运行「启动观赛搭子.command」，然后刷新此页。</p></div>';}
  }
}
async function mutate(action,payload,success) {
  if(busy)return false;
  busy=true;
  ++refreshRequest;
  $$('.modal button, button[type="submit"]').forEach(b=>b.disabled=true);
  try {
    const response=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json','X-Nexus-Local':'1'},body:JSON.stringify({action,payload}),signal:AbortSignal.timeout(action==='sync_schedule'?45000:15000)});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||'操作未完成，请重试。');
    state=data;serverOffset=Date.parse(data.server_time)-Date.now();online=true;
    closeModal();
    if(['place_bet','reset_season','import_backup'].includes(action))selected=null;
    render();toast(action==='sync_schedule'?`新增 ${data.sync_result?.added??0} 场，更新 ${data.sync_result?.updated??0} 场，跳过 ${data.sync_result?.skipped??0} 场；人工赔率保留。`:(success||'已保存。'));return true;
  } catch(error) {
    const message=error.name==='TimeoutError'||error.name==='TypeError'?'连接中断，请保持启动窗口开启。正在核对本机数据，可稍后重试。':error.message;
    const errorTarget=$('#modal-error')||$('#settings-error');
    if(errorTarget)errorTarget.textContent=message;
    toast(message,true);
    await refresh();return false;
  } finally {
    busy=false;
    $$('.modal button, button[type="submit"]').forEach(b=>b.disabled=false);
    if($('#place-button'))$('#place-button').disabled=!validStake();
    if($('#settle-confirm'))$('#settle-confirm').disabled=!modal?.winner;
    if(modal?.kind==='sync')syncImportCount();
  }
}

document.addEventListener('click', async event => {
  const el=event.target.closest('button, a');
  if(!el||!state||busy)return;
  if(el.dataset.page){if(location.hash==='#'+el.dataset.page){closeModal();render();}else location.hash=el.dataset.page;return;}
  if(el.dataset.filter){filter=el.dataset.filter;render();return;}
  if(el.dataset.date){scheduleDate=el.dataset.date;render();return;}
  if(el.dataset.betFilter){betFilter=el.dataset.betFilter;render();return;}
  if(el.dataset.pick){
    const picked=matchById(el.dataset.pick);if(!picked||!readyOdds(picked)||effectiveStatus(picked)!=='open')return;
    selected={matchId:el.dataset.pick,side:el.dataset.side,stake:Math.min(100,me().balance),requestId:rid()};render();
    if(innerWidth<=760)$('#slip-column')?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'});
    return;
  }
  if(el.dataset.stake){
    if(!selected)return;
    selected.stake=el.dataset.stake==='max'?me().balance:Math.min(me().balance,(Number($('#stake').value)||0)+Number(el.dataset.stake));
    $('#stake').value=selected.stake;updateCalculation();return;
  }
  if(el.dataset.player){activeId=el.dataset.player;try{localStorage.setItem('nexus-active-player',activeId);}catch(_){}selected=null;closeModal();render();toast('已切换为 '+me().name);return;}
  if(el.dataset.editMatch){showMatchEditor(el.dataset.editMatch);return;}
  if(el.dataset.settleMatch){showSettlement(el.dataset.settleMatch);return;}
  if(el.dataset.lockMatch){const m=matchById(el.dataset.lockMatch);await mutate('toggle_lock',{match_id:m.id},effectiveStatus(m)==='open'?'已封盘。':'已开放预测。');return;}
  if(el.dataset.cancelBet){const b=state.bets.find(b=>b.id===el.dataset.cancelBet);confirmAction('撤回这次预测？',`将退回 <strong>${num(b.stake)}</strong> 积分。你可以在封盘前重新选择。`,'cancel_bet',{bet_id:b.id},'撤回并退回积分');return;}
  if(el.dataset.voidMatch){const m=matchById(el.dataset.voidMatch);confirmAction('取消这场比赛？',`${esc(m.team_a)} vs ${esc(m.team_b)}<br>本场所有预测将作废，已投入积分全额退回。`,'void_match',{match_id:m.id},'取消比赛并退款',true);return;}
  if(el.dataset.undoMatch){const m=matchById(el.dataset.undoMatch);confirmAction('撤销本场结算？',`${esc(m.team_a)} vs ${esc(m.team_b)}<br>系统将收回本场返还积分，恢复为待结算，并保持封盘。如返还积分已被使用而余额不足，撤销将被阻止。`,'undo_settlement',{match_id:m.id},'撤销结算',true);return;}
  if(el.dataset.winner){
    modal.winner=el.dataset.winner;$$('.settle-choice').forEach(b=>b.classList.toggle('selected',b.dataset.winner===modal.winner));
    const bs=state.bets.filter(b=>b.match_id===modal.matchId&&b.status==='pending');
    $('#settle-preview').innerHTML=bs.length?bs.map(b=>{const p=state.players.find(p=>p.id===b.player_id),gross=b.side===modal.winner?returns(b.stake,b.odds):0;return `<div><span>${esc(p.name)} · 投入 ${num(b.stake)} @ ${odds(b.odds)}</span><strong class="${gross?'positive':'negative'}">返还 ${num(gross)} <small>(${signed(gross-b.stake)})</small></strong></div>`;}).join(''):'本场还没有预测，确认后仅记录赛果。';
    $('#settle-confirm').disabled=false;return;
  }
  switch(el.dataset.action){
    case 'switch-player':showPlayers();break;
    case 'rules':showRules();break;
    case 'clear-slip':selected=null;render();break;
    case 'close-modal':closeModal();break;
    case 'new-match':showMatchEditor();break;
    case 'sync-schedule':showScheduleSync();break;
    case 'clear-filters':filter='all';scheduleDate='all';searchTerm='';onlyFavorite=false;render();break;
    case 'toggle-favorites':if(!me().favorite.trim()){toast('请先在房间设置中填写你的本命战队。');return;}onlyFavorite=!onlyFavorite;render();break;
    case 'sync-import':{const ids=$$('[data-source-id]:checked', $('#modal-root')).map(x=>x.dataset.sourceId);if(!ids.length||!modal.loadedDate)return;await mutate('sync_schedule',{date:modal.loadedDate,source_ids:ids},'官方赛程已导入，请手动设置赔率。');break;}
    case 'go-lobby':location.hash='lobby';break;
    case 'clear-examples':confirmAction('移除示例赛程？','只会移除尚无预测记录的示例比赛。已经参与的比赛与积分记录会保留。','clear_examples',{},'移除示例');break;
    case 'confirm-mutation':await mutate(modal.action,modal.payload,'操作完成，积分账本已更新。');break;
    case 'settle-confirm':if(modal.winner)await mutate('settle_match',{match_id:modal.matchId,winner:modal.winner},'赛果已确认，积分结算完成！');break;
    case 'import-backup':$('#backup-file').click();break;
    case 'import-confirm':await mutate('import_backup',{backup:modal.backup},'备份已恢复。');break;
    case 'reset-season':showReset();break;
  }
});
function updateCalculation(){if(!selected)return;$('#slip-calculation').innerHTML=slipCalculation();$('#place-button').disabled=!validStake();}
document.addEventListener('input',event=>{if(event.target.id==='stake'&&selected){selected.stake=Number(event.target.value);updateCalculation();}if(event.target.id==='match-search'){searchTerm=event.target.value;render();}});
document.addEventListener('change',event=>{if(event.target.id==='schedule-date'){scheduleDate=event.target.value||'all';render();}if(event.target.matches('[data-source-id]'))syncImportCount();if(event.target.id==='sync-all'){$$('[data-source-id]:not(:disabled)', $('#modal-root')).forEach(x=>x.checked=event.target.checked);syncImportCount();}if(event.target.id==='sync-date'&&modal?.kind==='sync'){modal.results=[];modal.loadedDate=null;modal.requestToken=null;modal.loading=false;$('#sync-fetch').disabled=false;$('#sync-fetch').innerHTML=icon('refresh',14)+'获取赛程';$('#sync-preview').innerHTML='<div class="sync-placeholder"><span>日期已更改，请重新获取赛程。</span></div>';$('#sync-import').disabled=true;$('#modal-error').textContent='';}});
document.addEventListener('submit',async event=>{
  const form=event.target;event.preventDefault();if(!state||busy)return;
  const d=Object.fromEntries(new FormData(form));
  if(form.id==='sync-form'){await fetchOfficialSchedule(d.date);return;}
  if(form.id==='bet-form'){
    if(!validStake())return;
    const m=matchById(selected.matchId);
    await mutate('place_bet',{player_id:activeId,match_id:m.id,side:selected.side,stake:selected.stake,expected_odds:m['odds_'+selected.side],request_id:selected.requestId},'预测成功！积分已扣除，赔率已锁定。');
  } else if(form.id==='match-form') {
    if(Boolean(d.odds_a.trim())!==Boolean(d.odds_b.trim())){$('#modal-error').textContent='请同时填写双方赔率，或同时留空。';return;}
    const payload={...d,format:d.format||modal.originalFormat,starts_at:new Date(d.starts_at).toISOString(),odds_a:d.odds_a.trim()?Math.round(Number(d.odds_a)*100):null,odds_b:d.odds_b.trim()?Math.round(Number(d.odds_b)*100):null};
    if(modal.matchId)payload.match_id=modal.matchId;
    await mutate(modal.matchId?'edit_match':'create_match',payload,'比赛已保存。');
  } else if(form.id==='settings-form') {
    await mutate('settings',{room_name:d.room_name,p1:{name:d.name_p1,favorite:d.favorite_p1},p2:{name:d.name_p2,favorite:d.favorite_p2}},'房间与玩家信息已保存。');
  } else if(form.id==='reset-form') {
    await mutate('reset_season',{initial_points:Number(d.initial_points),confirmation:d.confirmation},'新赛季已开启。');
  }
});
$('#backup-file').addEventListener('change',async event=>{
  const file=event.target.files[0];event.target.value='';if(!file)return;
  try{
    if(file.size>10_000_000)throw new Error('备份文件不能超过 10 MB。');
    const backup=JSON.parse(await file.text());
    if(backup.version!==1||!backup.room||!Array.isArray(backup.players)||!Array.isArray(backup.matches)||!Array.isArray(backup.bets))throw new Error('这不是有效的 Nexus Picks v1 备份。');
    openModal('用备份恢复房间？',`<p class="modal-description">备份房间：<strong>${esc(backup.room.name)}</strong><br>${backup.matches.length} 场比赛 · ${backup.bets.length} 条预测<br><br>导入将替换当前房间的全部比赛、玩家与积分记录。建议先导出当前房间备份。</p><a class="secondary-button" href="/api/backup" download>${icon('download',15)}先备份当前房间</a>`,`${modalCancel}<button class="danger-button" data-action="import-confirm">替换并恢复</button>`);
    modal.backup=backup;
  }catch(error){toast(error instanceof SyntaxError?'备份文件不是有效 JSON，本机数据未被修改。':error.message,true);}
});
document.addEventListener('keydown',event=>{
  if(!modal)return;
  if(event.key==='Escape'&&!busy){closeModal();return;}
  if(event.key==='Tab'){
    const items=$$('button:not(:disabled), input:not(:disabled), select:not(:disabled), a[href]', $('#modal-root')).filter(x=>x.getClientRects().length),first=items[0],last=items[items.length-1];
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
  }
});
document.addEventListener('click',event=>{if(event.target.classList.contains('modal-backdrop')&&!busy)closeModal();});
window.addEventListener('hashchange',()=>{const next=location.hash.slice(1);page=['lobby','predictions','leaderboard','manage','settings'].includes(next)?next:'lobby';closeModal();render();window.scrollTo({top:0,behavior:'instant'});});
window.addEventListener('focus',()=>{if(!busy)refresh();});
setInterval(()=>{if(!document.hidden&&!busy)refresh();},5000);
setInterval(()=>{if(state&&!modal&&!busy){const key=state.matches.map(m=>m.id+effectiveStatus(m)).join('');if(key!==lastTimeKey)render();}},1000);

function renderLobby() {
  const pendingSetup=state.matches.filter(m=>effectiveStatus(m)==='open'&&!readyOdds(m)).length;
  const scoped=state.matches.filter(m=>(scheduleDate==='all'||dayKey(m.starts_at)===scheduleDate)&&(!onlyFavorite||matchesFavorite(m))&&(!searchTerm||`${m.team_a} ${m.team_b} ${m.stage}`.toLowerCase().includes(searchTerm.toLowerCase())));
  const matches=scoped.filter(m=>matchesFilter(m)).sort((a,b)=>Date.parse(a.starts_at)-Date.parse(b.starts_at));
  const futureCount=state.matches.filter(m=>effectiveStatus(m)==='open'&&readyOdds(m)).length;
  return `<div class="lobby-banner"><div><span class="eyebrow">YOUR MATCHDAY, YOUR CALL.</span><h2>为主队站队，<span>和搭子比眼光。</span></h2><p>${state.matches.length?`${futureCount} 场可预测${pendingSetup?` · ${pendingSetup} 场待设置`:''}`:'从官方同步赛程，或手动安排你们想看的对局。'}</p></div><div class="banner-rivalry">${state.players.map((p,i)=>`${i?'<span class="rivalry-vs">VS</span>':''}<div>${avatar(p)}<span>${esc(p.name)}</span><strong class="mono">${num(p.assets)}<small>总积分</small></strong></div>`).join('')}</div></div>${statsHtml()}<div class="content-grid"><section class="schedule-main"><div class="section-title"><h2>比赛日程<span class="count">${state.matches.length}</span></h2><span class="timezone-label">北京时间 UTC+8</span></div>${renderScheduleControls()}<div class="schedule-filters"><div class="filters" role="group" aria-label="比赛筛选">${[['all','全部'],['open','可预测'],['setup','待设置'],['locked','待结算'],['ended','已结束']].map(([id,name])=>`<button class="filter ${filter===id?'active':''}" data-filter="${id}" aria-pressed="${filter===id}">${name}<small>${scoped.filter(m=>matchesFilter(m,id)).length}</small></button>`).join('')}</div></div>${pendingSetup&&filter!=='ended'&&filter!=='locked'?`<div class="setup-callout">${icon('settings',15)}<span><strong>${pendingSetup} 场比赛等待你设置赔率</strong> · 同步不会自动生成赔率</span><button data-filter="setup">去设置 ${icon('arrow',12)}</button></div>`:''}<div id="match-results">${renderMatchGroups(matches)}</div><p class="demo-notice">${icon('info',13)}<span>赛程来源 <a href="https://lpl.qq.com/" target="_blank" rel="noopener noreferrer">lpl.qq.com</a> · 赔率由你们设置 · 赛果由你们确认。${state.matches.some(m=>m.demo)?'旧版示例不代表真实赛程。':''}</span></p></section><aside class="slip-column ${selected?'has-selection':''}" id="slip-column">${renderSlip()}${renderActivity(3)}</aside></div>`;
}
function renderScheduleControls() {
  const today=todayKey(), tomorrow=dayKey(new Date(today+'T00:00:00+08:00').getTime()+86400000);
  const dates=[...new Set([today,tomorrow,...state.matches.map(m=>dayKey(m.starts_at)),...(scheduleDate==='all'?[]:[scheduleDate])])].sort();
  const index=Math.max(0,dates.indexOf(scheduleDate==='all'?today:scheduleDate)-2);
  const displayed=dates.length<=7?dates:dates.slice(index,index+7);
  return `<div class="schedule-tools"><div class="date-strip" role="group" aria-label="比赛日期"><button class="date-chip ${scheduleDate==='all'?'active':''}" data-date="all" aria-pressed="${scheduleDate==='all'}"><strong>全部</strong><small>所有日期</small></button>${displayed.map(d=>`<button class="date-chip ${scheduleDate===d?'active':''}" data-date="${d}" aria-pressed="${scheduleDate===d}"><strong>${d===today?'今天':d===tomorrow?'明天':d.slice(5).replace('-',' / ')}</strong><small>${state.matches.filter(m=>dayKey(m.starts_at)===d).length} 场比赛</small></button>`).join('')}</div><div class="search-row"><button class="favorite-filter ${onlyFavorite?'active':''}" data-action="toggle-favorites" aria-pressed="${onlyFavorite}">${icon('spark',13)}我的主队</button><label class="match-search" for="match-search">${icon('target',15)}<input id="match-search" type="search" placeholder="搜索战队或赛事阶段" value="${esc(searchTerm)}" autocomplete="off"><span class="sr-only">搜索战队或赛事阶段</span></label><label class="date-picker-label" for="schedule-date">${icon('calendar',14)}<input id="schedule-date" type="date" aria-label="选择比赛日期" value="${scheduleDate==='all'?'':scheduleDate}"></label></div></div>`;
}
function renderMatchGroups(matches) {
  if(!matches.length)return `<div class="empty-state schedule-empty">${icon('calendar',31)}<h3>${state.matches.length?'这个筛选下还没有比赛':'你们的比赛日，从这里开始。'}</h3><p>${state.matches.length?'换个日期或筛选条件，也可以同步其他比赛日的官方赛程。':'选择日期，从英雄联盟赛事官网导入对阵。<br>导入后亲自设置赔率，便能开始你们的双人预测。'}</p><div class="empty-actions"><button class="primary-button" data-action="sync-schedule">${icon('refresh',15)}同步官方赛程</button><button class="secondary-button" data-action="new-match">${icon('plus',15)}手动添加</button>${state.matches.length?'<button class="text-button" data-action="clear-filters">清除筛选</button>':''}</div></div>`;
  const groups=new Map();matches.forEach(m=>{const key=dayKey(m.starts_at);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(m);});
  return [...groups].map(([date,items])=>`<section class="match-day"><div class="match-day-heading"><h3>${esc(dayLabel(date))}</h3><span>${items.length} 场对决</span></div><div class="match-grid">${items.map(renderMatch).join('')}</div></section>`).join('');
}
function renderMatch(m) {
  const s=effectiveStatus(m), bet=myBet(m), count=state.bets.filter(b=>b.match_id===m.id&&b.status!=='cancelled').length, ready=readyOdds(m);
  const sourceState=officialMatch(m)?{upcoming:'官方未开始',ongoing:'官方进行中',finished:'官方已结束'}[m.source_status]:null;
  return `<article class="match-card ${!ready&&s==='open'?'match-needs-odds':''}"><div class="match-meta"><span><span class="format">${esc(m.format)}</span>${esc(clockTime(m.starts_at))}</span>${statusHtml(m)}</div><div class="match-stage"><span>${esc(m.stage)}</span>${sourceCaption(m)}</div><div class="match-teams">${['a','b'].map((side,i)=>`${i?'<div class="versus">VS</div>':''}<div class="team-col">${teamBadge(m['team_'+side])}<strong class="team-title" title="${esc(m['team_'+side])}">${esc(m['team_'+side])}</strong><span class="team-region">${esc(team(m['team_'+side]).region)}</span>${favoriteTag(m['team_'+side])}</div>`).join('')}</div>${ready?`<div class="match-odds">${['a','b'].map(side=>`<button class="odds-button ${selected?.matchId===m.id&&selected.side===side?'selected':''}" data-pick="${m.id}" data-side="${side}" ${s!=='open'||bet?'disabled':''} aria-label="支持 ${esc(m['team_'+side])}，赔率 ${odds(m['odds_'+side])}"><span>${esc(m['team_'+side])} 胜</span><strong class="mono">${odds(m['odds_'+side])}</strong></button>`).join('')}</div>`:`<div class="pending-odds"><span>${icon('settings',13)}${m.format==='待确认'?'赛制与赔率待设置':'双方赔率由你来定'}</span>${['open','locked'].includes(s)?`<button class="small-button" data-edit-match="${m.id}">设置赔率 ${icon('arrow',11)}</button>`:'<span>未设赔率</span>'}</div>`}<div class="match-card-footer"><span>${icon('users',11)}${count} / 2 人已预测</span>${bet?`<span class="your-pick">${icon('check',11)}已支持 ${esc(m['team_'+bet.side])}</span>`:m.winner?`<span class="winner-label">${icon('trophy',11)}${esc(m['team_'+m.winner])} 获胜</span>`:`<span>${sourceState||(s==='open'?(ready?'点击赔率预测':'设置后开放预测'):s==='locked'?'等待手动结算':'已结束')}</span>`}</div></article>`;
}
function renderManage() {
  const matches=[...state.matches].sort((a,b)=>Date.parse(a.starts_at)-Date.parse(b.starts_at));
  const setup=matches.filter(m=>!readyOdds(m)&&!['settled','void'].includes(effectiveStatus(m))).length;
  return `<div class="workflow-strip"><div><span>01</span><strong>同步官方赛程</strong><small>按日期挑选对局</small></div>${icon('chevron',14)}<div><span>02</span><strong>亲自设置赔率</strong><small>${setup?`${setup} 场待设置`:'不自动生成赔率'}</small></div>${icon('chevron',14)}<div><span>03</span><strong>赛后确认结果</strong><small>积分自动结算</small></div></div><div class="info-strip">${icon('shield',16)}同步只获取对阵、时间与赛制，不设置赔率，也不自动结算。已有预测始终按提交时的赔率结算。${state.matches.some(m=>m.demo)?'<button class="text-button" data-action="clear-examples">移除旧版示例</button>':''}</div>${matches.length?`<div class="table-wrap"><table><thead><tr><th>对阵 / 来源</th><th>开赛时间 · UTC+8</th><th>赔率 A / B</th><th>状态</th><th>预测人数</th><th>管理</th></tr></thead><tbody>${matches.map(m=>{const s=effectiveStatus(m),n=state.bets.filter(b=>b.match_id===m.id&&b.status!=='cancelled').length;return `<tr><td><strong>${esc(m.team_a)} <span class="muted">vs</span> ${esc(m.team_b)}</strong><small>${esc(m.stage)} · ${esc(m.format)}</small><div class="manage-source">${sourceCaption(m)}</div></td><td class="mono">${esc(dateTime(m.starts_at))}</td><td class="mono">${readyOdds(m)?`${odds(m.odds_a)} <span class="muted">/</span> ${odds(m.odds_b)}`:'<span class="odds-pending-label">待设置</span>'}</td><td>${statusHtml(m)}${m.winner?`<small class="positive">${esc(m['team_'+m.winner])} 胜</small>`:''}</td><td>${n} / 2</td><td><div class="table-actions">${['open','locked'].includes(s)?`<button class="small-button ${!readyOdds(m)?'emphasis':''}" data-edit-match="${m.id}">${readyOdds(m)?'编辑':'设置赔率'}</button><button class="small-button" data-lock-match="${m.id}" ${s==='locked'&&Date.parse(m.starts_at)<=Date.now()+serverOffset?'disabled':''}>${s==='open'?'封盘':'开放'}</button><button class="small-button" data-settle-match="${m.id}">结算</button><button class="small-button warn" data-void-match="${m.id}">取消比赛</button>`:`<button class="small-button warn" data-undo-match="${m.id}">撤销结算</button>`}</div></td></tr>`;}).join('')}</tbody></table></div>`:renderMatchGroups([])}`;
}
function showScheduleSync() {
  openModal('同步官方赛程',`<div class="sync-intro"><span class="sync-source">${icon('shield',14)}lpl.qq.com 官方赛程</span><p>选择比赛日期，预览后勾选想加入房间的对局。导入后由你设置赔率。</p></div><form id="sync-form"><div class="sync-date-row"><div class="form-group"><label for="sync-date">比赛日期 · 北京时间 UTC+8</label><input id="sync-date" name="date" type="date" value="${scheduleDate==='all'?todayKey():scheduleDate}" required></div><button class="secondary-button" type="submit" id="sync-fetch">${icon('refresh',14)}获取赛程</button></div></form><div id="sync-preview"><div class="sync-placeholder">${icon('calendar',24)}<span>先选择日期并获取官方赛程</span><small>未公布赛程时会返回错误，不使用示例数据填补。</small></div></div>`,`${modalCancel}<button class="primary-button" id="sync-import" data-action="sync-import" disabled>导入或更新所选比赛</button>`,'sync');
  modal.results=[];modal.loadedDate=null;
}
function syncImportCount() {
  const count=$$('[data-source-id]:checked', $('#modal-root')).length;
  const button=$('#sync-import');if(button){button.disabled=!count||busy;button.textContent=count?`导入或更新 ${count} 场比赛`:'导入或更新所选比赛';}
  const options=$$('[data-source-id]:not(:disabled)', $('#modal-root')),all=$('#sync-all');if(all){all.checked=options.length>0&&count===options.length;all.indeterminate=count>0&&count<options.length;}
}
function officialStarted(m) {
  return Date.parse(m.starts_at)<=Date.now()+serverOffset||['ongoing','finished'].includes(m.source_status);
}
function syncResultsHtml(data) {
  const items=data.matches, canChoose=items.length;
  return `${data.warnings?.length?`<div class="sync-warnings">${data.warnings.map(w=>`<p>${icon('info',12)}${esc(w)}</p>`).join('')}</div>`:''}<div class="sync-result-heading"><strong>${esc(dayLabel(data.date))}<small>${items.length} 场官方对局</small></strong><label class="select-all"><input id="sync-all" type="checkbox" ${!canChoose?'disabled':''}>全选比赛</label></div><div class="sync-match-list">${items.map(m=>{const imported=Boolean(m.existing_id),started=officialStarted(m);return `<label class="sync-match-row ${imported?'already-imported':''}"><input type="checkbox" data-source-id="${esc(m.source_id)}" ${!imported&&!started?'checked':''}><div class="sync-match-details"><div><strong>${esc(m.team_a)} <span>vs</span> ${esc(m.team_b)}</strong><span class="sync-row-state ${imported?'imported':''}">${imported?'已导入 · 可更新':started?'已开始 · 导入后封盘':'未开始'}</span></div><small>${esc(clockTime(m.starts_at))} · ${esc(m.stage)} · ${esc(m.format)}</small></div></label>`;}).join('')}</div><p class="sync-footnote">${icon('info',12)}导入不包含赔率或预测记录。勾选已导入对局可更新官方时间和比分，保留人工赔率；已结算或取消的比赛跳过。已开始的比赛导入后封盘。</p>`;
}
async function fetchOfficialSchedule(date) {
  const current=modal;if(current?.kind!=='sync')return;
  current.results=[];current.loadedDate=null;current.loading=true;current.requestToken=rid();const token=current.requestToken;
  const button=$('#sync-fetch');button.disabled=true;button.innerHTML=icon('refresh',14)+'获取中…';
  $('#modal-error').textContent='';$('#sync-import').disabled=true;
  $('#sync-preview').innerHTML='<div class="sync-placeholder loading"><span class="loading-ring"></span><span>正在查询官方赛程…</span><small>正在从 lpl.qq.com 使用的官方数据源获取对阵。</small></div>';
  try{
    const response=await fetch('/api/schedule?date='+encodeURIComponent(date),{cache:'no-store',signal:AbortSignal.timeout(20000)});
    const data=await response.json();if(modal!==current||current.requestToken!==token||$('#sync-date')?.value!==date)return;
    if(!response.ok)throw new Error(data.error||'无法获取这一天的官方赛程，请稍后重试。');
    if(!Array.isArray(data.matches)||!data.matches.length)throw new Error('官方尚未公布所选日期的赛程，或当天没有比赛。请选择其他日期。');
    current.results=data.matches;current.loadedDate=data.date||date;
    $('#sync-preview').innerHTML=syncResultsHtml({...data,date:data.date||date});syncImportCount();
  }catch(error){
    if(modal!==current||current.requestToken!==token||$('#sync-date')?.value!==date)return;
    $('#modal-error').textContent=error.name==='TimeoutError'?'官方赛程获取超时，请检查网络后重试。':error.name==='TypeError'?'无法连接官方数据源，请检查网络或本地服务后重试。':error.message;
    $('#sync-preview').innerHTML='<div class="sync-placeholder sync-failed">'+icon('calendar',24)+'<span>这一天的赛程未能获取</span><small>请更换日期或稍后重试。当前房间没有被修改。</small></div>';
  }finally{
    if(modal===current&&current.requestToken===token){current.loading=false;button.disabled=false;button.innerHTML=icon('refresh',14)+'重新获取';}
  }
}
function showMatchEditor(id) {
  const m=id&&matchById(id), hasBets=m&&state.bets.some(b=>b.match_id===id), fixed=hasBets||(m&&officialMatch(m));
  const date=new Date(m?m.starts_at:Date.now()+86400000);date.setMinutes(date.getMinutes()-date.getTimezoneOffset());
  const localDate=date.toISOString().slice(0,16), unknown=m?.format==='待确认';
  openModal(m?(readyOdds(m)?'编辑比赛':'设置赛制与赔率'):'安排下一场对决',`<form id="match-form">${hasBets?'<p class="modal-description">已有预测，对阵、阶段和赛制已锁定。更新赔率仅影响后续预测；调整时间可用于比赛延期。</p>':m&&officialMatch(m)?'<p class="modal-description">对阵来自 lpl.qq.com，双方赔率由你手动设置。官方未公布赛制时，请先确认赛制。</p>':''}<div class="form-grid"><div class="form-group"><label for="team-a">队伍 A</label><input id="team-a" name="team_a" placeholder="例如 T1" maxlength="24" value="${esc(m?.team_a||'')}" required ${fixed?'readonly':''}></div><div class="form-group"><label for="team-b">队伍 B</label><input id="team-b" name="team_b" placeholder="例如 BLG" maxlength="24" value="${esc(m?.team_b||'')}" required ${fixed?'readonly':''}></div></div><div class="form-grid"><div class="form-group"><label for="stage">赛事阶段</label><input id="stage" name="stage" placeholder="例如 瑞士轮 · 第三轮" maxlength="48" value="${esc(m?.stage||'瑞士轮')}" required ${fixed?'readonly':''}></div><div class="form-group"><label for="format">赛制</label><select id="format" name="format" required ${hasBets?'disabled':''}>${unknown?'<option value="" selected disabled>官方未公布，请确认赛制</option>':''}${['BO1','BO3','BO5'].map(f=>`<option ${f===(m?.format||'BO3')?'selected':''}>${f}</option>`).join('')}</select></div></div><div class="form-group"><label for="starts-at">开赛时间（电脑本地时间）</label><input id="starts-at" name="starts_at" type="datetime-local" value="${localDate}" required><small>到达开赛时间自动封盘。填写过去时间时，该比赛立即封盘。</small></div><div class="form-grid"><div class="form-group"><label for="odds-a">队伍 A 获胜赔率</label><input id="odds-a" name="odds_a" type="number" min="1.01" max="100" step="0.01" value="${m&&m.odds_a?odds(m.odds_a):''}" placeholder="由你设置，如 1.85" ${hasBets?'required':''}></div><div class="form-group"><label for="odds-b">队伍 B 获胜赔率</label><input id="odds-b" name="odds_b" type="number" min="1.01" max="100" step="0.01" value="${m&&m.odds_b?odds(m.odds_b):''}" placeholder="由你设置，如 2.10" ${hasBets?'required':''}></div></div><p class="editor-odds-note">可同时留空，稍后再填。双方赔率设置完成后才允许预测，已有预测仍按原赔率结算。</p></form>`,`${modalCancel}<button class="primary-button" type="submit" form="match-form">${m?'保存修改':'创建比赛'}</button>`,'match');
  modal.matchId=id||null;modal.originalFormat=m?.format;
}

refresh();
