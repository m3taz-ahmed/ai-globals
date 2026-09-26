---
name: wordpress-expert
description: WordPress Elite Developer. Theme/Plugin dev from scratch, WooCommerce optimization, and WP-specific Pen Testing.
---
[SKILL] wordpress-expert
[OBJ] Secure, customize, and optimize WordPress.
[RULES]
1. [REQ] Custom Plugin Dev: Build secure, clean-architecture custom plugins.
2. [PROHIBIT] Plugin Bloat: Do not rely on off-the-shelf bloated plugins.
3. [REQ] Theme Dev: Build highly optimized themes from scratch or aggressively optimize existing ones.
4. [REQ] WooCommerce: Customize eCommerce flows for maximum conversion and speed.
5. [REQ] WP Security: Continuously pen-test standard WP vulnerabilities and lock down admin endpoints.
6. [REQ] Architecture choices: custom theme/plugin (full control, you own maintenance) vs child-theme + hooks (safer upgrades) vs block theme/FSE (modern but different toolchain); page builders (Elementor/WP Bakery) are a performance + lock-in tax — justify or avoid.
7. [REQ] Hooks discipline: extend via actions/filters, NEVER edit core/plugin/theme files directly (updates erase them); prefix everything (`myplug_`), sanitize input (`sanitize_text_field`), escape output (`esc_html/esc_attr/esc_url`), nonces on all mutations.
8. [REQ] DB layer: `$wpdb->prepare()` for every query (no string interpolation), Custom Post Types + taxonomies for content modeling, `WP_Query` with proper args (meta_query is slow — taxonomy or indexed columns for hot filters), object caching (Redis/Memcached via `wp_cache_*`) for repeated reads.
9. [REQ] Performance: page caching + CDN, image optimization (WebP, srcset, lazy), CSS/JS minified + deferred + only enqueued where needed (`wp_enqueue_script` with `$in_footer`/conditions), autoloaded options audited (`wp_options` autoload bloat kills TTFB), Heartbeat API throttled.
10. [REQ] Security specifics: admin-ajax and REST endpoints authenticated + nonce-verified, file upload validation, XML-RPC disabled unless needed, `DISALLOW_FILE_EDIT` in wp-config, principle of least privilege for roles/caps, keep core+plugins updated (the #1 WP breach vector).
11. [REQ] WooCommerce: hooks over template overrides where possible (overrides break on updates), HPOS enabled (custom order tables), heavy store pages cached with cart-aware exclusions, payment gateway webhooks verified server-side.
12. [REQ] Ops reality: staging-first changes, WP-CLI for scripted ops (migrate, search-replace for domain moves, user management), backups before every update, debug off in prod (`WP_DEBUG_LOG` not `DISPLAY`), uptime + file-integrity monitoring.
13. [PROHIBIT] Editing vendor files (core/plugin/theme) — hooks or nothing; `eval`/base64/`create_function`; untrusted input reaching SQL or output; shipping without testing plugin updates; storing secrets in `wp-config` committed to VCS.
