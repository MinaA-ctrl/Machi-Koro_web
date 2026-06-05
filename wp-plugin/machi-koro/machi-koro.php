<?php
/**
 * Plugin Name: Machi Koro
 * Description: Online multiplayer Machi Koro (Harbor Expansion) game.
 * Version: 0.1.0
 */

if (!defined('ABSPATH')) exit;

define('MK_VERSION', '0.1.0');
// Schema version: bump whenever a migration is added to mk_migrate(). Kept
// separate from MK_VERSION so schema changes are independent of plugin releases.
define('MK_DB_VERSION', '2');
define('MK_DIR', plugin_dir_path(__FILE__));
define('MK_URL', plugin_dir_url(__FILE__));

require_once MK_DIR . 'includes/db.php';
require_once MK_DIR . 'includes/api.php';
require_once MK_DIR . 'includes/shortcodes.php';

register_activation_hook(__FILE__, 'mk_install');
// Apply pending migrations on live installs without a reactivation.
add_action('plugins_loaded', 'mk_maybe_migrate');
