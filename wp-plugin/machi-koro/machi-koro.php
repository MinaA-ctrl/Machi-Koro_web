<?php
/**
 * Plugin Name: Machi Koro
 * Description: Online multiplayer Machi Koro — WordPress page-host for the FastAPI + Postgres backend (Stage 2).
 * Version: 0.2.0
 */

if (!defined('ABSPATH')) exit;

define('MK_VERSION', '0.2.0');
define('MK_DIR', plugin_dir_path(__FILE__));
define('MK_URL', plugin_dir_url(__FILE__));

// Page-host only (Stage 2, S2.7): WordPress serves the shortcode pages + assets;
// the JS client talks to the new FastAPI + Postgres backend behind nginx's /api.
// The old WP REST surface (includes/api.php) and the MySQL schema bootstrap
// (includes/db.php, mk_install/mk_migrate + the activation/upgrade hooks) were
// retired here — all game logic, REST, persistence, and auth now live in the
// backend. Orphaned wp_mk_* MySQL tables are harmless and left in place.
require_once MK_DIR . 'includes/shortcodes.php';
