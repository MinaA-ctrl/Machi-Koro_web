<?php
if (!defined('ABSPATH')) exit;

function mk_install() {
    global $wpdb;
    $charset = $wpdb->get_charset_collate();
    require_once ABSPATH . 'wp-admin/includes/upgrade.php';

    dbDelta("CREATE TABLE IF NOT EXISTS {$wpdb->prefix}mk_tables (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(12) NOT NULL UNIQUE,
        name VARCHAR(80) NOT NULL,
        game_version VARCHAR(16) NOT NULL DEFAULT 'harbour',
        sharp TINYINT(1) NOT NULL DEFAULT 0,
        host_id VARCHAR(64) NOT NULL,
        password_hash VARCHAR(255) DEFAULT NULL,
        is_public TINYINT(1) DEFAULT 1,
        status ENUM('waiting','playing','finished') DEFAULT 'waiting',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) $charset;");

    dbDelta("CREATE TABLE IF NOT EXISTS {$wpdb->prefix}mk_players (
        id INT AUTO_INCREMENT PRIMARY KEY,
        table_id INT NOT NULL,
        user_id INT DEFAULT NULL,
        identity VARCHAR(64) DEFAULT NULL,
        guest_name VARCHAR(64) DEFAULT NULL,
        seat INT NOT NULL,
        is_host TINYINT(1) DEFAULT 0,
        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) $charset;");

    dbDelta("CREATE TABLE IF NOT EXISTS {$wpdb->prefix}mk_game_states (
        id INT AUTO_INCREMENT PRIMARY KEY,
        table_id INT NOT NULL,
        state LONGTEXT NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY table_id (table_id)
    ) $charset;");

    dbDelta("CREATE TABLE IF NOT EXISTS {$wpdb->prefix}mk_scores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        table_id INT NOT NULL,
        game_seq INT NOT NULL DEFAULT 0,
        landmarks_built INT DEFAULT 0,
        coins_at_end INT DEFAULT 0,
        won TINYINT(1) DEFAULT 0,
        played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uniq_score (table_id, game_seq, user_id)
    ) $charset;");

    // Run explicit migrations after the dbDelta bootstrap so a reactivation on
    // an existing install also picks up column changes dbDelta can't do.
    mk_migrate();
}

/**
 * Explicit, idempotent schema migrations for existing installs.
 *
 * Migration discipline (retro action #4): dbDelta is unreliable for adding
 * columns / changing indexes on tables that already exist — it silently no-ops.
 * So column/index changes go here as guarded ALTERs that check
 * information_schema first, and we verify with SHOW COLUMNS / SHOW INDEX.
 */
function mk_migrate() {
    global $wpdb;
    $tables = "{$wpdb->prefix}mk_tables";

    // B4: game_version on tables (Basic / Harbour version selection).
    $has_version = $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'game_version'",
        DB_NAME, $tables
    ));
    if (!$has_version) {
        // VARCHAR(16) NOT NULL DEFAULT 'harbour' — existing rows backfill to the
        // current live version, preserving their behavior.
        $wpdb->query("ALTER TABLE {$tables}
            ADD COLUMN game_version VARCHAR(16) NOT NULL DEFAULT 'harbour' AFTER name");
    }

    // D-BE: sharp add-on flag (Millionaire's Row layered on the base version).
    // Same guarded-ALTER pattern as game_version above. DEFAULT 0 backfills
    // existing tables to "no Sharp", preserving their behavior.
    $has_sharp = $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM information_schema.COLUMNS
         WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'sharp'",
        DB_NAME, $tables
    ));
    if (!$has_sharp) {
        $wpdb->query("ALTER TABLE {$tables}
            ADD COLUMN sharp TINYINT(1) NOT NULL DEFAULT 0 AFTER game_version");
    }
}

/**
 * Run pending migrations on normal page loads (not just plugin activation), so a
 * deployed update reaches live installs without a manual deactivate/reactivate.
 * Gated on a stored schema version so it's a cheap option read on the hot path.
 */
function mk_maybe_migrate() {
    if (get_option('mk_db_version') !== MK_DB_VERSION) {
        mk_migrate();
        update_option('mk_db_version', MK_DB_VERSION);
    }
}

function mk_generate_code() {
    global $wpdb;
    do {
        $code = 'MK-' . strtoupper(substr(md5(uniqid()), 0, 6));
        $exists = $wpdb->get_var($wpdb->prepare(
            "SELECT id FROM {$wpdb->prefix}mk_tables WHERE code = %s", $code
        ));
    } while ($exists);
    return $code;
}
