<?php
if (!defined('ABSPATH')) exit;

// Enqueue assets only on pages that use our shortcodes
add_action('wp_enqueue_scripts', function () {
    if (!mk_page_needs_assets()) return;

    wp_enqueue_style('mk-style', MK_URL . 'assets/style.css', [], filemtime(MK_DIR . 'assets/style.css'));
    wp_enqueue_script('mk-app', MK_URL . 'assets/app.js', [], filemtime(MK_DIR . 'assets/app.js'), true);

    $play_page = get_page_by_path('play');
    wp_localize_script('mk-app', 'MK', [
        'apiBase'   => rest_url('machi-koro/v1'),
        'nonce'     => wp_create_nonce('wp_rest'),
        'wsUrl'     => home_url('', 'http') === home_url('', 'https')
                        ? 'wss://' . $_SERVER['HTTP_HOST'] . '/ws/'
                        : 'ws://' . $_SERVER['HTTP_HOST'] . '/ws/',
        'userId'    => get_current_user_id(),
        'loggedIn'  => is_user_logged_in(),
        'homeUrl'   => $play_page ? get_permalink($play_page) : '/',
        'mySeat'    => (int) ($_SESSION['mk_seat'] ?? -1),
    ]);
});

function mk_page_needs_assets() {
    global $post;
    if (!$post) return false;
    $tags = ['mk_home', 'mk_lobby', 'mk_waiting_room', 'mk_game', 'mk_rules'];
    foreach ($tags as $tag) {
        if (has_shortcode($post->post_content, $tag)) return true;
    }
    return false;
}

// [mk_home] — landing page
add_shortcode('mk_home', function () {
    ob_start(); ?>
    <div id="mk-home" class="mk-page">
        <h1>Machi Koro</h1>
        <div class="mk-actions">
            <button id="mk-btn-create" class="mk-btn mk-btn-primary">Create Table</button>
            <button id="mk-btn-browse" class="mk-btn mk-btn-secondary">Browse Tables</button>
        </div>
        <div class="mk-join-row">
            <input id="mk-join-code" type="text" placeholder="Enter join code (e.g. MK-A1B2C3)" maxlength="12" />
            <button id="mk-btn-join-code" class="mk-btn">Join</button>
        </div>
        <div id="mk-browse-panel" class="mk-hidden">
            <input id="mk-search" type="text" placeholder="Search tables..." />
            <div id="mk-table-list"></div>
        </div>
        <div id="mk-create-panel" class="mk-hidden">
            <input id="mk-table-name" type="text" placeholder="Table name" maxlength="80" />
            <?php if (!is_user_logged_in()): ?>
            <input id="mk-guest-name" type="text" placeholder="Your name" maxlength="64" />
            <?php endif; ?>
            <div class="mk-create-btns">
                <button id="mk-btn-create-public" class="mk-btn mk-btn-primary">Create Public</button>
                <button id="mk-btn-create-private" class="mk-btn mk-btn-secondary">Create Private</button>
            </div>
            <p class="mk-create-hint">Public tables appear in Browse. Private tables are hidden — share the code to invite friends.</p>
        </div>
    </div>
    <?php return ob_get_clean();
});

// [mk_waiting_room] — lobby page after joining
add_shortcode('mk_waiting_room', function () {
    ob_start(); ?>
    <div id="mk-waiting-room" class="mk-page">
        <div class="mk-code-display">
            <span id="mk-table-code"></span>
            <button id="mk-btn-copy-code" class="mk-btn-small">Copy</button>
        </div>
        <div id="mk-player-list"></div>
        <div class="mk-waiting-actions">
            <button id="mk-btn-start" class="mk-btn mk-btn-primary mk-hidden">Start Game</button>
            <p id="mk-start-error" class="mk-error-msg mk-hidden">Not enough players at the table.</p>
            <button id="mk-btn-leave" class="mk-btn mk-btn-danger">Leave Table</button>
        </div>
    </div>
    <?php return ob_get_clean();
});

// [mk_rules] — rules reference page
add_shortcode('mk_rules', function () {
    ob_start(); ?>
    <div id="mk-rules" class="mk-page">

        <div class="mk-rules-hero">
            <h1>🏙️ Machi Koro</h1>
            <p class="mk-rules-edition">Harbor Expansion — Rules</p>
        </div>

        <section class="mk-rules-section">
            <h2>🎯 Goal</h2>
            <p>Be the first player to build all <strong>6 landmarks</strong>. City Hall is free and pre-built for everyone at the start.</p>
        </section>

        <section class="mk-rules-section">
            <h2>🔄 Each Turn</h2>
            <div class="mk-rules-steps">
                <div class="mk-rules-step">
                    <span class="mk-rules-step-num">1</span>
                    <strong>Roll Dice</strong>
                    Roll 1 die (or 2 if you have Train Station). You may reroll once with Radio Tower.
                </div>
                <div class="mk-rules-step">
                    <span class="mk-rules-step-num">2</span>
                    <strong>Earn Income</strong>
                    Cards with matching dice activate in order:
                    <span class="mk-rules-order"><span class="mk-ro-red">① Red</span> → <span class="mk-ro-blue">② Blue</span> → <span class="mk-ro-green">③ Green</span> → <span class="mk-ro-purple">④ Purple</span></span>
                </div>
                <div class="mk-rules-step">
                    <span class="mk-rules-step-num">3</span>
                    <strong>Build</strong>
                    Optionally buy one establishment or landmark. Then your turn ends.
                </div>
            </div>
        </section>

        <section class="mk-rules-section">
            <h2>🎨 Card Colors</h2>
            <div class="mk-rules-types">
                <div class="mk-rules-type-card mk-rules-blue">
                    <strong>🔵 Blue</strong><br>Primary Industry<br>
                    <small>Activates on <em>anyone's</em> turn. Bank pays you.</small>
                </div>
                <div class="mk-rules-type-card mk-rules-green">
                    <strong>🟢 Green</strong><br>Secondary Industry<br>
                    <small>Activates on <em>your turn only</em>. Bank pays you.</small>
                </div>
                <div class="mk-rules-type-card mk-rules-red">
                    <strong>🔴 Red</strong><br>Restaurant<br>
                    <small>Activates on an <em>opponent's turn</em>. You take coins from them.</small>
                </div>
                <div class="mk-rules-type-card mk-rules-purple">
                    <strong>🟣 Purple</strong><br>Major Establishment<br>
                    <small>Your turn only. Powerful effects. Max <em>1 per player</em>.</small>
                </div>
            </div>
        </section>

        <section class="mk-rules-section">
            <h2>🏪 Establishments</h2>
            <p style="color:#aaa;margin-bottom:4px;">Cards resolve in this order each roll:</p>
            <div class="mk-rules-order-bar">
                <span class="mk-ro-red">① Red</span>
                <span class="mk-ro-arrow">→</span>
                <span class="mk-ro-blue">② Blue</span>
                <span class="mk-ro-arrow">+</span>
                <span class="mk-ro-green">③ Green</span>
                <span class="mk-ro-arrow">→</span>
                <span class="mk-ro-purple">④ Purple</span>
            </div>

            <h3 class="mk-rules-color-h mk-rules-red-h"><span class="mk-rules-order-badge">①</span> 🔴 Red — Restaurant (opponent's turn — they pay you)</h3>
            <div class="mk-rules-table-wrap">
                <table class="mk-rules-table">
                    <thead><tr><th>Card</th><th>Symbol</th><th>Dice</th><th>Cost</th><th>Effect</th></tr></thead>
                    <tbody>
                        <tr class="mk-rt-red"><td>Sushi Bar ⚓</td><td>☕</td><td>1</td><td>💰2</td><td>Requires Harbor. Take 3 coins from the active player.</td></tr>
                        <tr class="mk-rt-red"><td>Café</td><td>☕</td><td>3</td><td>💰2</td><td>Take 1 coin from the active player.</td></tr>
                        <tr class="mk-rt-red"><td>Pizza Joint</td><td>☕</td><td>7</td><td>💰1</td><td>Take 1 coin from the active player.</td></tr>
                        <tr class="mk-rt-red"><td>Hamburger Stand</td><td>☕</td><td>8</td><td>💰1</td><td>Take 1 coin from the active player.</td></tr>
                        <tr class="mk-rt-red"><td>Family Restaurant</td><td>☕</td><td>9–10</td><td>💰3</td><td>Take 2 coins from the active player.</td></tr>
                    </tbody>
                </table>
            </div>

            <h3 class="mk-rules-color-h mk-rules-blue-h"><span class="mk-rules-order-badge">②</span> 🔵 Blue — Primary Industry (everyone earns)</h3>
            <div class="mk-rules-table-wrap">
                <table class="mk-rules-table">
                    <thead><tr><th>Card</th><th>Symbol</th><th>Dice</th><th>Cost</th><th>Effect</th></tr></thead>
                    <tbody>
                        <tr class="mk-rt-blue"><td>Wheat Field</td><td>🌾</td><td>1</td><td>💰1</td><td>Get 1 coin from the bank.</td></tr>
                        <tr class="mk-rt-blue"><td>Ranch</td><td>🐄</td><td>2</td><td>💰1</td><td>Get 1 coin from the bank.</td></tr>
                        <tr class="mk-rt-blue"><td>Flower Garden</td><td>🌾</td><td>4</td><td>💰2</td><td>Get 1 coin from the bank.</td></tr>
                        <tr class="mk-rt-blue"><td>Forest</td><td>⚙️</td><td>5</td><td>💰3</td><td>Get 1 coin from the bank.</td></tr>
                        <tr class="mk-rt-blue"><td>Mackerel Boat ⚓</td><td>🐟</td><td>8</td><td>💰3</td><td>Requires Harbor. Get 3 coins from the bank.</td></tr>
                        <tr class="mk-rt-blue"><td>Mine</td><td>⚙️</td><td>9</td><td>💰6</td><td>Get 5 coins from the bank.</td></tr>
                        <tr class="mk-rt-blue"><td>Apple Orchard</td><td>🌾</td><td>10</td><td>💰3</td><td>Get 3 coins from the bank.</td></tr>
                        <tr class="mk-rt-blue"><td>Tuna Boat ⚓</td><td>🐟</td><td>12–13–14</td><td>💰5</td><td>Requires Harbor. Roll 2 dice and get that many coins.</td></tr>
                    </tbody>
                </table>
            </div>

            <h3 class="mk-rules-color-h mk-rules-green-h"><span class="mk-rules-order-badge">③</span> 🟢 Green — Secondary Industry (your turn only)</h3>
            <div class="mk-rules-table-wrap">
                <table class="mk-rules-table">
                    <thead><tr><th>Card</th><th>Symbol</th><th>Dice</th><th>Cost</th><th>Effect</th></tr></thead>
                    <tbody>
                        <tr class="mk-rt-green"><td>Bakery</td><td>🍞</td><td>2–3</td><td>💰1</td><td>Get 1 coin from the bank.</td></tr>
                        <tr class="mk-rt-green"><td>Convenience Store</td><td>🍞</td><td>4</td><td>💰2</td><td>Get 3 coins from the bank.</td></tr>
                        <tr class="mk-rt-green"><td>Flower Shop</td><td>🍞</td><td>6</td><td>💰1</td><td>Get 1 coin per Flower Garden you own.</td></tr>
                        <tr class="mk-rt-green"><td>Cheese Factory</td><td>🏭</td><td>7</td><td>💰5</td><td>Get 3 coins per Ranch you own.</td></tr>
                        <tr class="mk-rt-green"><td>Furniture Factory</td><td>🏭</td><td>8</td><td>💰3</td><td>Get 3 coins per Forest or Mine you own.</td></tr>
                        <tr class="mk-rt-green"><td>Farmers Market</td><td>🍎</td><td>11–12</td><td>💰2</td><td>Get 2 coins per wheat-symbol card you own.</td></tr>
                        <tr class="mk-rt-green"><td>Food Warehouse ⚓</td><td>🏭</td><td>12–13</td><td>💰2</td><td>Requires Harbor. Get 2 coins per cup ☕ card you own.</td></tr>
                    </tbody>
                </table>
            </div>

            <h3 class="mk-rules-color-h mk-rules-purple-h"><span class="mk-rules-order-badge">④</span> 🟣 Purple — Major Establishments (your turn only, max 1 per player)</h3>
            <div class="mk-rules-table-wrap">
                <table class="mk-rules-table">
                    <thead><tr><th>Card</th><th>Symbol</th><th>Dice</th><th>Cost</th><th>Effect</th></tr></thead>
                    <tbody>
                        <tr class="mk-rt-purple"><td>Publisher</td><td>🏰</td><td>7</td><td>💰5</td><td>Take 1 coin per cup ☕ or bread 🍞 card from each opponent.</td></tr>
                        <tr class="mk-rt-purple"><td>Tax Office</td><td>🏰</td><td>8–9</td><td>💰4</td><td>Take half (rounded down) from each opponent who has 10+ coins.</td></tr>
                        <tr class="mk-rt-purple"><td>Stadium</td><td>🏰</td><td>6</td><td>💰6</td><td>Take 2 coins from each opponent.</td></tr>
                        <tr class="mk-rt-purple"><td>TV Station</td><td>🏰</td><td>6</td><td>💰7</td><td>Take 5 coins from any one opponent (you choose who).</td></tr>
                        <tr class="mk-rt-purple"><td>Business Center</td><td>🏰</td><td>6</td><td>💰8</td><td>Trade one non-Major establishment with any opponent.</td></tr>
                    </tbody>
                </table>
            </div>
        </section>

        <section class="mk-rules-section">
            <h2>🏛️ Landmarks</h2>
            <p>Build all 6 to win. Buy one per turn during the Build phase.</p>
            <div class="mk-rules-table-wrap">
                <table class="mk-rules-table mk-rules-lm-table">
                    <thead><tr><th>Landmark</th><th>Cost</th><th>Effect</th></tr></thead>
                    <tbody>
                        <tr><td>🏛️ City Hall</td><td>Free (pre-built)</td><td>After income, if you have 0 coins, get 1 coin from the bank.</td></tr>
                        <tr><td>⚓ Harbor</td><td>💰2</td><td>When you roll 10 or more, add +2 to the total. Unlocks Mackerel Boat, Tuna Boat, Sushi Bar &amp; Food Warehouse.</td></tr>
                        <tr><td>🚂 Train Station</td><td>💰4</td><td>You may choose to roll 1 or 2 dice each turn.</td></tr>
                        <tr><td>🛍️ Shopping Mall</td><td>💰10</td><td>Your cup ☕ and bread 🍞 cards each earn +1 coin when they activate (including red cards).</td></tr>
                        <tr><td>🎡 Amusement Park</td><td>💰16</td><td>If you roll doubles, take another turn. Only once per round — doubles on the bonus turn don't chain.</td></tr>
                        <tr><td>📻 Radio Tower</td><td>💰22</td><td>Once per turn, you may reroll the dice and use the new result.</td></tr>
                        <tr><td>✈️ Airport</td><td>💰30</td><td>If you skip building during the Build phase, receive 10 coins from the bank.</td></tr>
                    </tbody>
                </table>
            </div>
        </section>

        <section class="mk-rules-section">
            <h2>💡 Good to Know</h2>
            <ul class="mk-rules-notes">
                <li><strong>Income order:</strong> Red cards resolve first (opponents earn before you), then blue, then green, then purple.</li>
                <li><strong>Shopping Mall</strong> also boosts red ☕ cards — a Café owner with Shopping Mall takes 2 instead of 1.</li>
                <li><strong>TV Station &amp; Business Center</strong> are interactive — the game pauses and asks you to pick a target.</li>
                <li><strong>Tuna Boat</strong> triggers a second dice roll — only players with Tuna Boat and Harbor participate.</li>
                <li><strong>Supply limit:</strong> Each card has 6 copies in the market. Purple Major cards have 1 copy per player in the game. Sold-out cards cannot be bought.</li>
                <li><strong>Coins in the bank are unlimited.</strong> You start with 3 coins.</li>
            </ul>
        </section>

        <div class="mk-rules-cta">
            <a href="/play/" class="mk-btn mk-btn-primary">Play Now →</a>
        </div>

    </div>
    <?php return ob_get_clean();
});

// [mk_game] — game table page
add_shortcode('mk_game', function () {
    ob_start(); ?>
    <div id="mk-toast-container"></div>
    <div id="mk-leave-game">
        <button id="mk-btn-leave-game" class="mk-btn mk-btn-danger">Leave Game</button>
    </div>
    <div id="mk-game">
        <div id="mk-game-main">
            <div id="mk-opponents-ring"></div>
            <div id="mk-table-surface">
                <div id="mk-market-header">
                    <div class="mk-market-title-block">
                        <h2>Marketplace</h2>
                        <p>Select your next development</p>
                    </div>
                    <div id="mk-filter-tabs">
                        <button class="mk-filter-tab active" data-filter="all">All</button>
                        <button class="mk-filter-tab" data-filter="blue">Blue</button>
                        <button class="mk-filter-tab" data-filter="green">Green</button>
                        <button class="mk-filter-tab" data-filter="red">Red</button>
                        <button class="mk-filter-tab" data-filter="purple">Purple</button>
                    </div>
                </div>
                <div id="mk-market"></div>
                <div id="mk-roll-center" class="mk-hidden">
                    <p class="mk-roll-prompt">It's your turn!</p>
                    <button id="mk-btn-roll">Roll Dice</button>
                </div>
            </div>
            <div id="mk-player-area">
                <div id="mk-dice-area">
                    <div id="mk-dice-result"></div>
                    <div id="mk-build-actions">
                        <button id="mk-btn-skip" class="mk-btn">Skip Build</button>
                    </div>
                </div>
                <div id="mk-reactions-bar">
                    <?php foreach (['😂','😮','😤','🤔','😎','👏','😭','🎉','💀','😈'] as $e): ?>
                    <button class="mk-reaction-btn" onclick="sendReaction('<?= $e ?>')"><?= $e ?></button>
                    <?php endforeach; ?>
                </div>
            </div>
        </div>
        <aside id="mk-sidebar-right">
            <div id="mk-player-profile">
                <div class="mk-profile-avatar" id="mk-avatar-initials">?</div>
                <div class="mk-profile-info">
                    <div class="mk-profile-name-row">
                        <span id="mk-my-name"></span>
                        <span class="mk-you-badge">YOU</span>
                    </div>
                    <div class="mk-profile-sub">Harbor Expansion</div>
                    <span id="mk-my-reaction" class="mk-my-reaction-bubble"></span>
                </div>
            </div>
            <div class="mk-wealth-card">
                <div class="mk-wealth-inner">
                    <div>
                        <div class="mk-wealth-label">Total Wealth</div>
                        <div class="mk-wealth-value">💰 <span id="mk-coin-count">0</span></div>
                    </div>
                    <div class="mk-rank-block">
                        <div class="mk-wealth-label">Income Rank</div>
                        <div class="mk-income-rank" id="mk-income-rank">#–</div>
                    </div>
                </div>
            </div>
            <div class="mk-right-section">
                <div class="mk-right-section-hdr">
                    Your Establishments
                    <span class="mk-count-badge" id="mk-est-count">0</span>
                </div>
                <div id="mk-my-cards"></div>
            </div>
            <div class="mk-right-section">
                <div class="mk-right-section-hdr">Landmarks</div>
                <div id="mk-my-landmarks" class="mk-right-landmarks"></div>
            </div>
            <div class="mk-sidebar-actions">
                <button class="mk-btn mk-btn-secondary" disabled>Coin Store</button>
                <button class="mk-btn mk-btn-secondary" disabled>History</button>
            </div>
        </aside>
        <div id="mk-prompt-overlay" class="mk-hidden">
            <div id="mk-prompt-box">
                <p id="mk-prompt-text"></p>
                <button id="mk-prompt-yes" class="mk-btn mk-btn-primary">Yes</button>
                <button id="mk-prompt-no" class="mk-btn">No</button>
            </div>
        </div>
        <div id="mk-end-overlay" class="mk-hidden">
            <div id="mk-end-box">
                <h2 id="mk-end-title">Game Over!</h2>
                <div id="mk-scores-list"></div>
                <div class="mk-end-actions">
                    <button id="mk-btn-exit-lobby" class="mk-btn mk-btn-primary">Exit to Lobby</button>
                </div>
            </div>
        </div>
    </div>
    <?php return ob_get_clean();
});
