# Phase 4: Deployment & Release

## 1. PRE-DEPLOYMENT CHECKLIST
Before any deployment to staging or production, verify:
- [ ] All tests pass (`php artisan test`, `npm test`).
- [ ] Static analysis passes (`phpstan`, `eslint`).
- [ ] Database migrations are reviewed and tested on a staging copy.
- [ ] Environment variables are configured for the target environment.
- [ ] Cache is cleared and rebuilt: `php artisan config:cache`, `php artisan route:cache`, `php artisan view:cache`.
- [ ] Assets are built: `npm run build`.
- [ ] `CHANGELOG.md` is updated with the release notes.
- [ ] Version tag is prepared (semantic versioning).

## 2. DEPLOYMENT PROCEDURE
1. **Maintenance Mode:** Enable `php artisan down --secret="bypass-token"` for zero-downtime access by admins.
2. **Pull Changes:** `git pull origin main` on the production server.
3. **Dependencies:** `composer install --no-dev --optimize-autoloader`, `npm ci --production`.
4. **Migrations:** `php artisan migrate --force`.
5. **Cache Rebuild:** Run all cache commands from the checklist.
6. **Queue Restart:** `php artisan queue:restart` to pick up new code.
7. **Go Live:** `php artisan up`.

## 3. ROLLBACK PROCEDURE
If deployment fails:
1. **Immediate:** `php artisan down`, revert to previous git tag: `git checkout v[previous]`.
2. **Database:** If migrations are the issue, `php artisan migrate:rollback --step=N`. Only if the rollback migration was properly written.
3. **Dependencies:** `composer install --no-dev --optimize-autoloader` on the reverted code.
4. **Restore:** `php artisan up` and verify functionality.
5. **Document:** Record the failure in `MEMORY.md` with a post-mortem.

## 4. HEALTH CHECK VERIFICATION
After deployment, verify:
- [ ] Application responds with HTTP 200 on the health endpoint (`/health` or `/api/ping`).
- [ ] Critical user flows work (login, core feature, payment if applicable).
- [ ] Error monitoring (Sentry, Bugsnag) shows no spike in new errors.
- [ ] Queue workers are processing jobs (`php artisan queue:monitor`).
- [ ] Scheduled tasks are registered (`php artisan schedule:list`).

## 5. ZERO-DOWNTIME DEPLOYMENTS (ADVANCED)
- For high-traffic applications, use Envoyer, Deployer, or similar tools for atomic symlink deployments.
- Implement database migrations that are backward-compatible (no column drops or renames without a multi-step migration).
- Use feature flags to decouple deployment from feature release.
