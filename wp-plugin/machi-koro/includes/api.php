<?php
if (!defined('ABSPATH')) exit;

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
});

function mk_api_list_tables($req) {
    global $wpdb;
    $search = sanitize_text_field($req->get_param('search') ?? '');
    $like = '%' . $wpdb->esc_like($search) . '%';

    $rows = $wpdb->get_results($wpdb->prepare(
        "SELECT t.id, t.code, t.name, t.is_public, t.status,
                COUNT(p.id) AS player_count
         FROM {$wpdb->prefix}mk_tables t
         LEFT JOIN {$wpdb->prefix}mk_players p ON p.table_id = t.id
         WHERE t.is_public = 1 AND t.status = 'waiting' AND t.name LIKE %s
         GROUP BY t.id
         ORDER BY t.created_at DESC
         LIMIT 50",
        $like
    ));

    return rest_ensure_response($rows);
}

function mk_api_create_table($req) {
    global $wpdb;
    $name    = sanitize_text_field($req->get_param('name') ?? 'Machi Koro Table');
    $public  = (bool) ($req->get_param('is_public') ?? true);
    $host_id = mk_current_identity();

    $code = mk_generate_code();

    $wpdb->insert("{$wpdb->prefix}mk_tables", [
        'code'      => $code,
        'name'      => $name,
        'host_id'   => $host_id,
        'is_public' => $public ? 1 : 0,
    ]);

    $table_id = $wpdb->insert_id;

    // Seat the host as player 0
    $display = mk_unique_guest_name($table_id, mk_current_display_name($req));
    mk_seat_player($table_id, $host_id, $display, 0, true);

    return rest_ensure_response(['code' => $code]);
}

function mk_api_get_table($req) {
    global $wpdb;
    $row = $wpdb->get_row($wpdb->prepare(
        "SELECT t.* FROM {$wpdb->prefix}mk_tables t WHERE t.code = %s",
        strtoupper($req['code'])
    ));
    if (!$row) return new WP_Error('not_found', 'Table not found', ['status' => 404]);

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
    $code = strtoupper($req['code']);
    $table = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$wpdb->prefix}mk_tables WHERE code = %s", $code
    ));

    if (!$table) return new WP_Error('not_found', 'Table not found', ['status' => 404]);
    if ($table->status !== 'waiting') return new WP_Error('started', 'Game already started', ['status' => 409]);

    $count = (int) $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM {$wpdb->prefix}mk_players WHERE table_id = %d", $table->id
    ));
    if ($count >= 5) return new WP_Error('full', 'Table is full', ['status' => 409]);

    $identity = mk_current_identity();
    $display  = mk_unique_guest_name($table->id, mk_current_display_name($req));
    mk_seat_player($table->id, $identity, $display, $count, false);

    return rest_ensure_response(['seat' => $count]);
}

function mk_api_kick_player($req) {
    global $wpdb;
    $code      = strtoupper($req['code']);
    $player_id = (int) ($req->get_param('player_id') ?? 0);
    $host_id   = mk_current_identity();

    $table = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$wpdb->prefix}mk_tables WHERE code = %s AND host_id = %s",
        $code, $host_id
    ));
    if (!$table) return new WP_Error('forbidden', 'Only the host can kick players', ['status' => 403]);

    $kicked = $wpdb->get_row($wpdb->prepare(
        "SELECT seat FROM {$wpdb->prefix}mk_players WHERE id = %d AND table_id = %d",
        $player_id, $table->id
    ));
    $wpdb->delete("{$wpdb->prefix}mk_players", ['id' => $player_id, 'table_id' => $table->id]);
    return rest_ensure_response(['kicked' => $player_id, 'seat' => $kicked ? (int) $kicked->seat : null]);
}

function mk_api_start_game($req) {
    global $wpdb;
    $code    = strtoupper($req['code']);
    $host_id = mk_current_identity();

    $table = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$wpdb->prefix}mk_tables WHERE code = %s AND host_id = %s AND status = 'waiting'",
        $code, $host_id
    ));
    if (!$table) return new WP_Error('forbidden', 'Not allowed or game already started', ['status' => 403]);

    $count = (int) $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM {$wpdb->prefix}mk_players WHERE table_id = %d", $table->id
    ));
    if ($count < 2) return new WP_Error('too_few', 'Need at least 2 players', ['status' => 409]);

    $wpdb->update("{$wpdb->prefix}mk_tables", ['status' => 'playing'], ['id' => $table->id]);

    // Initial game state will be handled by WebSocket server
    return rest_ensure_response(['started' => true, 'players' => $count]);
}

function mk_api_rename_player($req) {
    global $wpdb;
    $code     = strtoupper($req['code']);
    $seat     = (int) ($req->get_param('seat') ?? -1);
    $new_name = sanitize_text_field($req->get_param('name') ?? '');

    if (!$new_name || $seat < 0)
        return new WP_Error('invalid', 'Invalid parameters', ['status' => 400]);

    $table = $wpdb->get_row($wpdb->prepare(
        "SELECT id FROM {$wpdb->prefix}mk_tables WHERE code = %s AND status = 'waiting'", $code
    ));
    if (!$table) return new WP_Error('not_found', 'Table not found or already started', ['status' => 404]);

    $player = $wpdb->get_row($wpdb->prepare(
        "SELECT id FROM {$wpdb->prefix}mk_players WHERE table_id = %d AND seat = %d AND user_id IS NULL",
        $table->id, $seat
    ));
    if (!$player) return new WP_Error('not_found', 'Guest player not found', ['status' => 404]);

    $unique = mk_unique_guest_name($table->id, $new_name, $player->id);
    $wpdb->update("{$wpdb->prefix}mk_players", ['guest_name' => $unique], ['id' => $player->id]);

    return rest_ensure_response(['name' => $unique]);
}

// --- helpers ---

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
        'guest_name' => $uid ? null : $display,
        'seat'       => $seat,
        'is_host'    => $is_host ? 1 : 0,
    ]);
}
