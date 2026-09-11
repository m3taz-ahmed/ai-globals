"""Tests for Laravel/Filament/UI governance modules (v5.14)."""

from __future__ import annotations

from runtime.blade_template_linter import BladeTemplateLinter
from runtime.db_migration_safety import MigrationSafetyChecker
from runtime.filament_access_auditor import FilamentAccessAuditor
from runtime.laravel_policy_linter import LaravelPolicyLinter
from runtime.ui_a11y_checker import A11yChecker

# -- LaravelPolicyLinter --


class TestLaravelPolicyLinter:
    def test_guarded_empty_detected(self) -> None:
        linter = LaravelPolicyLinter()
        findings = linter.lint_content(
            "<?php\nclass User extends Model {\n    protected $guarded = [];\n}\n",
            "User.php",
        )
        assert any(f.rule_id == "LP001" for f in findings)

    def test_raw_sql_detected(self) -> None:
        linter = LaravelPolicyLinter()
        findings = linter.lint_content(
            "<?php\nDB::select(\"SELECT * FROM users WHERE id = $id\");\n",
            "UserController.php",
        )
        assert any(f.rule_id == "LP002" for f in findings)

    def test_missing_fillable_on_model(self) -> None:
        linter = LaravelPolicyLinter()
        findings = linter.lint_content(
            "<?php\nclass Post extends Model {\n    // no fillable\n}\n",
            "Post.php",
        )
        assert any(f.rule_id == "LP008" for f in findings)

    def test_no_findings_on_clean_code(self) -> None:
        linter = LaravelPolicyLinter()
        findings = linter.lint_content(
            "<?php\nclass User extends Model {\n"
            "    protected $fillable = ['name', 'email'];\n"
            "}\n",
            "User.php",
        )
        assert len(findings) == 0

    def test_summary(self) -> None:
        linter = LaravelPolicyLinter()
        findings = linter.lint_content(
            "<?php\nclass User extends Model {\n    protected $guarded = [];\n}\n",
            "User.php",
        )
        summary = linter.summary(findings)
        assert summary["total"] > 0
        assert "LP001" in summary["by_rule"]


# -- FilamentAccessAuditor --


class TestFilamentAccessAuditor:
    def test_panel_without_auth(self) -> None:
        auditor = FilamentAccessAuditor()
        findings = auditor.audit_content(
            "<?php\nclass AdminPanelProvider extends PanelProvider {\n"
            "    public function panel(Panel $panel): Panel {\n"
            "        return $panel->path('admin');\n    }\n}\n",
            "AdminPanelProvider.php",
        )
        assert any(f.rule_id == "FA001" for f in findings)

    def test_resource_without_policy(self) -> None:
        auditor = FilamentAccessAuditor()
        findings = auditor.audit_content(
            "<?php\nclass UserResource extends Resource {\n"
            "    protected static ?string $model = User::class;\n}\n",
            "UserResource.php",
        )
        assert any(f.rule_id == "FA002" for f in findings)

    def test_can_wildcard_detected(self) -> None:
        auditor = FilamentAccessAuditor()
        findings = auditor.audit_content(
            "<?php\n$action->can('*');\n",
            "UserResource.php",
        )
        assert any(f.rule_id == "FA003" for f in findings)

    def test_summary(self) -> None:
        auditor = FilamentAccessAuditor()
        findings = auditor.audit_content(
            "<?php\nclass UserResource extends Resource {\n}\n",
            "UserResource.php",
        )
        summary = auditor.summary(findings)
        assert summary["total"] > 0


# -- MigrationSafetyChecker --


class TestMigrationSafetyChecker:
    def test_drop_column_detected(self) -> None:
        checker = MigrationSafetyChecker()
        findings = checker.check_content(
            "<?php\nclass DropColumnFromUsers extends Migration {\n"
            "    public function up() {\n"
            "        Schema::table('users', fn($t) => $t->dropColumn('old'));\n"
            "    }\n}\n",
            "2026_01_01_drop_column.php",
        )
        assert any(f.rule_id == "MG001" for f in findings)

    def test_missing_down_detected(self) -> None:
        checker = MigrationSafetyChecker()
        findings = checker.check_content(
            "<?php\nclass CreateUsersTable extends Migration {\n"
            "    public function up() {\n        Schema::create('users', fn($t) => $t->id());\n    }\n}\n",
            "2026_01_01_create_users.php",
        )
        assert any(f.rule_id == "MG002" for f in findings)

    def test_model_all_detected(self) -> None:
        checker = MigrationSafetyChecker()
        findings = checker.check_content(
            "<?php\nclass BackfillUsers extends Migration {\n"
            "    public function up() {\n"
            "        foreach (User::all() as $user) { $user->update(['x' => 1]); }\n"
            "    }\n    public function down() {}\n}\n",
            "2026_01_01_backfill.php",
        )
        assert any(f.rule_id == "MG004" for f in findings)

    def test_rename_column_detected(self) -> None:
        checker = MigrationSafetyChecker()
        findings = checker.check_content(
            "<?php\nclass RenameColumn extends Migration {\n"
            "    public function up() {\n"
            "        Schema::table('users', fn($t) => $t->renameColumn('name', 'full_name'));\n"
            "    }\n    public function down() {}\n}\n",
            "2026_01_01_rename.php",
        )
        assert any(f.rule_id == "MG006" for f in findings)


# -- A11yChecker --


class TestA11yChecker:
    def test_img_without_alt(self) -> None:
        checker = A11yChecker()
        findings = checker.check_content(
            '<html><body><img src="photo.jpg"></body></html>',
            "test.blade.php",
        )
        assert any(f.rule_id == "A11y-001" for f in findings)

    def test_button_without_text(self) -> None:
        checker = A11yChecker()
        findings = checker.check_content(
            '<html><body><button class="btn"></button></body></html>',
            "test.blade.php",
        )
        assert any(f.rule_id == "A11y-002" for f in findings)

    def test_arabic_without_rtl(self) -> None:
        checker = A11yChecker()
        findings = checker.check_content(
            '<html lang="ar"><body>مرحبا</body></html>',
            "test.blade.php",
        )
        assert any(f.rule_id == "A11y-007" for f in findings)

    def test_tabindex_positive(self) -> None:
        checker = A11yChecker()
        findings = checker.check_content(
            '<html><body><a href="#" tabindex="5">link</a></body></html>',
            "test.blade.php",
        )
        assert any(f.rule_id == "A11y-010" for f in findings)

    def test_clean_html_no_findings(self) -> None:
        checker = A11yChecker()
        findings = checker.check_content(
            '<html><body><img src="x.jpg" alt="photo"><button>Click</button></body></html>',
            "test.blade.php",
        )
        assert len(findings) == 0


# -- BladeTemplateLinter --


class TestBladeTemplateLinter:
    def test_raw_output_detected(self) -> None:
        linter = BladeTemplateLinter()
        findings = linter.lint_content(
            "{!! $user->bio !!}\n",
            "test.blade.php",
        )
        assert any(f.rule_id == "BL001" for f in findings)

    def test_form_without_csrf(self) -> None:
        linter = BladeTemplateLinter()
        findings = linter.lint_content(
            "<form method=\"POST\" action=\"/users\">\n<input name=\"name\">\n</form>\n",
            "test.blade.php",
        )
        assert any(f.rule_id == "BL002" for f in findings)

    def test_hardcoded_url(self) -> None:
        linter = BladeTemplateLinter()
        findings = linter.lint_content(
            '<a href="/admin/users">Users</a>\n',
            "test.blade.php",
        )
        assert any(f.rule_id == "BL003" for f in findings)

    def test_summary(self) -> None:
        linter = BladeTemplateLinter()
        findings = linter.lint_content("{!! $html !!}\n", "test.blade.php")
        summary = linter.summary(findings)
        assert summary["total"] > 0
        assert "BL001" in summary["by_rule"]
