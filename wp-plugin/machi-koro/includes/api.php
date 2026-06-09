<?php
if (!defined('ABSPATH')) exit;

// These endpoints are intentionally public (guests with no WP login must reach
// them). Authorization for privileged actions is enforced *inside* the handlers:
// kick/start require the caller's identity to match the table's stored host_id,
// and rename requires host-or-seat-owner. So permission_callback stays open and
// the real checks live where the identity + table row are both available.
add_action('rest_api_init', function () {
    $ns = 'machi-koro/v1';

    register_rest_route($ns, '/tables', [
        ['methods' => 'GET',  'callback' => 'mk_api_list_tables',  'permission_callback' => '__return_true'],
        ['methods' => 'POST', 'callback' => 'mk_api_create_table', 'permission_callback' => '__return_true'],
    ]);

    register_rest_route($ns, '/tables/(?P<code>[A-Z0-9\-]+)', [
        ['methods' => 'GET', 'callback' => 'mk_api_get_table', 'permission_callback' => '__return_true'],
    ]);

    register_rest_route($ns, '/tables/(?P<code>[A-Z0-9\-]+)/join', [
        ['methods' => 'POST', 'callback' => 'mk_api_join_table', 'permission_callback' => '__return_true'],
    ]);

    register_rest_route($ns, '/tables/(?P<code>[A-Z0-9\-]+)/kick', [
        ['methods' => 'POST', 'callback' => 'mk_api_kick_player', 'permission_callback' => '__return_true'],
    ]);

    register_rest_route($ns, '/tables/(?P<code>[A-Z0-9\-]+)/start', [
        ['methods' => 'POST', 'callback' => 'mk_api_start_game', 'permission_callback' => '__return_true'],
    ]);

    register_rest_route($ns, '/tables/(?P<code>[A-Z0-9\-]+)/rename', [
        ['methods' => 'POST', 'callback' => 'mk_api_rename_player', 'permission_callback' => '__return_true'],
    ]);

    register_rest_route($ns, '/leaderboard', [
        ['methods' => 'GET', 'callback' => 'mk_api_leaderboard', 'permission_callback' => '__return_true'],
    ]);
});

function mk_api_list_tables($req) {
    global $wpdb;
    $search = sanitize_text_field($req->get_param('search') ?? '');
    $like = '%' . $wpdb->esc_like($search) . '%';

    $rows = $wpdb->get_results($wpdb->prepare(
        "SELECT t.id, t.code, t.name, t.game_version, t.sharp, t.variable_supply,
                t.is_public, t.status,
                (t.password_hash IS NOT NULL) AS is_protected,
                COUNT(p.id) AS player_count
         FROM {$wpdb->prefix}mk_tables t
         LEFT JOIN {$wpdb->prefix}mk_players p ON p.table_id = t.id
         WHERE t.is_public = 1 AND t.status = 'waiting' AND t.name LIKE %s
         GROUP BY t.id
         ORDER BY t.created_at DESC
         LIMIT 50",
        $like
    ));

    // Cast so JSON carries a real boolean — the string "0" would be truthy in JS.
    foreach ($rows as $r) {
        $r->is_protected    = (bool) $r->is_protected;
        $r->sharp           = (bool) $r->sharp;
        $r->variable_supply = (bool) $r->variable_supply;
        $r->player_count    = (int) $r->player_count;
    }

    return rest_ensure_response($rows);
}

function mk_api_create_table($req) {
    global $wpdb;
    $host_id = mk_current_identity();

    // Throttle table creation (≤ 5 per minute). Key on user id or client IP, NOT
    // the guest identity — a guest can rotate X-MK-Guest to dodge a per-identity
    // counter (QA-005).
    if (!mk_rate_limit(mk_rate_limit_key('create'), 5, 60))
        return mk_err('rate_limited', 'Too many tables created — please slow down', 429);

    // Name is optional; fall back to a default when blank rather than erroring.
    $raw_name = $req->get_param('name');
    if ($raw_name === null || trim((string) $raw_name) === '') {
        $name = 'Machi Koro Table';
    } else {
        $name = mk_validate_name($raw_name, 40);
        if (is_wp_error($name)) return $name;
    }
    $public = (bool) ($req->get_param('is_public') ?? true);

    // Game version (B4): 'basic' | 'harbour'. Defaults to 'harbour' (current live
    // behavior); an unknown value falls back rather than erroring, matching the
    // engine's defensive version→config mapping.
    $allowed_versions = ['basic', 'harbour'];
    $version = strtolower(trim((string) ($req->get_param('version') ?? 'harbour')));
    if (!in_array($version, $allowed_versions, true)) {
        $version = 'harbour';
    }

    // Sharp add-on (D-BE): boolean, default false. The base version above and this
    // flag together identify the composed config (engine config_for(version, sharp)).
    // rest_sanitize_boolean handles real bools and "true"/"false"/"1"/"0" strings.
    $sharp = rest_sanitize_boolean($req->get_param('sharp') ?? false);

    // Variable Supply: host-toggleable supply mode, boolean, default false.
    // Fully independent of sharp — available for any version.
    $variable_supply = rest_sanitize_boolean($req->get_param('variable_supply') ?? false);

    $code = mk_generate_code();

    $data = [
        'code'            => $code,
        'name'            => $name,
        'game_version'    => $version,
        'sharp'           => $sharp ? 1 : 0,
        'variable_supply' => $variable_supply ? 1 : 0,
        'host_id'         => $host_id,
        'is_public'       => $public ? 1 : 0,
    ];
    // Optional password protection (TASK-006): store a salted hash only when a
    // non-empty password is supplied. Never store the plaintext.
    $password = (string) ($req->get_param('password') ?? '');
    if ($password !== '') {
        $data['password_hash'] = wp_hash_password($password);
    }
    $wpdb->insert("{$wpdb->prefix}mk_tables", $data);

    $table_id = $wpdb->insert_id;

    // Seat the host as player 0
    $display = mk_unique_guest_name($table_id, mk_current_display_name($req));
    mk_seat_player($table_id, $host_id, $display, 0, true);

    return rest_ensure_response(['code' => $code]);
}

function mk_api_get_table($req) {
    global $wpdb;
    $code = mk_validate_code($req['code']);
    if (is_wp_error($code)) return $code;

    // WEB-001: never SELECT t.* here — that leaked password_hash and host_id to a
    // public endpoint. Expose only safe columns + the derived is_protected flag.
    $row = $wpdb->get_row($wpdb->prepare(
        "SELECT t.id, t.code, t.name, t.game_version, t.sharp, t.variable_supply,
                t.is_public, t.status, t.created_at,
                (t.password_hash IS NOT NULL) AS is_protected
         FROM {$wpdb->prefix}mk_tables t WHERE t.code = %s",
        $code
    ));
    if (!$row) return mk_err('not_found', 'Table not found', 404);
    $row->is_protected    = (bool) $row->is_protected;
    $row->sharp           = (bool) $row->sharp;
    $row->variable_supply = (bool) $row->variable_supply;

    $players = $wpdb->get_results($wpdb->prepare(
        "SELECT p.id, p.seat, p.is_host, p.user_id, p.guest_name,
                COALESCE(u.display_name, p.guest_name) AS display_name
         FROM {$wpdb->prefix}mk_players p
         LEFT JOIN {$wpdb->users} u ON u.ID = p.user_id
         WHERE p.table_id = %d ORDER BY p.seat",
        $row->id
    ));

    $row->players = $players;
    return rest_ensure_response($row);
}

function mk_api_join_table($req) {
    global $wpdb;
    $code = mk_validate_code($req['code']);
    if (is_wp_error($code)) return $code;

    $table = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$wpdb->prefix}mk_tables WHERE code = %s", $code
    ));

    if (!$table) return mk_err('not_found', 'Table not found', 404);
    if ($table->status !== 'waiting') return mk_err('started', 'Game already started', 409);

    // Password gate (TASK-006): protected tables require a correct password.
    // password_hash stays server-side; only the join result (seat/token) is returned.
    if (!empty($table->password_hash)) {
        $password = (string) ($req->get_param('password') ?? '');
        if ($password === '' || !wp_check_password($password, $table->password_hash))
            return mk_err('forbidden', 'Wrong password', 403);
    }

    // Cap is on player COUNT (≤ 5 players), independent of seat numbers.
    $count = (int) $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM {$wpdb->prefix}mk_players WHERE table_id = %d", $table->id
    ));
    if ($count >= 5) return mk_err('full', 'Table is full', 409);

    // Allocate the next seat as MAX(seat)+1, NOT COUNT(*): after a kick, COUNT(*)
    // can point back at a still-occupied seat, letting two players hold valid
    // tokens for the same seat (QA-004). MAX+1 may leave harmless gaps but
    // guarantees one owner per seat. -1 base => first seat is 0.
    $seat = (int) $wpdb->get_var($wpdb->prepare(
        "SELECT COALESCE(MAX(seat), -1) + 1 FROM {$wpdb->prefix}mk_players WHERE table_id = %d",
        $table->id
    ));

    $identity = mk_current_identity();
    $display  = mk_unique_guest_name($table->id, mk_current_display_name($req));
    mk_seat_player($table->id, $identity, $display, $seat, false);

    return rest_ensure_response([
        'seat'  => $seat,
        'token' => mk_ws_token($code, $seat, $identity),
    ]);
}

function mk_api_kick_player($req) {
    global $wpdb;
    $code = mk_validate_code($req['code']);
    if (is_wp_error($code)) return $code;
    $player_id = (int) ($req->get_param('player_id') ?? 0);
    $host_id   = mk_current_identity();

    // Authorization: row exists only when the caller's identity matches host_id.
    // status='waiting' guard (PM-001): kicking is a lobby-only action. Without it
    // the host could delete a wp_mk_players row mid-game, corrupting the roster
    // that save_scores reads on finish.
    $table = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$wpdb->prefix}mk_tables WHERE code = %s AND host_id = %s AND status = 'waiting'",
        $code, $host_id
    ));
    if (!$table) return mk_err('forbidden', 'Only the host can kick players, and only before the game starts', 403);

    $kicked = $wpdb->get_row($wpdb->prepare(
        "SELECT seat FROM {$wpdb->prefix}mk_players WHERE id = %d AND table_id = %d",
        $player_id, $table->id
    ));
    $wpdb->delete("{$wpdb->prefix}mk_players", ['id' => $player_id, 'table_id' => $table->id]);
    return rest_ensure_response(['kicked' => $player_id, 'seat' => $kicked ? (int) $kicked->seat : null]);
}

function mk_api_start_game($req) {
    global $wpdb;
    $code = mk_validate_code($req['code']);
    if (is_wp_error($code)) return $code;
    $host_id = mk_current_identity();

    // Authorization: row exists only when the caller's identity matches host_id.
    $table = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$wpdb->prefix}mk_tables WHERE code = %s AND host_id = %s AND status = 'waiting'",
        $code, $host_id
    ));
    if (!$table) return mk_err('forbidden', 'Not allowed or game already started', 403);

    $count = (int) $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM {$wpdb->prefix}mk_players WHERE table_id = %d", $table->id
    ));
    if ($count < 2) return mk_err('too_few', 'Need at least 2 players', 409);

    $wpdb->update("{$wpdb->prefix}mk_tables", ['status' => 'playing'], ['id' => $table->id]);

    // Initial game state will be handled by WebSocket server.
    // Host occupies seat 0 — issue their signed game token here.
    return rest_ensure_response([
        'started' => true,
        'players' => $count,
        'token'   => mk_ws_token($code, 0, $host_id),
    ]);
}

function mk_api_rename_player($req) {
    global $wpdb;
    $code = mk_validate_code($req['code']);
    if (is_wp_error($code)) return $code;
    $seat = (int) ($req->get_param('seat') ?? -1);
    if ($seat < 0) return mk_err('invalid_seat', 'Invalid seat', 400);
    $new_name = mk_validate_name($req->get_param('name') ?? '');
    if (is_wp_error($new_name)) return $new_name;

    $table = $wpdb->get_row($wpdb->prepare(
        "SELECT id, host_id FROM {$wpdb->prefix}mk_tables WHERE code = %s AND status = 'waiting'", $code
    ));
    if (!$table) return mk_err('not_found', 'Table not found or already started', 404);

    $player = $wpdb->get_row($wpdb->prepare(
        "SELECT id, identity FROM {$wpdb->prefix}mk_players WHERE table_id = %d AND seat = %d AND user_id IS NULL",
        $table->id, $seat
    ));
    if (!$player) return mk_err('not_found', 'Guest player not found', 404);

    // Authorize: only the host, or the guest who owns this seat, may rename it.
    // The seat owner is matched via the stored identity. NOTE: a guest's identity
    // derives from the spoofable X-MK-Guest header, so guest self-auth is only as
    // strong as that header — acceptable for guests per the Sprint-1 brief; host
    // identity for a registered host (user:<id>) comes from WP auth and is not.
    $caller  = mk_current_identity();
    $is_host = ($caller === $table->host_id);
    $is_self = ($player->identity !== null && $caller === $player->identity);
    if (!$is_host && !$is_self)
        return mk_err('forbidden', 'Only the host or the seat owner can rename', 403);

    $unique = mk_unique_guest_name($table->id, $new_name, $player->id);
    $wpdb->update("{$wpdb->prefix}mk_players", ['guest_name' => $unique], ['id' => $player->id]);

    return rest_ensure_response(['name' => $unique]);
}

function mk_api_leaderboard($req) {
    global $wpdb;
    // Aggregate persisted results per registered player. Guests are never written
    // to wp_mk_scores, so they don't appear here.
    $rows = $wpdb->get_results(
        "SELECT s.user_id,
                u.display_name,
                COUNT(*)                AS games,
                COALESCE(SUM(s.won), 0) AS wins,
                COALESCE(SUM(s.landmarks_built), 0) AS landmarks_built,
                COALESCE(MAX(s.coins_at_end), 0)    AS best_coins
         FROM {$wpdb->prefix}mk_scores s
         LEFT JOIN {$wpdb->users} u ON u.ID = s.user_id
         GROUP BY s.user_id, u.display_name
         ORDER BY wins DESC, games DESC, landmarks_built DESC
         LIMIT 50"
    );
    return rest_ensure_response($rows);
}

// --- helpers ---

/** Consistent WP_Error shape for every failure response. */
function mk_err($code, $msg, $status) {
    return new WP_Error($code, $msg, ['status' => $status]);
}

/** Normalize + validate a table code. Returns the uppercased code or a WP_Error. */
function mk_validate_code($raw) {
    $code = strtoupper(trim((string) $raw));
    if (!preg_match('/^[A-Z0-9\-]{3,12}$/', $code))
        return mk_err('invalid_code', 'Invalid table code', 400);
    return $code;
}

/** Sanitize + length-clamp a display/table name. Returns the name or a WP_Error if empty. */
function mk_validate_name($raw, $max = 32) {
    $name = trim(sanitize_text_field((string) $raw));
    if ($name === '')             return mk_err('invalid_name', 'Name is required', 400);
    if (mb_strlen($name) > $max)  $name = mb_substr($name, 0, $max);
    return $name;
}

/**
 * Simple per-identity throttle backed by a WP transient counter.
 * Returns false once $max actions occur within $window seconds. "Fine for MVP"
 * per the handoff; a blocked caller never resets the window (TTL just expires).
 */
function mk_rate_limit($key, $max, $window) {
    $tkey  = 'mk_rl_' . md5($key);
    $count = (int) get_transient($tkey);
    if ($count >= $max) return false;
    set_transient($tkey, $count + 1, $window);
    return true;
}

/**
 * Best-effort client IP for rate limiting. Trusts X-Real-IP because our nginx
 * sets it from $remote_addr (overwriting any client value); falls back to the
 * last hop of X-Forwarded-For (also appended by nginx), then REMOTE_ADDR.
 * For throttling only — not an authentication control.
 */
function mk_client_ip() {
    $ip = trim((string) ($_SERVER['HTTP_X_REAL_IP'] ?? ''));
    if ($ip === '' && !empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
        $parts = array_map('trim', explode(',', $_SERVER['HTTP_X_FORWARDED_FOR']));
        $ip = end($parts);
    }
    if ($ip === '') $ip = (string) ($_SERVER['REMOTE_ADDR'] ?? '');
    return filter_var($ip, FILTER_VALIDATE_IP) ?: '0.0.0.0';
}

/**
 * Rate-limit key that can't be reset by rotating the spoofable X-MK-Guest header
 * (QA-005): logged-in users key on their stable user id; anonymous callers key on
 * client IP, so a guest minting a fresh guest:uniqid() per call still accumulates.
 */
function mk_rate_limit_key($action) {
    $uid = get_current_user_id();
    return $uid ? "{$action}:user:{$uid}" : "{$action}:ip:" . mk_client_ip();
}

/**
 * Shared HMAC secret, read from the container environment (set in docker-compose).
 * Checks getenv / $_SERVER / $_ENV since SAPIs differ in where they expose env vars.
 */
function mk_ws_secret() {
    $s = getenv('MK_WS_SECRET');
    if ($s === false || $s === '') $s = $_SERVER['MK_WS_SECRET'] ?? '';
    if ($s === '')                 $s = $_ENV['MK_WS_SECRET'] ?? '';
    return $s;
}

/**
 * Issue a short-lived, signed token authorizing one (code, seat, identity) to
 * connect to the game WebSocket. The websocket server recomputes the HMAC over
 * code|seat|identity|exp using the same secret; the token — not the spoofable
 * X-MK-Guest header — is the trust anchor for who owns a seat.
 *
 * Wire format: base64url( "identity|exp|sig" )  (code & seat travel in the WS path).
 */
function mk_ws_token($code, $seat, $identity) {
    $secret = mk_ws_secret();
    if ($secret === '') return '';            // misconfigured; WS will reject anyway
    $exp = time() + 6 * 3600;                  // 6h: covers lobby wait + a full game
    $msg = $code . '|' . $seat . '|' . $identity . '|' . $exp;
    $sig = hash_hmac('sha256', $msg, $secret);
    $plain = $identity . '|' . $exp . '|' . $sig;
    return rtrim(strtr(base64_encode($plain), '+/', '-_'), '=');
}

function mk_current_identity() {
    $uid = get_current_user_id();
    if ($uid) return 'user:' . $uid;
    // Guests send a client-generated uuid via X-MK-Guest header
    $guest_id = sanitize_text_field($_SERVER['HTTP_X_MK_GUEST'] ?? '');
    return 'guest:' . ($guest_id ?: uniqid('g', true));
}

function mk_current_display_name($req) {
    $uid = get_current_user_id();
    if ($uid) {
        $user = get_userdata($uid);
        return $user->display_name;
    }
    return sanitize_text_field($req->get_param('guest_name') ?? 'Guest');
}

function mk_unique_guest_name($table_id, $name, $exclude_player_id = null) {
    global $wpdb;
    $query  = "SELECT COALESCE(u.display_name, p.guest_name) AS n
               FROM {$wpdb->prefix}mk_players p
               LEFT JOIN {$wpdb->users} u ON u.ID = p.user_id
               WHERE p.table_id = %d";
    $params = [$table_id];
    if ($exclude_player_id) { $query .= " AND p.id != %d"; $params[] = $exclude_player_id; }
    $existing = array_map('strtolower', array_filter($wpdb->get_col($wpdb->prepare($query, ...$params))));

    $base      = trim($name);
    $candidate = $base;
    $i         = 1;
    while (in_array(strtolower($candidate), $existing)) {
        $candidate = $base . ' ' . $i++;
    }
    return $candidate;
}

function mk_seat_player($table_id, $identity, $display, $seat, $is_host) {
    global $wpdb;
    $uid = str_starts_with($identity, 'user:') ? (int) substr($identity, 5) : null;
    $wpdb->insert("{$wpdb->prefix}mk_players", [
        'table_id'   => $table_id,
        'user_id'    => $uid,
        'identity'   => $identity,   // who owns this seat (used for rename self-check)
        'guest_name' => $uid ? null : $display,
        'seat'       => $seat,
        'is_host'    => $is_host ? 1 : 0,
    ]);
}
