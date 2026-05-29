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
        guest_name VARCHAR(64) DEFAULT NULL,
        seat INT NOT NULL,
        is_host TINYINT(1) DEFAULT 0,
        joined_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) $charset;");

    dbDelta("CREATE TABLE IF NOT EXISTS {$wpdb->prefix}mk_game_states (
        id INT AUTO_INCREMENT PRIMARY KEY,
        table_id INT NOT NULL,
        state LONGTEXT NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) $charset;");

    dbDelta("CREATE TABLE IF NOT EXISTS {$wpdb->prefix}mk_scores (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        table_id INT NOT NULL,
        landmarks_built INT DEFAULT 0,
        coins_at_end INT DEFAULT 0,
        won TINYINT(1) DEFAULT 0,
        played_at DATETIME DEFAULT CURRENT_TIMESTAMP
    ) $charset;");
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
