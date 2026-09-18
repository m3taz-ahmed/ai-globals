[WORKFLOW] 60-atomic-release-deployment
[OBJ] Atomic release deployment (releases/ + current symlink + shared/) — canonical reference for push-to-production on ANY hosting tier: VPS, shared+SSH, FTP-only cPanel. Stack-agnostic; Laravel examples.
[TRIGGER] atomic deploy, zero-downtime deploy, release deployment, shared hosting deploy, capistrano, deployer, نشر بدون توقف, نشر الإصدارات
[RULES]

## 1. The Pattern

Every production app deploys as an immutable **release** — never edit code in place.

```
/var/www/<app>/                    # or ~/apps/<app> on shared hosting
├── current -> releases/<id>       # symlink; web server docroot = current/public
├── releases/
│   ├── 20260918_143022_a1b2c3d/   # <timestamp>_<git-sha>
│   ├── 20260915_091011_e4f5g6h/
│   └── ...                        # keep last 5 (configurable)
├── shared/
│   ├── .env                       # single source of env truth, chmod 640
│   └── storage/                   # uploads, logs, sessions — survives releases
└── .dep/                          # tool metadata + deploy.lock (Deployer)
```

Why it works: the release is built **completely** (deps, assets, caches, migrations) while `current` still points at the old release. The swap is one atomic filesystem operation. Old releases remain for instant rollback.

**Non-negotiable rules:**
1. [PROHIBIT] Never `git pull` / edit files inside the live docroot on production.
2. [REQ] `current` and `releases/` must be on the **same filesystem** — `rename(2)` atomicity does not cross mounts.
3. [REQ] Web server docroot points at `current/public` — never at a release path directly.
4. [REQ] Anything that must survive a release lives in `shared/` and is symlinked into each release.

## 2. The Atomic Swap — correct vs broken

The swap must be a single `rename(2)` syscall:

```bash
# CORRECT — atomic
ln -sfn releases/<id> current.tmp
mv -T current.tmp current

# BROKEN — race window where `current` does not exist
rm current && ln -s releases/<id> current
ln -sfn releases/<id> current   # ln -sf = unlink+symlink internally, same race
```

On a busy site the race window in the broken forms is hit dozens of times per deploy (404/500 spikes). Tools that do this correctly: Deployer (`deploy:symlink`), Capistrano, Envoyer. If writing your own script, use the `mv -T` two-step above.

## 3. Environment Tiers — pick the strategy that fits

| Tier | Environment | SSH | Root | Strategy | Downtime |
|------|-------------|-----|------|----------|----------|
| A | VPS / dedicated (Nginx/Apache + PHP-FPM) | yes | yes | Deployer atomic releases + systemd/supervisor | zero |
| B | Shared hosting with SSH (cPanel, no root) | yes | no | Same layout under `~/`; cron workers; docroot via panel or shim | zero (mostly) |
| C | Shared hosting FTP/File-Manager only | no | no | CI-built artifact + index.php shim + tokenized HTTP runner | near-zero for code; maintenance window for migrations |
| D | Panel Git pull (cPanel Git Version Control etc.) | via panel | no | In-place `git pull` + `artisan down/up` | seconds of maintenance mode — do NOT claim zero-downtime |

[REQ] Detect the tier BEFORE writing any deploy config: `ssh user@host 'id'` → Tier A/B. FTP-only panel → Tier C.

## 4. Tier A — VPS with SSH + sudo (canonical)

### One-time server setup

```bash
sudo useradd -m -s /bin/bash deployer            # dedicated deploy user
sudo mkdir -p /var/www/<app>/{releases,shared}
sudo chown -R deployer:deployer /var/www/<app>
# .env lives in shared/, readable by PHP-FPM user
sudo install -m 640 -o deployer -g www-data /dev/null /var/www/<app>/shared/.env
# Repo access: read-only GitHub deploy key on the server, NOT a personal SSH key
```

Nginx: `root /var/www/<app>/current/public;` — Apache: `DocumentRoot .../current/public` + `Options FollowSymLinks`. Reload web server once at setup; never again per deploy (symlink swap needs no reload).

sudoers — allow ONLY the FPM reload (nothing else):
```
deployer ALL=(root) NOPASSWD: /usr/bin/systemctl reload php8.4-fpm
```

Cron (as deployer — path via `current`, survives swaps):
```
* * * * * cd /var/www/<app>/current && php artisan schedule:run >> /dev/null 2>&1
```

Supervisor/systemd units for Horizon, Reverb, scheduler workers — all reference `current/artisan`, never a release path.

### deploy.php (Deployer recipe — generic template)

```php
<?php
namespace Deployer;

require 'recipe/laravel.php';

set('application', '<app>');
set('repository', 'git@github.com:<org>/<repo>.git');
set('keep_releases', 5);
set('release_name', fn () => date('Ymd_His') . '_' . substr(runLocally('git rev-parse HEAD'), 0, 7));

add('shared_files', ['.env']);
add('shared_dirs', ['storage']);
add('writable_dirs', ['bootstrap/cache', 'storage']);

host('production')
    ->set('hostname', '<host>')
    ->set('remote_user', 'deployer')
    ->set('deploy_path', '/var/www/<app>');

desc('Backup DB before migrations');
task('db:backup', fn () => run('cd {{release_path}} && bash deploy/backup-database.sh'));
before('artisan:migrate', 'db:backup');

desc('Build frontend (skip if built in CI and shipped as artifact)');
task('npm:build', fn () => run('cd {{release_path}} && npm ci --ignore-scripts && npm run build', ['timeout' => 300]));

desc('Reload PHP-FPM to clear opcache');
task('php:fpm-reload', fn () => run('sudo /usr/bin/systemctl reload php8.4-fpm'));

task('deploy', [
    'deploy:prepare',
    'deploy:vendors',
    'artisan:storage:link',
    'artisan:config:cache',
    'artisan:route:cache',
    'artisan:view:cache',
    'npm:build',
    'artisan:migrate',
    'deploy:publish',        // atomic swap happens inside here
]);

after('deploy:publish', 'php:fpm-reload');
after('php:fpm-reload', 'artisan:horizon:terminate');   // graceful worker drain
after('artisan:horizon:terminate', 'artisan:octane:reload'); // if Octane/FrankenPHP
after('artisan:octane:reload', 'healthcheck');
fail('deploy', 'deploy:unlock');
```

### GitHub Actions skeleton

```yaml
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps: [checkout, setup php/node, composer install, npm build, tests, audits, sbom]

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production            # required reviewers gate
    steps:
      - ssh-keyscan -H $DEPLOY_HOST >> ~/.ssh/known_hosts   # pin host key
      - webfactory/ssh-agent with DEPLOY_SSH_KEY secret
      - run: vendor/bin/dep deploy production -v

  verify:
    needs: deploy
    steps: [curl -f $PRODUCTION_URL/up]   # Laravel /up or custom /health

  rollback:
    needs: [deploy, verify]
    if: failure()
    steps: [vendor/bin/dep deploy:rollback production -v]
```

## 5. Tier B — Shared hosting with SSH (no root)

Same `releases/ + current + shared/` layout under `~/apps/<app>` — the pattern does not need root. Adapt:

- **Docroot**: point the (sub)domain document root in cPanel to `~/apps/<app>/current/public`. If the primary domain docroot is locked to `public_html`, either:
  - make `public_html` itself a symlink → `~/apps/<app>/current/public` (works if `FollowSymLinks` allowed; verify host doesn't recreate the dir), or
  - keep real `public_html` with only an `index.php` shim (Tier C pattern below).
- **No FPM reload**: most shared hosts run per-request PHP (CGI/LSAPI) — opcache either doesn't persist or is invalidated by the new realpath. If stale code appears, expose a protected `opcache_reset()` endpoint (see §7 runner) or set `opcache.validate_timestamps=1` via `.user.ini`.
- **No supervisor**: replace with cron —
  ```
  * * * * * cd ~/apps/<app>/current && php artisan schedule:run >> /dev/null 2>&1
  * * * * * cd ~/apps/<app>/current && php artisan queue:work --stop-when-empty --max-time=55 >> /dev/null 2>&1
  ```
  `--stop-when-empty` + `--max-time` makes workers exit after the swap and respawn on new code — the poor-man's `queue:restart`. If `queue:restart` is available via cron flag file, prefer it.
- **No Deployer on host**: run `dep` from CI over SSH (Deployer runs locally/CI, executes remote commands) — works with non-root SSH. Or use the POSIX fallback in §9.
- **Node build OOM on small hosts**: build assets in CI and upload `public/build`, or set `set('build_path')` artifact upload — never `npm run build` on a 512MB shared box.

## 6. Tier C — FTP / File-Manager only (no SSH)

Zero-downtime is limited here — be honest about it. Code swaps are near-atomic via the shim; migrations need a maintenance window.

**Layout:**
```
~/laravel_app/                 # OUTSIDE webroot — full app lives here
├── current -> releases/<id>
├── releases/<id>/
└── shared/.env, shared/storage/
~/public_html/                 # real dir (cPanel-managed)
├── index.php                  # SHIM — loads app via ../laravel_app/current
├── .htaccess
└── build/                     # synced per deploy; hashed filenames coexist
```

**`public_html/index.php` shim** (stable file, deployed once):
```php
<?php
$app = require __DIR__.'/../laravel_app/current/bootstrap/app.php';
$app->handleRequest(Illuminate\Http\Request::capture());
```
(For Laravel ≤10 keep the classic autoload+kernel form; match the app's own `public/index.php` with paths rewritten to `../laravel_app/current/...`.)

**Why near-atomic:** PHP code resolves through `current` (atomic). Assets under `public/build` are content-hashed — upload the new build dir alongside the old; old pages keep working, then remove stale files after the swap.

**If symlinks are blocked entirely** (some hosts disable `symlink()`): fall back to copy mode — deploy into `releases/<id>`, then during a short maintenance window copy `releases/<id>` → a fixed `app_current/` dir. Mark this deploy type as *downtime-expected*; never call it zero-downtime.

**Tokenized HTTP runner** — the only way to run artisan without SSH. Protected route (deploy once, keep secret):
```php
Route::get('/_deploy/{action}', function (string $action, Request $r) {
    abort_unless(hash_equals((string) config('app.deploy_token'), (string) $r->query('token')), 404);
    abort_unless(in_array($action, ['optimize:clear','migrate','storage:link','up','down'], true), 404);
    Artisan::call($action, ['--force' => true]);
    return response('ok: '.$action, 200);
})->middleware('throttle:5,1');
```
Rules: token in `shared/.env` (`DEPLOY_TOKEN`), `hash_equals` compare, whitelist actions only, never log the token, rotate on exposure, never leave one-off scripts in `public/`.

**Migrations without artisan:** ship idempotent `.sql` files (safe to run twice — `CREATE TABLE IF NOT EXISTS`, guards around alters) and apply via panel phpMyAdmin, or use the runner's `migrate` action during maintenance mode.

**`.htaccess` alternative** when docroot can't move and shim isn't wanted:
```apache
RewriteEngine On
RewriteRule ^(.*)$ /../laravel_app/current/public/$1   # only if host allows rewrites above docroot
```
Prefer the shim — docroot escapes via rewrite are blocked on many hosts.

## 7. Deploy Sequence (universal — every tier)

1. **Preflight**: `df -h` free space for a new release + vendor; deploy lock acquired; tests green in CI; backup verified (`backup:monitor` / dump script).
2. **Create release** `releases/<ts>_<sha>/` and place code (git archive/clone or artifact extract).
3. **Link shared**: `.env` → `shared/.env`; `storage` → `shared/storage`. Verify perms (writable by PHP user).
4. **Deps & build**: `composer install --no-dev -o`; `npm ci && npm run build` (or artifact from CI).
5. **Warm caches**: `config:cache route:cache view:cache event:cache` (skip `route:cache` if closures exist — CI must catch this).
6. **Migrate** `php artisan migrate --force` — runs on the NEW release's code BEFORE the swap; safe only because migrations are expand-phase compatible (§8).
7. **Swap** `current` atomically (`mv -T`).
8. **Restart executors**: FPM reload / `opcache_reset`; `queue:restart` or `horizon:terminate`; `octane:reload`; reverb restart. Cron `schedule:run` needs nothing (resolves via `current`).
9. **Health check** `/up` or `/health` → non-200 = auto-rollback path.
10. **Cleanup**: keep N=5 releases (`deploy:cleanup`); unlock; notify.

## 8. Migrations — expand/contract (mandatory)

- **Expand**: nullable columns, new tables, new indexes — deploy with code.
- **Migrate**: code writes to both old and new shape.
- **Contract**: drops/renames — ALWAYS a separate later deploy, after all instances run new code.
- [PROHIBIT] Never ship a destructive migration in the same deploy that removes its usage.
- [REQ] Backup DB immediately before `migrate` on every deploy.
- [REQ] Never auto-`migrate:rollback` in CI — human decision only.
- Multi-instance: migrate BEFORE the swap only works because expand-phase keeps old code functional during the window.

## 9. POSIX fallback script (no Deployer — git-based, Tier A/B)

```bash
#!/usr/bin/env bash
set -euo pipefail
APP=/var/www/<app>; REL="$APP/releases/$(date +%Y%m%d_%H%M%S)_$(git rev-parse --short HEAD)"
LOCK="$APP/.dep/deploy.lock"
mkdir -p "$APP/.dep" "$REL"
[ -f "$LOCK" ] && { echo "deploy locked"; exit 1; }
trap 'rm -f "$LOCK"' EXIT; touch "$LOCK"

git archive HEAD | tar -x -C "$REL"                  # or: git clone --depth 1
ln -sfn "$APP/shared/.env" "$REL/.env"
rm -rf "$REL/storage"; ln -sfn "$APP/shared/storage" "$REL/storage"
cd "$REL"
composer install --no-dev --optimize-autoloader --no-interaction
php artisan config:cache route:cache view:cache
bash deploy/backup-database.sh || true
php artisan migrate --force
ln -sfn "$REL" "$APP/current.tmp"; mv -T "$APP/current.tmp" "$APP/current"   # atomic
php artisan queue:restart || true
sudo systemctl reload php8.4-fpm || true
ls -1dt "$APP"/releases/*/ | tail -n +6 | xargs rm -rf   # keep 5
curl -f --max-time 30 "$APP_URL/up"
```

## 10. Rollback

- **Code rollback** (instant): `dep deploy:rollback` or manually `ln -sfn releases/<prev> current.tmp && mv -T current.tmp current`, then re-run step 8 restarts.
- **DB rollback**: only contract-phase migrations may be rolled back, and only manually. Expand-phase migrations stay — they're harmless to the old release.
- **Auto-rollback in CI**: `if: failure()` job → `dep deploy:rollback` + alert. Never auto-rollback migrations.
- [REQ] After any rollback, write a post-mortem note in the project runbook.

## 11. Failure modes & fixes

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| 404/500 burst at swap moment | `rm+ln` or `ln -sf` swap | `mv -T` two-step (§2) |
| Stale code after deploy | opcache / realpath cache | FPM reload post-swap; `opcache_reset()` endpoint on shared; unique release paths make stale realpath entries unreachable |
| Workers run old code | queue/horizon not restarted | restart AFTER `deploy:publish`, never before |
| Octane/FrankenPHP serves old code | long-running process | `octane:reload` / `frankenphp reload` post-swap |
| "Target class not found" mid-deploy | caches warmed before deps | order: vendors → caches → migrate → swap |
| `route:cache` fails | closure routes | CI must run `route:cache` as a check; remove closures or skip caching |
| Disk full, deploy dies | releases accumulate | `keep_releases=5` + cleanup in flow; `df -h` preflight |
| Two deploys collide | no lock | `deploy:lock`/`.dep/deploy.lock`; `deploy:unlock` on fail |
| `.env` differences per release | env stored per-release | `.env` only in `shared/` — never in git, never per-release |
| `public/storage` 404 after swap | link created inside release pointing at release path | link `storage`→`shared/storage`; `storage:link` resolves via `current` |
| Sessions/login wiped on deploy | sessions stored per-release | sessions live in `shared/storage/framework/sessions` |
| Cron runs wrong version | cron points at release path | cron always uses `current` |
| Assets 404 after swap (Tier C) | `public_html` is real dir, build dir replaced | hashed filenames: upload new `build/` beside old, prune later |
| `mv -T` fails | releases on different mount | keep releases+current on same filesystem |
| Health check fails behind maintenance | health route gated | exempt `/up`,`/health` from `down` middleware |
| Permissions denied on storage | wrong owner on shared | `chown -R <php-user>` shared/storage; 775 dirs 664 files |
| SELinux denies symlinked storage | missing context | `restorecon -Rv /var/www/<app>` or `httpd_sys_rw_content_t` on shared |
| Old release executes forever | opcache `file_cache` / persistent workers | restart all persistent executors; don't enable opcache.file_cache across releases |
| Deploy key leak | personal SSH key on server | read-only repo deploy key; CI `ssh-keyscan -H` pins host |

## 12. Security checklist

- [REQ] Dedicated `deployer` user; sudoers limited to FPM reload only.
- [REQ] Repo access via read-only deploy key; never personal keys on servers.
- [REQ] `DEPLOY_SSH_KEY`/`DEPLOY_HOST` in CI secrets; `known_hosts` pinned via `ssh-keyscan -H`.
- [REQ] GitHub `production` environment with required reviewers.
- [REQ] `.env` chmod 640 in `shared/` — outside docroot, never committed.
- [REQ] Docroot exposes ONLY `current/public` — `.env`, `.git`, `storage` unreachable.
- [REQ] Health endpoint returns `{ok,version}` only — no internals; rate-limit it.
- [REQ] Tier C runner: `hash_equals`, action whitelist, throttle, token in env not code.
- [PROHIBIT] Never print env vars, tokens, or `.env` contents in CI logs or deploy output.

## 13. Stack notes

- **Laravel/PHP**: Deployer `recipe/laravel.php` covers the whole flow — `deploy.php` + `.github/workflows/release.yml` in §4 are the canonical templates to adapt per project.
- **Node/PM2**: same layout; `pm2 reload <app> --update-env` post-swap; `ecosystem.config.js` uses `current` paths.
- **Python/gunicorn**: `systemctl reload` or HUP post-swap; venv per-release or shared via `.venv` in `shared/`.
- **Static sites**: docroot = `current`; swap is the entire deploy.
- **Windows/IIS**: use junctions (`mklink /J`) — same atomic-ish swap via config repoint; `app_offline.htm` for guaranteed drain.
- **Docker/K8s**: this pattern is replaced by image tags + rolling updates — do not mix.

## 14. Adoption checklist

1. Detect tier (§3) → pick strategy.
2. Create `releases/ + shared/ + .dep/` layout; move `.env`+`storage` into `shared/`.
3. Repoint docroot to `current/public` (or shim on Tier C).
4. Wire restarts: FPM/queue/octane/reverb post-swap; cron via `current`.
5. Add deploy lock + keep_releases=5 + df preflight.
6. CI: build/test → deploy → health check → auto-rollback on failure.
7. Document rollback + expand/contract rule in the project runbook.
8. Test: deploy twice, rollback once, verify `/up` green throughout.
