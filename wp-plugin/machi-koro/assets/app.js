/* global MK */

// Stable guest ID persisted in localStorage
if (!localStorage.getItem('mk_guest_id')) {
    localStorage.setItem('mk_guest_id', 'g-' + Math.random().toString(36).slice(2) + Date.now().toString(36));
}
const MK_GUEST_ID = localStorage.getItem('mk_guest_id');

const api = {
    get:  (path)       => fetch(MK.apiBase + path, {
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
                    <div class="mk-table-info">${esc(t.name)} ${t.is_protected ? '🔒' : ''}</div>
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
        // Protected tables need a password before we can join — ask first.
        if (table.is_protected) {
            openPasswordPrompt(code);
            return;
        }
        const res = await doJoin(code);
        if (res.seat !== undefined) goWaiting(code, res.seat);
        else showJoinError(res.message || 'Could not join table.');
    };

    // Send a join request; `password` is included only for protected tables.
    function doJoin(code, password) {
        const guestName = $('mk-guest-name')?.value || 'Guest';
        const body = { guest_name: guestName };
        if (password != null) body.password = password;
        return api.post('/tables/' + code + '/join', body);
    }

    // Store seat + redirect into the waiting room. Shared by create and join.
    function goWaiting(code, seat) {
        sessionStorage.setItem('mk_code', code);
        sessionStorage.setItem('mk_seat', seat);
        window.location.href = '/waiting-room/?code=' + code;
    }

    // Modal that asks for a table password and joins on submit.
    // Wrong password (403) keeps the modal open with an inline, retryable error.
    function openPasswordPrompt(code) {
        document.getElementById('mk-pw-overlay')?.remove();

        const overlay = document.createElement('div');
        overlay.id = 'mk-pw-overlay';
        overlay.className = 'mk-modal-overlay';
        overlay.innerHTML = `
            <div class="mk-modal">
                <h3 class="mk-modal-title">🔒 Password required</h3>
                <p class="mk-modal-text">This table is protected. Enter the password to join.</p>
                <input id="mk-pw-input" type="password" placeholder="Password" maxlength="64" autocomplete="off" />
                <p id="mk-pw-error" class="mk-error-msg mk-hidden"></p>
                <div class="mk-modal-btns">
                    <button id="mk-pw-submit" class="mk-btn mk-btn-primary">Join</button>
                    <button id="mk-pw-cancel" class="mk-btn mk-btn-secondary">Cancel</button>
                </div>
            </div>`;
        document.body.appendChild(overlay);

        const input  = $('mk-pw-input');
        const errEl  = $('mk-pw-error');
        const submit = $('mk-pw-submit');
        const close  = () => overlay.remove();
        const showErr = (msg) => { errEl.textContent = msg; errEl.classList.remove('mk-hidden'); };

        input.focus();

        const trySubmit = async () => {
            const password = input.value;
            if (!password) { showErr('Please enter the password.'); return; }
            submit.disabled = true;
            const res = await doJoin(code, password);
            if (res.seat !== undefined) { goWaiting(code, res.seat); return; }
            // Re-enable so the user can retry without reopening the modal.
            submit.disabled = false;
            if (res.data?.status === 403) {
                showErr('Wrong password. Try again.');
                input.select();
            } else {
                showErr(res.message || 'Could not join table.');
            }
        };

        submit.addEventListener('click', trySubmit);
        input.addEventListener('keydown', e => { if (e.key === 'Enter') trySubmit(); });
        $('mk-pw-cancel').addEventListener('click', close);
        overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    }

    function showJoinError(msg) {
        const el = document.createElement('p');
        el.className = 'mk-error-msg';
        el.textContent = msg;
        el.style.textAlign = 'center';
        $('mk-home').appendChild(el);
        setTimeout(() => el.remove(), 3500);
    }

    async function createTable(isPublic) {
        const password = $('mk-table-password')?.value.trim() || '';
        const body = {
            name:       $('mk-table-name').value || 'Machi Koro Table',
            is_public:  isPublic,
            guest_name: $('mk-guest-name')?.value || 'Guest',
        };
        // Only send a password when the host actually set one — protects the table.
        if (password) body.password = password;
        const res = await api.post('/tables', body);
        if (res.code) {
            goWaiting(res.code, 0);
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
            if (msg.event === 'table_closed') showTableClosedOverlay();
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
                <p style="font-size:13px;margin-top:16px">Returning to lobby in 3 seconds…</p>
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
                <p style="font-size:13px;margin-top:16px">Returning to lobby in 3 seconds…</p>
            </div>`;
        document.body.appendChild(overlay);
        setTimeout(() => { window.location.href = MK.homeUrl; }, 3000);
    }

    function showLobbyToast(msg) {
        let container = document.getElementById('mk-lobby-toast');
        if (!container) {
            container = document.createElement('div');
            container.id = 'mk-lobby-toast';
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
        const mySeat   = sessionStorage.getItem('mk_seat');
        const myIsHost = players.some(p => p.is_host == 1 && String(p.seat) === mySeat);

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
        input.type = 'text'; input.value = oldName;
        input.className = 'mk-name-input'; input.maxLength = 64;
        nameEl.replaceWith(input);
        input.focus(); input.select();
        const save = async () => {
            const newName = input.value.trim();
            if (!newName) { revert(); return; }
            const res = await api.post(`/tables/${code}/rename`, { seat, name: newName });
            if (res.name) ws.send(JSON.stringify({ event: 'player_renamed', seat, name: res.name }));
            api.get('/tables/' + code).then(t => renderPlayers(t.players));
        };
        const revert = () => {
            const span = document.createElement('span');
            span.className = 'mk-player-name'; span.dataset.seat = seat; span.textContent = oldName;
            input.replaceWith(span);
        };
        input.addEventListener('blur', save);
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter')  input.blur();
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

    const SYMBOLS = {
        wheat:'🌾', cow:'🐄', cup:'☕', bread:'🍞',
        factory:'🏭', fish:'🐟', fruit:'🍎', gear:'⚙️', tower:'🏰',
    };
    const LANDMARK_ICONS = {
        train_station:'🚂', shopping_mall:'🛍️', amusement_park:'🎡',
        radio_tower:'📻', harbor:'⚓', city_hall:'🏛️', airport:'✈️',
    };
    const LANDMARK_EFFECTS = {
        city_hall:      'If you have 0 coins after income, get 1 from bank',
        harbor:         'Roll 10+? Add +2 total. Unlocks sea cards',
        train_station:  'Choose to roll 1 or 2 dice each turn',
        shopping_mall:  '☕ and 🍞 cards each earn +1 extra',
        amusement_park: 'Roll doubles? Take another turn',
        radio_tower:    'Once per turn, may reroll the dice',
        airport:        'Skip building? Receive 10 coins from bank',
    };
    const PHASE_LABELS = {
        roll: 'Roll Phase', tuna_roll: 'Tuna Roll',
        build: 'Build Phase', tv_station: 'TV Station',
        business_center: 'Business Center', finished: 'Game Over',
    };

    let ws, gameState, connectedCount = 1;
    const activeReactions = {};
    const reactionTimers  = {};

    // ── WebSocket ─────────────────────────────────────
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
                if (gameState.phase === 'tuna_roll' && prevPhase !== 'tuna_roll' && gameState.active_seat !== mySeat) {
                    const name = gameState.players.find(p => p.seat === gameState.active_seat)?.name ?? 'Active player';
                    toast(`🐟 Tuna Boat! Waiting for ${name} to roll 2 dice…`);
                }
                if (gameState.phase === 'tv_station' && gameState.active_seat === mySeat) showTVStationUI(gameState);
                if (gameState.phase === 'tv_station' && prevPhase !== 'tv_station' && gameState.active_seat !== mySeat) {
                    const name = gameState.players.find(p => p.seat === gameState.active_seat)?.name ?? 'Active player';
                    toast(`📺 ${name} is choosing a TV Station target…`);
                }
                if (gameState.phase !== 'tv_station') document.getElementById('mk-tvs-overlay')?.remove();

                if (gameState.phase === 'business_center' && gameState.active_seat === mySeat) showBusinessCenterUI(gameState);
                if (gameState.phase === 'business_center' && prevPhase !== 'business_center' && gameState.active_seat !== mySeat) {
                    const name = gameState.players.find(p => p.seat === gameState.active_seat)?.name ?? 'Active player';
                    toast(`🔄 ${name} is choosing a Business Center trade…`);
                }
                if (gameState.phase !== 'business_center') document.getElementById('mk-bc-overlay')?.remove();
            }

            if (msg.event === 'prompt') showPrompt(msg.text, msg.promptId);
            if (msg.event === 'player_left_game')    toast(`${esc(msg.name)} left the game.`, 'warn');
            if (msg.event === 'player_rejoined_game') toast(`${esc(msg.name)} reconnected.`);
            if (msg.event === 'game_toast')          toast(msg.text);
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
        document.getElementById('mk-your-turn-banner')?.remove();
        const el = document.createElement('div');
        el.id = 'mk-your-turn-banner';
        el.textContent = '🎲 Your Turn!';
        document.body.appendChild(el);
        setTimeout(() => el.classList.add('mk-yb-hide'), 2000);
        setTimeout(() => el.remove(), 2600);
    }

    // ── Toast ─────────────────────────────────────────
    function toast(msg, type = '') {
        const container = document.getElementById('mk-toast-container');
        const el = document.createElement('div');
        el.className = 'mk-toast' + (type ? ` mk-toast-${type}` : '');
        el.textContent = msg;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }

    // ── Leave ─────────────────────────────────────────
    document.getElementById('mk-btn-leave-game').addEventListener('click', () => {
        showPrompt('Leave the game?', null,
            () => { ws?.close(); window.location.href = MK.homeUrl; },
            null, 'Yes, leave', 'Stay'
        );
    });

    // ── Drawer toggle ─────────────────────────────────
    document.getElementById('mk-drawer-toggle').addEventListener('click', () => {
        document.getElementById('mk-game').classList.toggle('drawer-collapsed');
    });

    // ── Main render ───────────────────────────────────
    function render(state) {
        if (!state) return;
        renderOpponents(state);
        renderMarket(state);
        renderMyArea(state);
    }

    // ── Opponents ─────────────────────────────────────
    function renderOpponents(state) {
        const oppsEl = document.getElementById('mk-opps');
        const others = state.players.filter(p => p.seat !== mySeat);
        oppsEl.innerHTML = others.map(p => {
            // count cards by color
            let blue = 0, green = 0, red = 0, purple = 0;
            Object.entries(p.cards ?? {}).forEach(([id, count]) => {
                const cd = state.card_defs?.[id];
                if (!cd) return;
                if (cd.type.includes('Primary'))    blue   += count;
                else if (cd.type.includes('Secondary')) green += count;
                else if (cd.type.includes('Restaurant')) red += count;
                else if (cd.type.includes('Major'))  purple += count;
            });
            const lmDots = (p.landmarks ?? []).map(lm =>
                `<div class="lm-dot ${lm.built ? 'built' : ''}" title="${esc(lm.name)}"></div>`
            ).join('');
            const isActive = state.active_seat === p.seat;
            const reaction = activeReactions[p.seat];
            return `
                <div class="opp ${isActive ? 'active' : ''}" onclick="showOpponentCards(${p.seat})" title="View ${esc(p.name)}'s cards">
                    ${reaction ? `<div class="opp-reaction">${reaction}</div>` : ''}
                    <div class="opp-head">
                        <div class="opp-name">
                            <span class="opp-avatar">${esc(p.name).charAt(0).toUpperCase()}</span>
                            ${esc(p.name)}
                        </div>
                        <div class="opp-coins">💰 ${p.coins}</div>
                    </div>
                    <div class="opp-stats">
                        <span class="stat-chip blue">🟦 ${blue}</span>
                        <span class="stat-chip green">🟩 ${green}</span>
                        <span class="stat-chip red">🟥 ${red}</span>
                        <span class="stat-chip purple">🟪 ${purple}</span>
                    </div>
                    <div class="opp-lms">${lmDots}</div>
                </div>`;
        }).join('');
    }

    // ── Opponent card detail overlay ──────────────────
    window.showOpponentCards = (seat) => {
        const opp = gameState?.players.find(p => p.seat === seat);
        if (!opp) return;
        document.getElementById('mk-opp-cards-overlay')?.remove();

        const cardsHTML = Object.entries(opp.cards ?? {}).length
            ? Object.entries(opp.cards).map(([id, count]) => {
                const card = gameState.card_defs[id];
                const cc   = colorClass(card.type);
                const colors = { blue: '#5DADE2', green: '#7ABF7E', red: '#E08470', purple: '#A98BC4' };
                const bg = colors[cc] ?? '#A89281';
                const diceLabel = Array.isArray(card.dice) ? card.dice.join('–') : card.dice;
                return `<div style="background:${bg};color:#fff;border-radius:8px;padding:6px 10px;font-size:13px;display:flex;justify-content:space-between;align-items:center;gap:12px;">
                    <span>${SYMBOLS[card.symbol] ?? ''} ${esc(card.name)} ×${count}</span>
                    <span style="opacity:.8;font-size:11px;">${diceLabel}</span>
                </div>`;
            }).join('')
            : '<p style="color:#A89281;font-size:13px;margin:0;font-style:italic;">No establishments yet.</p>';

        const lmHTML = (opp.landmarks ?? []).map(lm =>
            `<div style="display:flex;align-items:center;gap:8px;font-size:13px;">
                <div style="width:14px;height:14px;border-radius:3px;background:${lm.built ? '#E8B53C' : 'rgba(78,52,46,.2)'};flex-shrink:0;"></div>
                <span style="color:${lm.built ? '#B68724' : '#A89281'};">${esc(lm.name)}</span>
                ${lm.built ? '<span style="color:#B68724;font-size:11px;">✓</span>' : ''}
            </div>`
        ).join('');

        const overlay = document.createElement('div');
        overlay.id = 'mk-opp-cards-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:998;';
        overlay.innerHTML = `
            <div style="background:#FFF7E6;color:#4E342E;border-radius:18px;padding:24px;max-width:420px;width:90%;max-height:80vh;overflow-y:auto;position:relative;box-shadow:0 18px 30px rgba(78,52,46,.3);">
                <button onclick="document.getElementById('mk-opp-cards-overlay').remove()" style="position:absolute;top:12px;right:14px;background:none;border:none;color:#A89281;font-size:20px;cursor:pointer;">✕</button>
                <h3 style="margin:0 0 4px;font-family:Fredoka,sans-serif;color:#B68724;">${esc(opp.name)}</h3>
                <p style="margin:0 0 16px;color:#A89281;font-size:13px;">💰 ${opp.coins} coins</p>
                <p style="margin:0 0 8px;font-size:11px;color:#A89281;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Establishments</p>
                <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:20px;">${cardsHTML}</div>
                <p style="margin:0 0 8px;font-size:11px;color:#A89281;text-transform:uppercase;letter-spacing:1px;font-weight:700;">Landmarks</p>
                <div style="display:flex;flex-direction:column;gap:8px;">${lmHTML}</div>
            </div>`;
        overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
        document.body.appendChild(overlay);
    };

    // ── Market (two grids) ────────────────────────────
    function renderMarket(state) {
        const me       = state.players.find(p => p.seat === mySeat);
        const isMyTurn = state.active_seat === mySeat && state.phase === 'build';
        const lowEl    = document.getElementById('mk-market-low');
        const highEl   = document.getElementById('mk-market-high');

        function makeCard(card) {
            const supply     = state.supply?.[card.id] ?? 0;
            const soldOut    = supply <= 0;
            const alreadyOwn = card.type === 'Purple Major' && (me?.cards[card.id] ?? 0) >= 1;
            const canAfford  = !soldOut && !alreadyOwn && (me?.coins ?? 0) >= card.cost;
            const buyable    = isMyTurn && canAfford;
            const cc         = colorClass(card.type);
            const afford     = (soldOut || alreadyOwn) ? 'unaffordable' : (canAfford ? 'affordable' : 'unaffordable');
            const diceLabel  = Array.isArray(card.dice) ? card.dice.join('-') : String(card.dice);
            const stockCls   = (!soldOut && supply <= 2) ? 'low' : '';

            return `<div class="card ${cc} ${afford}" data-id="${card.id}"
                        ${buyable ? `onclick="selectCard('${card.id}')"` : ''}>
                <div class="card-top">
                    <span class="card-dice">${diceLabel}</span>
                    <span class="card-class">${SYMBOLS[card.symbol] ?? '🏢'}</span>
                </div>
                <div class="card-body">
                    <div class="card-sym">${SYMBOLS[card.symbol] ?? '🏢'}</div>
                    <div class="card-name">${esc(card.name)}</div>
                    <div class="card-effect">${esc(card.effect)}</div>
                </div>
                <div class="card-bottom">
                    <span class="card-cost">💰${card.cost}</span>
                    <span class="card-stock ${stockCls}">×${soldOut ? 0 : supply}</span>
                </div>
            </div>`;
        }

        const firstDice = c => Array.isArray(c.dice) ? c.dice[0] : c.dice;
        const lowCards  = state.market.filter(c => firstDice(c) <= 6);
        const highCards = state.market.filter(c => firstDice(c) > 6);

        if (lowEl)  lowEl.innerHTML  = lowCards.map(makeCard).join('');
        if (highEl) highEl.innerHTML = highCards.map(makeCard).join('');
    }

    // ── My Area (drawer) ──────────────────────────────
    function renderMyArea(state) {
        const me       = state.players.find(p => p.seat === mySeat);
        if (!me) return;
        const isMyTurn = state.active_seat === mySeat;
        const isBuild  = state.phase === 'build';
        const isTunaRoll = state.phase === 'tuna_roll';

        // Turn banner
        const activeName = state.players.find(p => p.seat === state.active_seat)?.name ?? '';
        setEl('mk-turn-name', isMyTurn ? 'Your Turn' : esc(activeName));
        setEl('mk-turn-phase', PHASE_LABELS[state.phase] ?? state.phase);

        // Phase pill
        updatePhasePill(state.phase);

        // Player info
        setEl('mk-avatar-initials', me.name.charAt(0).toUpperCase());
        setEl('mk-my-name', me.name);
        setEl('mk-coin-count', me.coins);

        // Roll / skip buttons
        const rollBtn = document.getElementById('mk-btn-roll');
        const skipBtn = document.getElementById('mk-btn-skip');
        const showRoll = isMyTurn && (state.phase === 'roll' || isTunaRoll);
        const showSkip = isMyTurn && isBuild;
        if (rollBtn) {
            rollBtn.style.display = showRoll ? '' : 'none';
            rollBtn.textContent = isTunaRoll ? '🐟 Tuna Roll' : '🎲 Roll Dice';
        }
        if (skipBtn) skipBtn.style.display = showSkip ? '' : 'none';

        // Dice result
        const diceEl = document.getElementById('mk-dice-result');
        const sumEl  = document.getElementById('mk-dice-sum');
        const dice = state.last_dice ?? [];
        if (diceEl) {
            if (dice.length === 0) {
                diceEl.innerHTML = '';
                if (sumEl) sumEl.style.display = 'none';
            } else if (dice.length === 1) {
                diceEl.innerHTML = `<span class="dice-box">${dice[0]}</span>`;
                if (sumEl) sumEl.style.display = 'none';
            } else {
                diceEl.innerHTML = `<span class="dice-box">${dice[0]}</span><span class="dice-box">${dice[1]}</span>`;
                if (sumEl) { sumEl.textContent = '= ' + state.last_roll; sumEl.style.display = ''; }
            }
        }

        // Landmarks
        const lmBuilt = me.landmarks.filter(lm => lm.built).length;
        const lmTotal = me.landmarks.length;
        setEl('mk-lm-count', `${lmBuilt}/${lmTotal}`);
        const lmEl = document.getElementById('mk-my-landmarks');
        if (lmEl) {
            lmEl.innerHTML = me.landmarks.map(lm => {
                const canAfford = me.coins >= lm.cost && !lm.built;
                const buyable   = isBuild && isMyTurn && canAfford;
                const cls       = [lm.built ? 'built' : '', buyable ? 'buyable' : ''].join(' ');
                return `<div class="lm-row ${cls}" data-lm="${lm.id}"
                             ${buyable ? `onclick="selectLandmark('${lm.id}')"` : ''}>
                    <div class="lm-icon">${LANDMARK_ICONS[lm.id] ?? '🏛️'}</div>
                    <div class="lm-info">
                        <div class="lm-name">${esc(lm.name)}</div>
                        <div class="lm-eff">${LANDMARK_EFFECTS[lm.id] ?? ''}</div>
                    </div>
                    <div class="lm-cost">${lm.built ? '✓ Built' : '💰' + lm.cost}</div>
                </div>`;
            }).join('');
        }

        // Owned establishments
        const estEntries = Object.entries(me.cards ?? {});
        const estTotal   = estEntries.reduce((s, [, c]) => s + c, 0);
        setEl('mk-est-count', estTotal);
        const cardsEl = document.getElementById('mk-my-cards');
        if (cardsEl) {
            cardsEl.innerHTML = estEntries.length
                ? estEntries.map(([id, count]) => {
                    const card = state.card_defs[id];
                    const cc   = colorClass(card.type);
                    // 0.5.5: show the card's effect on hover via native title (escape() leaves
                    // quotes intact, so also encode " for the attribute context). Native title
                    // can't be clipped by the 0.5.4 overflow:auto container and degrades on touch.
                    const effectTitle = esc(card.effect ?? '').replace(/"/g, '&quot;');
                    return `<div class="owned-card ${cc}" title="${effectTitle}">
                        <span class="owned-sym">${SYMBOLS[card.symbol] ?? '🏢'}</span>
                        <span class="owned-name">${esc(card.name)}</span>
                        <span class="owned-count">×${count}</span>
                    </div>`;
                }).join('')
                : '<p class="mk-no-cards">No establishments yet.</p>';
        }

        // Collapsed strip
        setEl('mk-strip-coin', '💰' + me.coins);
        setEl('mk-strip-cards', estTotal);
        setEl('mk-strip-lm', `${lmBuilt}/${lmTotal}`);
        const stackEl = document.getElementById('mk-strip-lm-stack');
        if (stackEl) {
            stackEl.innerHTML = me.landmarks.map(lm =>
                `<div class="strip-lm ${lm.built ? 'built' : ''}"></div>`
            ).join('');
        }
    }

    function setEl(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    function updatePhasePill(phase) {
        const p1 = document.getElementById('mk-phase-1');
        const p2 = document.getElementById('mk-phase-2');
        const p3 = document.getElementById('mk-phase-3');
        if (!p1) return;
        if (phase === 'roll' || phase === 'tuna_roll') {
            p1.className = 'phase-step active';
            p2.className = 'phase-step';
            p3.className = 'phase-step';
        } else {
            p1.className = 'phase-step done';
            p2.className = 'phase-step done';
            p3.className = 'phase-step active';
        }
    }

    // ── Build selection ───────────────────────────────
    let selectedCard = null, selectedLandmark = null;

    window.selectCard = (id) => {
        selectedCard = id; selectedLandmark = null;
        document.querySelectorAll('.card').forEach(el => el.classList.toggle('mk-selected', el.dataset.id === id));
        document.querySelectorAll('.lm-row').forEach(el => el.classList.remove('mk-selected'));
        showBuildConfirm(id, 'card');
    };

    window.selectLandmark = (id) => {
        selectedLandmark = id; selectedCard = null;
        document.querySelectorAll('.lm-row').forEach(el => el.classList.toggle('mk-selected', el.dataset.lm === id));
        document.querySelectorAll('.card').forEach(el => el.classList.remove('mk-selected'));
        showBuildConfirm(id, 'landmark');
    };

    function showBuildConfirm(id, type) {
        const me   = gameState.players.find(p => p.seat === mySeat);
        const item = type === 'card'
            ? gameState.market.find(c => c.id === id)
            : me?.landmarks.find(l => l.id === id);
        showPrompt(`Buy ${item.name} for 💰${item.cost}?`, null,
            () => send('build', { type, id }),
            () => {
                selectedCard = null; selectedLandmark = null;
                document.querySelectorAll('.card, .lm-row').forEach(el => el.classList.remove('mk-selected'));
            }
        );
    }

    // ── Roll / Skip ───────────────────────────────────
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

    // ── Prompt overlay ────────────────────────────────
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

    // ── TV Station ────────────────────────────────────
    function showTVStationUI(state) {
        if (document.getElementById('mk-tvs-overlay')) return;
        const opps = state.players.filter(p => p.seat !== mySeat);
        if (!opps.length) { send('tv_station_pick', { target_seat: -1 }); return; }

        const overlay = document.createElement('div');
        overlay.id = 'mk-tvs-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.65);display:flex;align-items:center;justify-content:center;z-index:998;';
        overlay.innerHTML = `
            <div style="background:#FFF7E6;color:#4E342E;border-radius:18px;padding:24px;max-width:400px;width:90%;text-align:center;box-shadow:0 18px 30px rgba(78,52,46,.3);">
                <h3 style="font-family:Fredoka,sans-serif;color:#B68724;margin:0 0 16px;">📺 TV Station — Take 5 coins from:</h3>
                <div style="display:flex;flex-direction:column;gap:10px;">
                    ${opps.map(o => `
                        <button onclick="tvsPickTarget(${o.seat})"
                            style="background:#FFF7E6;color:#4E342E;border:2px solid #E9D9B8;border-radius:10px;
                                   padding:12px 16px;cursor:pointer;font-size:15px;font-family:Fredoka,sans-serif;font-weight:600;
                                   display:flex;justify-content:space-between;align-items:center;
                                   transition:border-color .15s;">
                            <span>${esc(o.name)}</span>
                            <span style="color:#B68724;font-weight:700;">💰 ${o.coins}</span>
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

    // ── Business Center ───────────────────────────────
    function showBusinessCenterUI(state) {
        if (document.getElementById('mk-bc-overlay')) return;
        const me    = state.players.find(p => p.seat === mySeat);
        const opps  = state.players.filter(p => p.seat !== mySeat);
        const ccColors = { blue:'#5DADE2', green:'#7ABF7E', red:'#E08470', purple:'#A98BC4' };

        const myCards = Object.entries(me.cards)
            .filter(([id]) => state.card_defs[id]?.type !== 'Purple Major')
            .map(([id, count]) => ({ id, count, ...state.card_defs[id] }));

        const oppGroups = opps.map(o => ({
            seat: o.seat, name: o.name,
            cards: Object.entries(o.cards)
                .filter(([id]) => state.card_defs[id]?.type !== 'Purple Major')
                .map(([id, count]) => ({ id, count, ...state.card_defs[id] }))
        })).filter(o => o.cards.length > 0);

        if (!myCards.length || !oppGroups.length) { send('skip_business_center'); return; }

        let selMy = null, selOppSeat = null, selOppCard = null;
        const overlay = document.createElement('div');
        overlay.id = 'mk-bc-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.65);display:flex;align-items:center;justify-content:center;z-index:998;';

        function renderBC() {
            const myHTML = myCards.map(c => {
                const cc = colorClass(c.type);
                const bg = ccColors[cc] ?? '#A89281';
                return `<button onclick="bcMy('${c.id}')"
                    style="background:${bg};color:#fff;border:2.5px solid ${selMy===c.id?'#4E342E':'transparent'};
                           border-radius:8px;padding:6px 10px;cursor:pointer;font-size:13px;margin:3px;font-family:Nunito,sans-serif;">
                    ${esc(c.name)} ×${c.count}</button>`;
            }).join('');

            const oppsHTML = oppGroups.map(o =>
                `<div style="margin-bottom:10px;">
                    <div style="font-size:11px;color:#A89281;margin-bottom:4px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">${esc(o.name)}</div>
                    ${o.cards.map(c => {
                        const cc = colorClass(c.type);
                        const bg = ccColors[cc] ?? '#A89281';
                        return `<button onclick="bcOpp(${o.seat},'${c.id}')"
                            style="background:${bg};color:#fff;
                                   border:2.5px solid ${selOppSeat===o.seat&&selOppCard===c.id?'#4E342E':'transparent'};
                                   border-radius:8px;padding:6px 10px;cursor:pointer;font-size:13px;margin:3px;font-family:Nunito,sans-serif;">
                            ${esc(c.name)} ×${c.count}</button>`;
                    }).join('')}
                </div>`
            ).join('');

            const canConfirm = selMy && selOppCard;
            overlay.innerHTML = `
                <div style="background:#FFF7E6;color:#4E342E;border-radius:18px;padding:24px;
                            max-width:500px;width:90%;max-height:82vh;overflow-y:auto;box-shadow:0 18px 30px rgba(78,52,46,.3);">
                    <h3 style="font-family:Fredoka,sans-serif;color:#B68724;margin:0 0 14px;">🔄 Business Center — Trade a Card</h3>
                    <p style="font-weight:700;color:#A89281;margin:0 0 8px;font-size:13px;">Your card to give:</p>
                    <div style="margin-bottom:16px;">${myHTML}</div>
                    <p style="font-weight:700;color:#A89281;margin:0 0 8px;font-size:13px;">Opponent's card to receive:</p>
                    <div style="margin-bottom:20px;">${oppsHTML}</div>
                    <div style="display:flex;gap:10px;flex-wrap:wrap;">
                        <button onclick="bcConfirm()" class="btn btn-primary"
                            style="opacity:${canConfirm?1:.4};" ${canConfirm?'':'disabled'}>Confirm Trade</button>
                        <button onclick="bcSkip()" class="btn btn-secondary">Skip</button>
                    </div>
                </div>`;
        }

        window.bcMy     = id => { selMy = id; renderBC(); };
        window.bcOpp    = (seat, id) => { selOppSeat = seat; selOppCard = id; renderBC(); };
        window.bcConfirm = () => {
            if (!selMy || selOppSeat === null || !selOppCard) return;
            send('business_center', { my_card: selMy, opp_seat: selOppSeat, opp_card: selOppCard });
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

    // ── End screen ────────────────────────────────────
    function showEndScreen(state) {
        const overlay = document.getElementById('mk-end-overlay');
        const scores  = state.scores ?? [];
        const winner  = scores.find(s => s.is_winner);
        const iWon    = winner && winner.seat === mySeat;

        const titleEl = document.getElementById('mk-end-title');
        titleEl.textContent = iWon ? '🎉 You Win!' : (winner ? 'Better Luck Next Time!' : 'Game Over!');
        titleEl.classList.toggle('mk-loss', !iWon);

        const medals = ['🥇','🥈','🥉'];
        document.getElementById('mk-scores-list').innerHTML = scores.map((s, i) => `
            <div class="mk-score-row ${s.is_winner ? 'winner' : ''}">
                <span class="mk-score-rank">${medals[i] ?? `${i+1}.`}</span>
                <span class="mk-score-name">${esc(s.name)}</span>
                <span class="mk-score-pts">${s.landmarks_built} / 6 🏛️</span>
            </div>`).join('');

        overlay.classList.remove('mk-hidden');
    }

    document.getElementById('mk-btn-exit-lobby').addEventListener('click', () => {
        ws?.close();
        window.location.href = MK.homeUrl;
    });

    // ── Helper ────────────────────────────────────────
    function colorClass(type) {
        if (type.includes('Primary'))    return 'blue';
        if (type.includes('Secondary'))  return 'green';
        if (type.includes('Restaurant')) return 'red';
        if (type.includes('Major'))      return 'purple';
        return '';
    }

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
