/* global MK */

// Stable guest ID persisted in localStorage
if (!localStorage.getItem('mk_guest_id')) {
    localStorage.setItem('mk_guest_id', 'g-' + Math.random().toString(36).slice(2) + Date.now().toString(36));
}
const MK_GUEST_ID = localStorage.getItem('mk_guest_id');

const api = {
    get: (path) => fetch(MK.apiBase + path, {
        headers: { 'X-WP-Nonce': MK.nonce, 'X-MK-Guest': MK_GUEST_ID },
    }).then(r => r.json()),
    post: (path, body) => fetch(MK.apiBase + path, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-WP-Nonce': MK.nonce,
            'X-MK-Guest': MK_GUEST_ID,
        },
        body: JSON.stringify(body),
    }).then(r => r.json()),
};

// ── Home Page ─────────────────────────────────────────────────────────────────
if (document.getElementById('mk-home')) {
    const $ = id => document.getElementById(id);

    $('mk-btn-create').addEventListener('click', () => {
        $('mk-create-panel').classList.toggle('mk-hidden');
        $('mk-browse-panel').classList.add('mk-hidden');
    });

    $('mk-btn-browse').addEventListener('click', () => {
        $('mk-browse-panel').classList.toggle('mk-hidden');
        $('mk-create-panel').classList.add('mk-hidden');
        loadTables();
    });

    $('mk-search').addEventListener('input', debounce(loadTables, 300));

    async function loadTables() {
        const q = $('mk-search').value;
        const tables = await api.get('/tables?search=' + encodeURIComponent(q));
        $('mk-table-list').innerHTML = tables.map(t => `
            <div class="mk-table-row">
                <div>
                    <div class="mk-table-info">${esc(t.name)} ${t.has_password ? '🔒' : ''}</div>
                    <div class="mk-table-meta">${t.player_count}/5 players</div>
                </div>
                <button class="mk-btn mk-btn-primary" onclick="joinByCode('${esc(t.code)}')">Join</button>
            </div>`).join('');
    }

    $('mk-btn-join-code').addEventListener('click', () => {
        const code = $('mk-join-code').value.trim().toUpperCase();
        if (code) joinByCode(code);
    });

    window.joinByCode = async (code) => {
        const table = await api.get('/tables/' + code);
        if (!table.code) { showJoinError('Table not found.'); return; }
        if (table.status !== 'waiting') { showJoinError('This game has already started.'); return; }
        const guestName = $('mk-guest-name')?.value || 'Guest';
        const res = await api.post('/tables/' + code + '/join', { guest_name: guestName });
        if (res.seat !== undefined) {
            sessionStorage.setItem('mk_code', code);
            sessionStorage.setItem('mk_seat', res.seat);
            window.location.href = '/waiting-room/?code=' + code;
        } else {
            showJoinError(res.message || 'Could not join table.');
        }
    };

    function showJoinError(msg) {
        const el = document.createElement('p');
        el.className = 'mk-error-msg';
        el.textContent = msg;
        el.style.textAlign = 'center';
        $('mk-home').appendChild(el);
        setTimeout(() => el.remove(), 3500);
    }

    async function createTable(isPublic) {
        const body = {
            name:       $('mk-table-name').value || 'Machi Koro Table',
            is_public:  isPublic,
            guest_name: $('mk-guest-name')?.value || 'Guest',
        };
        const res = await api.post('/tables', body);
        if (res.code) {
            sessionStorage.setItem('mk_code', res.code);
            sessionStorage.setItem('mk_seat', 0);
            window.location.href = '/waiting-room/?code=' + res.code;
        } else {
            alert(res.message || 'Could not create table.');
        }
    }
    $('mk-btn-create-public').addEventListener('click',  () => createTable(true));
    $('mk-btn-create-private').addEventListener('click', () => createTable(false));
}

// ── Waiting Room ──────────────────────────────────────────────────────────────
if (document.getElementById('mk-waiting-room')) {
    const $ = id => document.getElementById(id);
    const params = new URLSearchParams(window.location.search);
    const code   = params.get('code') || sessionStorage.getItem('mk_code');
    let ws, cachedPlayers = [];

    $('mk-table-code').textContent = code;
    $('mk-btn-copy-code').addEventListener('click', () => navigator.clipboard.writeText(code));
    $('mk-btn-leave').addEventListener('click', () => { ws?.close(); window.location.href = MK.homeUrl; });

    async function init() {
        const table = await api.get('/tables/' + code);
        renderPlayers(table.players);

        // Show start button only for host (seat 0)
        if (sessionStorage.getItem('mk_seat') === '0') {
            $('mk-btn-start').classList.remove('mk-hidden');
        }

        connectWS();
    }

    function connectWS() {
        const seat = sessionStorage.getItem('mk_seat') || '0';
        ws = new WebSocket(MK.wsUrl + code + '/lobby/' + seat);
        ws.onmessage = (e) => {
            const msg = JSON.parse(e.data);
            const mySeat = sessionStorage.getItem('mk_seat');

            if (msg.event === 'player_left') {
                const leaving = cachedPlayers.find(p => String(p.seat) === String(msg.seat));
                if (leaving && String(msg.seat) !== mySeat) {
                    showLobbyToast(`${esc(leaving.display_name)} left the table.`);
                }
                api.get('/tables/' + code).then(t => renderPlayers(t.players));
            }

            if (['player_joined','player_renamed'].includes(msg.event)) {
                api.get('/tables/' + code).then(t => renderPlayers(t.players));
            }

            if (msg.event === 'player_kicked') {
                if (String(msg.seat) === mySeat) {
                    showKickedOverlay();
                } else {
                    api.get('/tables/' + code).then(t => renderPlayers(t.players));
                }
            }
            if (msg.event === 'table_closed') {
                showTableClosedOverlay();
            }
            if (msg.event === 'game_started') {
                window.location.href = '/game/?code=' + code;
            }
        };
    }

    function showKickedOverlay() {
        ws?.close();
        const overlay = document.createElement('div');
        overlay.id = 'mk-kicked-overlay';
        overlay.innerHTML = `
            <div id="mk-kicked-box">
                <h2>You were kicked</h2>
                <p>The host removed you from the table.</p>
                <p style="font-size:13px;color:#7f8c8d;margin-top:16px">Returning to lobby in 3 seconds…</p>
            </div>`;
        document.body.appendChild(overlay);
        setTimeout(() => { window.location.href = MK.homeUrl; }, 3000);
    }

    function showTableClosedOverlay() {
        ws?.close();
        const overlay = document.createElement('div');
        overlay.id = 'mk-kicked-overlay';
        overlay.innerHTML = `
            <div id="mk-kicked-box">
                <h2>Table Closed</h2>
                <p>The host left and the table has been closed.</p>
                <p style="font-size:13px;color:#7f8c8d;margin-top:16px">Returning to lobby in 3 seconds…</p>
            </div>`;
        document.body.appendChild(overlay);
        setTimeout(() => { window.location.href = MK.homeUrl; }, 3000);
    }

    function showLobbyToast(msg) {
        let container = document.getElementById('mk-lobby-toast');
        if (!container) {
            container = document.createElement('div');
            container.id = 'mk-lobby-toast';
            container.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:1000;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
            document.body.appendChild(container);
        }
        const el = document.createElement('div');
        el.className = 'mk-toast';
        el.textContent = msg;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }

    function renderPlayers(players) {
        cachedPlayers = players;
        const mySeat    = sessionStorage.getItem('mk_seat');
        const myIsHost  = players.some(p => p.is_host == 1 && String(p.seat) === mySeat);

        $('mk-player-list').innerHTML = players.map(p => {
            const isMine  = String(p.seat) === mySeat;
            const isGuest = !parseInt(p.user_id);
            return `<div class="mk-player-row">
                ${p.is_host == 1 ? '<span class="mk-crown">👑</span>' : '<span style="width:22px"></span>'}
                <span class="mk-player-name" data-seat="${p.seat}">${esc(p.display_name)}</span>
                <span class="mk-badge ${isGuest ? 'mk-badge-guest' : ''}">${isGuest ? 'Guest' : 'Registered'}</span>
                ${isMine && isGuest ? `<button class="mk-btn-small" onclick="editGuestName(${p.seat})">✏️</button>` : ''}
                ${myIsHost && !isMine ? `<button class="mk-btn-small" style="color:#c0392b" onclick="kickPlayer(${p.id})">✕</button>` : ''}
            </div>`;
        }).join('');

        const startBtn = $('mk-btn-start');
        if (!startBtn.classList.contains('mk-hidden')) {
            startBtn.disabled = players.length < 2;
        }
    }

    window.editGuestName = (seat) => {
        const nameEl = document.querySelector(`.mk-player-name[data-seat="${seat}"]`);
        if (!nameEl) return;
        const oldName = nameEl.textContent;
        const input   = document.createElement('input');
        input.type      = 'text';
        input.value     = oldName;
        input.className = 'mk-name-input';
        input.maxLength = 64;
        nameEl.replaceWith(input);
        input.focus(); input.select();

        const save = async () => {
            const newName = input.value.trim();
            if (!newName) { revert(); return; }
            const res = await api.post(`/tables/${code}/rename`, { seat, name: newName });
            if (res.name) {
                ws.send(JSON.stringify({ event: 'player_renamed', seat, name: res.name }));
            }
            api.get('/tables/' + code).then(t => renderPlayers(t.players));
        };
        const revert = () => {
            const span = document.createElement('span');
            span.className    = 'mk-player-name';
            span.dataset.seat = seat;
            span.textContent  = oldName;
            input.replaceWith(span);
        };
        input.addEventListener('blur', save);
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter')  { input.blur(); }
            if (e.key === 'Escape') { input.removeEventListener('blur', save); revert(); }
        });
    };

    window.kickPlayer = async (playerId) => {
        const res = await api.post(`/tables/${code}/kick`, { player_id: playerId });
        if (res.seat !== null && res.seat !== undefined) {
            ws.send(JSON.stringify({ event: 'player_kicked', seat: res.seat }));
        }
    };

    $('mk-btn-start').addEventListener('click', async () => {
        const res = await api.post('/tables/' + code + '/start', {});
        if (res.started) {
            ws.send(JSON.stringify({ event: 'game_started' }));
            window.location.href = '/game/?code=' + code;
        } else {
            const errEl = $('mk-start-error');
            errEl.textContent = res.code === 'too_few'
                ? 'Not enough players at the table.'
                : (res.message || 'Could not start game.');
            errEl.classList.remove('mk-hidden');
            setTimeout(() => errEl.classList.add('mk-hidden'), 3500);
        }
    });

    init();
}

// ── Game Table ────────────────────────────────────────────────────────────────
if (document.getElementById('mk-game')) {
    const params = new URLSearchParams(window.location.search);
    const code   = params.get('code') || sessionStorage.getItem('mk_code');
    const mySeat = parseInt(sessionStorage.getItem('mk_seat') ?? '0');
    const SYMBOLS = {wheat:'🌾',cow:'🐄',cup:'☕',bread:'🍞',factory:'🏭',fish:'🐟',fruit:'🍎',gear:'⚙️',tower:'🏰'};
    const LANDMARK_ICONS = {train_station:'🚂',shopping_mall:'🛒',amusement_park:'🎡',radio_tower:'📡',harbor:'⚓',city_hall:'🏛️',airport:'✈️',french_restaurant:'🍽️'};
    let ws, gameState, connectedCount = 1, currentFilter = 'all';
    const activeReactions = {};
    const reactionTimers  = {};

    function connectWS() {
        ws = new WebSocket(MK.wsUrl + code + '/game/' + mySeat);
        ws.onmessage = (e) => {
            const msg = JSON.parse(e.data);
            if (msg.event === 'state_update') {
                const prevPhase      = gameState?.phase;
                const prevActiveSeat = gameState?.active_seat;
                gameState = msg.state;
                connectedCount = msg.connected_count ?? connectedCount;
                render(gameState);
                if (gameState.phase === 'finished') showEndScreen(gameState);

                if (gameState.active_seat === mySeat && prevActiveSeat !== mySeat && gameState.phase === 'roll') {
                    showYourTurnBanner();
                }

                // Tuna Boat waiting toast for non-active players
                if (gameState.phase === 'tuna_roll' && prevPhase !== 'tuna_roll' && gameState.active_seat !== mySeat) {
                    const activeName = gameState.players.find(p => p.seat === gameState.active_seat)?.name ?? 'Active player';
                    toast(`🐟 Tuna Boat! Waiting for ${activeName} to roll 2 dice…`);
                }

                // TV Station overlay
                if (gameState.phase === 'tv_station' && gameState.active_seat === mySeat) {
                    showTVStationUI(gameState);
                }
                if (gameState.phase === 'tv_station' && prevPhase !== 'tv_station' && gameState.active_seat !== mySeat) {
                    const activeName = gameState.players.find(p => p.seat === gameState.active_seat)?.name ?? 'Active player';
                    toast(`📺 ${activeName} is choosing a TV Station target…`);
                }
                if (gameState.phase !== 'tv_station') {
                    document.getElementById('mk-tvs-overlay')?.remove();
                }

                // Business Center overlay
                if (gameState.phase === 'business_center' && gameState.active_seat === mySeat) {
                    showBusinessCenterUI(gameState);
                }
                if (gameState.phase === 'business_center' && prevPhase !== 'business_center' && gameState.active_seat !== mySeat) {
                    const activeName = gameState.players.find(p => p.seat === gameState.active_seat)?.name ?? 'Active player';
                    toast(`🔄 ${activeName} is choosing a Business Center trade…`);
                }
                if (gameState.phase !== 'business_center') {
                    document.getElementById('mk-bc-overlay')?.remove();
                }
            }
            if (msg.event === 'prompt') {
                showPrompt(msg.text, msg.promptId);
            }
            if (msg.event === 'player_left_game') {
                toast(`${esc(msg.name)} left the game.`, 'warn');
            }
            if (msg.event === 'player_rejoined_game') {
                toast(`${esc(msg.name)} reconnected.`);
            }
            if (msg.event === 'game_toast') {
                toast(msg.text);
            }
            if (msg.event === 'coin_event') {
                msg.changes.forEach(c => toast(c, c.startsWith('-') ? 'warn' : ''));
            }
            if (msg.event === 'reaction') {
                const s = msg.seat;
                activeReactions[s] = msg.emoji;
                clearTimeout(reactionTimers[s]);
                if (s === mySeat) {
                    const el = document.getElementById('mk-my-reaction');
                    if (el) { el.textContent = msg.emoji; el.classList.add('mk-my-reaction-active'); }
                } else if (gameState) {
                    renderOpponents(gameState);
                }
                reactionTimers[s] = setTimeout(() => {
                    delete activeReactions[s];
                    if (s === mySeat) {
                        const el = document.getElementById('mk-my-reaction');
                        if (el) { el.textContent = ''; el.classList.remove('mk-my-reaction-active'); }
                    } else if (gameState) {
                        renderOpponents(gameState);
                    }
                }, 3000);
            }
        };
    }

    function send(event, data = {}) {
        ws.send(JSON.stringify({ event, seat: mySeat, ...data }));
    }



    // ── Reactions ─────────────────────────────────────
    window.sendReaction = (emoji) => send('reaction', { emoji });

    // ── Your turn banner ──────────────────────────────
    function showYourTurnBanner() {
        const existing = document.getElementById('mk-your-turn-banner');
        if (existing) existing.remove();
        const el = document.createElement('div');
        el.id = 'mk-your-turn-banner';
        el.textContent = '🎲 It is your turn!';
        document.body.appendChild(el);
        setTimeout(() => el.classList.add('mk-yb-hide'), 2000);
        setTimeout(() => el.remove(), 2600);
    }

    // ── Toast notifications ───────────────────────────
    function toast(msg, type = '') {
        const container = document.getElementById('mk-toast-container');
        const el = document.createElement('div');
        el.className = 'mk-toast' + (type ? ` mk-toast-${type}` : '');
        el.textContent = msg;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }

    // ── Leave game button ─────────────────────────────
    document.getElementById('mk-btn-leave-game').addEventListener('click', () => {
        showPrompt(
            'Are you sure you want to leave the game?',
            null,
            () => { ws?.close(); window.location.href = MK.homeUrl; },
            null,
            'Yes, leave',
            'Stay'
        );
    });

    // ── Render ────────────────────────────────────────
    function render(state) {
        if (!state) return;
        renderOpponents(state);
        renderMarket(state);
        renderMyArea(state);
    }

    function renderOpponents(state) {
        const ring = document.getElementById('mk-opponents-ring');
        const others = state.players.filter(p => p.seat !== mySeat);
        ring.innerHTML = others.map(p => `
            <div class="mk-opponent ${state.active_seat === p.seat ? 'active-turn' : ''}" onclick="showOpponentCards(${p.seat})" title="View ${esc(p.name)}'s cards">
                ${activeReactions[p.seat] ? `<div class="mk-reaction-bubble">${activeReactions[p.seat]}</div>` : ''}
                <div class="mk-opp-avatar">
                    ${esc(p.name).charAt(0).toUpperCase()}
                    <span class="mk-opp-coin-badge">${p.coins}</span>
                </div>
                <div class="mk-opp-label">OPPONENT</div>
                <div class="mk-opp-name">${esc(p.name)}</div>
                <div class="mk-opp-landmarks">
                    ${p.landmarks.map(lm => `<div class="mk-opp-lm ${lm.built ? 'built' : ''}" title="${esc(lm.name)}"></div>`).join('')}
                </div>
            </div>`).join('');
    }

    window.showOpponentCards = (seat) => {
        const opp = gameState?.players.find(p => p.seat === seat);
        if (!opp) return;

        const existing = document.getElementById('mk-opp-cards-overlay');
        if (existing) existing.remove();

        const COLOR = { 'Blue Primary': '#2980b9', 'Green Secondary': '#27ae60', 'Red Restaurant': '#c0392b', 'Purple Major': '#8e44ad' };

        const cardsHTML = Object.entries(opp.cards).length
            ? Object.entries(opp.cards).map(([id, count]) => {
                const card = gameState.card_defs[id];
                const bg = COLOR[card.type] ?? '#555';
                return `<div style="background:${bg};color:#fff;border-radius:8px;padding:6px 10px;font-size:13px;display:flex;justify-content:space-between;align-items:center;gap:12px;">
                    <span>${SYMBOLS[card.symbol] ?? ''} ${esc(card.name)} ×${count}</span>
                    <span style="opacity:.75;font-size:11px;">${Array.isArray(card.dice) ? card.dice.join('–') : card.dice}</span>
                </div>`;
            }).join('')
            : '<p style="color:#888;font-size:13px;margin:0;">No establishments yet.</p>';

        const landmarksHTML = opp.landmarks.map(lm => `
            <div style="display:flex;align-items:center;gap:8px;font-size:13px;">
                <div style="width:14px;height:14px;border-radius:3px;background:${lm.built ? '#d4ac0d' : '#7f8c8d'};flex-shrink:0;"></div>
                <span style="color:${lm.built ? '#f1c40f' : '#888'};">${esc(lm.name)}</span>
                ${lm.built ? '<span style="color:#f1c40f;font-size:11px;">✓ Built</span>' : ''}
            </div>`).join('');

        const overlay = document.createElement('div');
        overlay.id = 'mk-opp-cards-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.75);display:flex;align-items:center;justify-content:center;z-index:998;';
        overlay.innerHTML = `
            <div style="background:#16213e;color:#eee;border-radius:14px;padding:24px;max-width:420px;width:90%;max-height:80vh;overflow-y:auto;position:relative;">
                <button onclick="document.getElementById('mk-opp-cards-overlay').remove()" style="position:absolute;top:12px;right:14px;background:none;border:none;color:#aaa;font-size:20px;cursor:pointer;">✕</button>
                <h3 style="margin:0 0 4px;color:#f1c40f;">${esc(opp.name)}</h3>
                <p style="margin:0 0 16px;color:#aaa;font-size:13px;">💰 ${opp.coins} coins</p>

                <p style="margin:0 0 8px;font-size:12px;color:#aaa;text-transform:uppercase;letter-spacing:1px;">Establishments</p>
                <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:20px;">${cardsHTML}</div>

                <p style="margin:0 0 8px;font-size:12px;color:#aaa;text-transform:uppercase;letter-spacing:1px;">Landmarks</p>
                <div style="display:flex;flex-direction:column;gap:8px;">${landmarksHTML}</div>
            </div>`;
        overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
        document.body.appendChild(overlay);
    };

    function renderMarket(state) {
        const market = document.getElementById('mk-market');
        const me = state.players.find(p => p.seat === mySeat);
        const isMyTurn = state.active_seat === mySeat && state.phase === 'build';

        market.innerHTML = state.market
            .filter(card => currentFilter === 'all' || colorClass(card.type) === currentFilter)
            .map(card => {
                const supply     = state.supply?.[card.id] ?? 0;
                const soldOut    = supply <= 0;
                const canAfford  = !soldOut && me.coins >= card.cost;
                const alreadyOwn = card.type === 'Purple Major' && (me.cards[card.id] ?? 0) >= 1;
                const buyable    = isMyTurn && canAfford && !alreadyOwn;

                const cls = [
                    colorClass(card.type),
                    soldOut || alreadyOwn ? 'mk-sold-out' : (!canAfford ? 'mk-cant-afford' : ''),
                ].join(' ');

                const diceLabel = Array.isArray(card.dice) ? card.dice.join('–') : card.dice;
                const typeLabel = card.type.split(' ')[0];

                return `<div class="mk-card ${cls}" data-id="${card.id}"
                            ${buyable ? `onclick="selectCard('${card.id}')"` : ''}>
                    <div class="mk-card-header">
                        <div class="mk-card-header-row">
                            <span class="mk-card-type-badge">${typeLabel}</span>
                            <span class="mk-card-supply-badge">${soldOut ? '✗' : supply}</span>
                        </div>
                    </div>
                    <div class="mk-card-image">${SYMBOLS[card.symbol] ?? '🏢'}</div>
                    <div class="mk-card-body">
                        <div class="mk-card-name">${esc(card.name)}</div>
                        <div class="mk-card-desc">${esc(card.effect)}</div>
                    </div>
                    <div class="mk-card-footer">
                        <span class="mk-card-dice-badge">${diceLabel}</span>
                        <span class="mk-card-cost-tag">💰${card.cost}</span>
                    </div>
                </div>`;
            }).join('');
    }

    function renderMyArea(state) {
        const me = state.players.find(p => p.seat === mySeat);
        if (!me) return;
        const isMyTurn = state.active_seat === mySeat;
        const isBuild  = state.phase === 'build';

        // Profile
        document.getElementById('mk-coin-count').textContent = me.coins;
        document.getElementById('mk-my-name').textContent = me.name;
        const avatarEl = document.getElementById('mk-avatar-initials');
        if (avatarEl) avatarEl.textContent = me.name.charAt(0).toUpperCase();

        // Income rank
        const rankEl = document.getElementById('mk-income-rank');
        if (rankEl) {
            const sorted = [...state.players].sort((a,b) => b.coins - a.coins);
            rankEl.textContent = '#' + (sorted.findIndex(p => p.seat === mySeat) + 1);
        }

        // Establishments
        const estEntries = Object.entries(me.cards);
        const estTotal = estEntries.reduce((s,[,c]) => s+c, 0);
        const estCountEl = document.getElementById('mk-est-count');
        if (estCountEl) estCountEl.textContent = estTotal;
        document.getElementById('mk-my-cards').innerHTML = estEntries.length
            ? estEntries.map(([id, count]) => {
                const card = state.card_defs[id];
                const cc = colorClass(card.type);
                return `<div class="mk-owned-card ${cc}">
                    <div class="mk-owned-card-bar"></div>
                    <div class="mk-owned-card-info">
                        <div class="mk-owned-card-name">${esc(card.name)} ×${count}</div>
                        <div class="mk-owned-card-sub">${Array.isArray(card.dice) ? card.dice.join('–') : card.dice} · ${card.type.split(' ')[0]}</div>
                    </div>
                    <div class="mk-owned-card-income">+${count}</div>
                </div>`;
            }).join('')
            : '<p class="mk-no-cards">No establishments yet.</p>';

        // Landmarks
        document.getElementById('mk-my-landmarks').innerHTML = me.landmarks.map(lm => {
            const canAfford = me.coins >= lm.cost && !lm.built;
            const cls = [lm.built ? 'built' : '', !lm.built && !canAfford ? 'mk-cant-afford-lm' : ''].join(' ');
            return `<div class="mk-right-lm ${cls}" data-lm="${lm.id}"
                         ${isBuild && isMyTurn && !lm.built && canAfford ? `onclick="selectLandmark('${lm.id}')"` : ''}>
                <div class="mk-right-lm-icon">${LANDMARK_ICONS[lm.id] ?? '🏛️'}</div>
                <div class="mk-right-lm-name">${esc(lm.name)}</div>
                ${lm.built ? '<div class="mk-right-lm-status">BUILT</div>' : `<div class="mk-right-lm-cost">💰${lm.cost}</div>`}
            </div>`;
        }).join('');

        // Roll center — show big centered button during our roll phase, hide otherwise
        const isTunaRoll = state.phase === 'tuna_roll';
        const showRoll = isMyTurn && (state.phase === 'roll' || isTunaRoll);
        document.getElementById('mk-roll-center').classList.toggle('mk-hidden', !showRoll);
        document.getElementById('mk-market-header').classList.toggle('mk-hidden', showRoll);
        document.getElementById('mk-market').classList.toggle('mk-hidden', showRoll);
        const rollBtn = document.getElementById('mk-btn-roll');
        rollBtn.textContent = isTunaRoll ? '🐟 Tuna Roll' : 'Roll Dice';

        // Skip button
        document.getElementById('mk-btn-skip').style.display = isBuild && isMyTurn ? '' : 'none';

        // Dice result
        const diceEl = document.getElementById('mk-dice-result');
        const dice = state.last_dice ?? [];
        if (dice.length === 0) {
            diceEl.innerHTML = '';
        } else if (dice.length === 1) {
            diceEl.innerHTML = `<span class="mk-die-box">${dice[0]}</span>`;
        } else {
            diceEl.innerHTML = `<span class="mk-die-box">${dice[0]}</span>`
                             + `<span class="mk-die-box">${dice[1]}</span>`
                             + `<span class="mk-dice-sum">= ${state.last_roll}</span>`;
        }
    }

    // ── Actions ───────────────────────────────────────
    let selectedCard = null, selectedLandmark = null;

    window.selectCard = (id) => {
        selectedCard = id; selectedLandmark = null;
        document.querySelectorAll('.mk-card').forEach(el => el.classList.toggle('mk-selected', el.dataset.id === id));
        document.querySelectorAll('.mk-right-lm').forEach(el => el.classList.remove('mk-selected'));
        showBuildConfirm(id, 'card');
    };

    window.selectLandmark = (id) => {
        selectedLandmark = id; selectedCard = null;
        document.querySelectorAll('.mk-right-lm').forEach(el => el.classList.toggle('mk-selected', el.dataset.lm === id));
        document.querySelectorAll('.mk-card').forEach(el => el.classList.remove('mk-selected'));
        showBuildConfirm(id, 'landmark');
    };

    function showBuildConfirm(id, type) {
        const defs = type === 'card' ? gameState.market : gameState.players.find(p => p.seat === mySeat).landmarks;
        const item = type === 'card' ? defs.find(c => c.id === id) : defs.find(l => l.id === id);
        showPrompt(`Buy ${item.name} for 💰${item.cost}?`, null, () => {
            send('build', { type, id });
        }, () => {
            selectedCard = null; selectedLandmark = null;
            document.querySelectorAll('.mk-card, .mk-right-lm').forEach(el => el.classList.remove('mk-selected'));
        });
    }

    document.getElementById('mk-btn-roll').addEventListener('click', () => {
        if (gameState?.phase === 'tuna_roll') {
            send('tuna_roll', { dice_count: 2 });
            return;
        }
        const me = gameState?.players?.find(p => p.seat === mySeat);
        const hasTrainStation = me?.landmarks?.some(lm => lm.id === 'train_station' && lm.built);
        if (hasTrainStation) {
            showPrompt('Roll 1 or 2 dice?', null,
                () => send('roll', { dice_count: 2 }),
                () => send('roll', { dice_count: 1 }),
                'Roll 2', 'Roll 1'
            );
        } else {
            send('roll', { dice_count: 1 });
        }
    });
    document.getElementById('mk-btn-skip').addEventListener('click', () => send('skip_build'));

    // ── Filter tabs ───────────────────────────────────
    document.querySelectorAll('.mk-filter-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            currentFilter = btn.dataset.filter;
            document.querySelectorAll('.mk-filter-tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            if (gameState) renderMarket(gameState);
        });
    });

    // ── Prompt overlay ────────────────────────────────
    let promptResolve = null;

    function showPrompt(text, promptId, onYes, onNo, yesLabel = 'Yes', noLabel = 'No') {
        const overlay = document.getElementById('mk-prompt-overlay');
        document.getElementById('mk-prompt-text').textContent = text;
        overlay.classList.remove('mk-hidden');

        const yes = document.getElementById('mk-prompt-yes');
        const no  = document.getElementById('mk-prompt-no');
        yes.textContent = yesLabel;
        no.textContent  = noLabel;

        yes.onclick = () => {
            overlay.classList.add('mk-hidden');
            if (promptId) send('prompt_response', { promptId, answer: true });
            onYes?.();
        };
        no.onclick = () => {
            overlay.classList.add('mk-hidden');
            if (promptId) send('prompt_response', { promptId, answer: false });
            onNo?.();
        };
    }

    // ── Helpers ───────────────────────────────────────
    function colorClass(type) {
        if (type.includes('Primary'))   return 'blue';
        if (type.includes('Secondary')) return 'green';
        if (type.includes('Restaurant'))return 'red';
        if (type.includes('Major'))     return 'purple';
        return '';
    }

    // ── Fortune Wheel ─────────────────────────────────────────────────────────
    // ── Business Center UI ────────────────────────────────────────────────────
    function showBusinessCenterUI(state) {
        if (document.getElementById('mk-bc-overlay')) return;

        const me = state.players.find(p => p.seat === mySeat);
        const opps = state.players.filter(p => p.seat !== mySeat);
        const COLOR = {'Blue Primary':'#2980b9','Green Secondary':'#27ae60','Red Restaurant':'#c0392b'};

        const myCards = Object.entries(me.cards)
            .filter(([id]) => state.card_defs[id]?.type !== 'Purple Major')
            .map(([id, count]) => ({id, count, ...state.card_defs[id]}));

        const oppGroups = opps.map(o => ({
            seat: o.seat, name: o.name,
            cards: Object.entries(o.cards)
                .filter(([id]) => state.card_defs[id]?.type !== 'Purple Major')
                .map(([id, count]) => ({id, count, ...state.card_defs[id]}))
        })).filter(o => o.cards.length > 0);

        if (!myCards.length || !oppGroups.length) { send('skip_business_center'); return; }

        let selMy = null, selOppSeat = null, selOppCard = null;

        const overlay = document.createElement('div');
        overlay.id = 'mk-bc-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.8);display:flex;align-items:center;justify-content:center;z-index:998;';

        function renderBC() {
            const myHTML = myCards.map(c =>
                `<button onclick="bcMy('${c.id}')" style="background:${COLOR[c.type]||'#555'};color:#fff;
                    border:2px solid ${selMy===c.id?'#f1c40f':'transparent'};border-radius:8px;
                    padding:6px 10px;cursor:pointer;font-size:13px;margin:3px;">
                    ${esc(c.name)} ×${c.count}</button>`
            ).join('');

            const oppsHTML = oppGroups.map(o =>
                `<div style="margin-bottom:10px;">
                    <div style="font-size:12px;color:#aaa;margin-bottom:4px;">${esc(o.name)}</div>
                    ${o.cards.map(c =>
                        `<button onclick="bcOpp(${o.seat},'${c.id}')" style="background:${COLOR[c.type]||'#555'};color:#fff;
                            border:2px solid ${selOppSeat===o.seat&&selOppCard===c.id?'#f1c40f':'transparent'};
                            border-radius:8px;padding:6px 10px;cursor:pointer;font-size:13px;margin:3px;">
                            ${esc(c.name)} ×${c.count}</button>`
                    ).join('')}
                </div>`
            ).join('');

            const canConfirm = selMy && selOppCard;
            overlay.innerHTML = `
                <div style="background:#16213e;color:#eee;border-radius:14px;padding:24px;
                            max-width:500px;width:90%;max-height:82vh;overflow-y:auto;">
                    <h3 style="color:#f1c40f;margin:0 0 14px;">🔄 Business Center — Trade an Establishment</h3>
                    <p style="font-weight:700;color:#aaa;margin:0 0 8px;">Choose <em>your</em> card to give:</p>
                    <div style="margin-bottom:16px;">${myHTML}</div>
                    <p style="font-weight:700;color:#aaa;margin:0 0 8px;">Choose an <em>opponent's</em> card to receive:</p>
                    <div style="margin-bottom:20px;">${oppsHTML}</div>
                    <div style="display:flex;gap:10px;flex-wrap:wrap;">
                        <button onclick="bcConfirm()" class="mk-btn mk-btn-primary"
                            style="opacity:${canConfirm?1:.4};" ${canConfirm?'':'disabled'}>
                            Confirm Trade</button>
                        <button onclick="bcSkip()" class="mk-btn">Skip</button>
                    </div>
                </div>`;
        }

        window.bcMy   = id => { selMy = id; renderBC(); };
        window.bcOpp  = (seat, id) => { selOppSeat = seat; selOppCard = id; renderBC(); };
        window.bcConfirm = () => {
            if (!selMy || selOppSeat === null || !selOppCard) return;
            send('business_center', {my_card: selMy, opp_seat: selOppSeat, opp_card: selOppCard});
            overlay.remove();
            ['bcMy','bcOpp','bcConfirm','bcSkip'].forEach(k => delete window[k]);
        };
        window.bcSkip = () => {
            send('skip_business_center');
            overlay.remove();
            ['bcMy','bcOpp','bcConfirm','bcSkip'].forEach(k => delete window[k]);
        };

        renderBC();
        document.body.appendChild(overlay);
    }

    // ── TV Station UI ─────────────────────────────────────────────────────────
    function showTVStationUI(state) {
        if (document.getElementById('mk-tvs-overlay')) return;
        const opps = state.players.filter(p => p.seat !== mySeat);
        if (!opps.length) { send('tv_station_pick', { target_seat: -1 }); return; }

        const overlay = document.createElement('div');
        overlay.id = 'mk-tvs-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.8);display:flex;align-items:center;justify-content:center;z-index:998;';
        overlay.innerHTML = `
            <div style="background:#16213e;color:#eee;border-radius:14px;padding:24px;max-width:400px;width:90%;text-align:center;">
                <h3 style="color:#f1c40f;margin:0 0 16px;">📺 TV Station — Take 5 coins from:</h3>
                <div style="display:flex;flex-direction:column;gap:10px;">
                    ${opps.map(o => `
                        <button onclick="tvsPickTarget(${o.seat})"
                            style="background:#0f3460;color:#eee;border:2px solid #2980b9;border-radius:10px;
                                   padding:12px 16px;cursor:pointer;font-size:15px;
                                   display:flex;justify-content:space-between;align-items:center;">
                            <span>${esc(o.name)}</span>
                            <span style="color:#f1c40f;font-weight:700;">💰 ${o.coins}</span>
                        </button>`).join('')}
                </div>
            </div>`;
        window.tvsPickTarget = (seat) => {
            send('tv_station_pick', { target_seat: seat });
            overlay.remove();
            delete window.tvsPickTarget;
        };
        document.body.appendChild(overlay);
    }

    // ── End screen ────────────────────────────────────────────────────────────
    function showEndScreen(state) {
        const overlay = document.getElementById('mk-end-overlay');
        const scores  = state.scores ?? [];
        const winner  = scores.find(s => s.is_winner);
        const iWon    = winner && winner.seat === mySeat;

        const titleEl = document.getElementById('mk-end-title');
        titleEl.textContent = iWon ? 'You Win!' : (winner ? 'Better Luck Next Time!' : 'Game Over!');
        titleEl.classList.toggle('mk-loss', !iWon);

        const medals = ['🥇', '🥈', '🥉'];
        document.getElementById('mk-scores-list').innerHTML = scores.map((s, i) => `
            <div class="mk-score-row ${s.is_winner ? 'winner' : ''}">
                <span class="mk-score-rank">${medals[i] ?? `${i + 1}.`}</span>
                <span class="mk-score-name">${esc(s.name)}</span>
                <span class="mk-score-pts">${s.landmarks_built} / 6 🏛️</span>
            </div>`).join('');

        overlay.classList.remove('mk-hidden');
    }

    document.getElementById('mk-btn-exit-lobby').addEventListener('click', () => {
        ws?.close();
        window.location.href = MK.homeUrl;
    });

    connectWS();
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}

function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}
