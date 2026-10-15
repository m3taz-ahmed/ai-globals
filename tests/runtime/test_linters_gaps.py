"""Gap-coverage tests: contract_emitter, db_migration_safety,
laravel_policy_linter, ui_a11y_checker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from runtime.db_migration_safety import MigrationSafetyChecker
from runtime.laravel_policy_linter import LaravelPolicyLinter
from runtime.ui_a11y_checker import A11yChecker


class TestMigrationSafety:
    C = MigrationSafetyChecker

    def _find(self, content, rule):
        return [f for f in self.C().check_content(content, "mig_table.php")
                if f.rule_id == rule]

    def test_non_migration_skipped(self):
        assert self.C().check_content("plain text", "x.php") == []

    def test_drop_column(self):
        assert self._find("Schema::table('t', fn($t) => $t->dropColumn('c'));", "MG001")

    def test_drop_table(self):
        assert self._find("Schema::drop('users');", "MG001")
        assert self._find("$t->dropIfExists();", "MG001")

    def test_missing_down(self):
        f = self._find("public function up() {}\nclass M extends Migration", "MG002")
        assert f and "irreversible" in f[0].message

    def test_has_down_ok(self):
        assert self._find(
            "public function up() {}\npublic function down() {}", "MG002") == []

    def test_non_concurrent_index(self):
        assert self._find("$t->index('col');", "MG003")
        assert self._find("$t->unique('col');", "MG003")
        assert self._find("$t->foreign('col');", "MG003")
        # concurrent usage is fine
        assert self._find("$t->index('col') CONCURRENTLY;", "MG003") == []

    def test_model_all(self):
        assert self._find("User::all();", "MG004")

    def test_raw_update(self):
        assert self._find("DB::update('UPDATE users SET x = 1');", "MG005")
        assert self._find("DB::statement(\"UPDATE t SET a=1\");", "MG005")

    def test_rename_column(self):
        assert self._find("$t->renameColumn('a','b');", "MG006")

    def test_change_column(self):
        assert self._find("$t->string('c')->change();", "MG008")

    def test_db_raw(self):
        assert self._find("DB::raw('x');", "MG009")

    def test_check_file_missing(self, tmp_path):
        assert self.C().check_file(tmp_path / "nope.php") == []

    def test_check_file_oserror(self, tmp_path):
        p = tmp_path / "m_table.php"
        p.write_text("Schema::drop('t');")
        with patch.object(Path, "read_text", side_effect=OSError):
            assert self.C().check_file(p) == []

    def test_check_files(self, tmp_path):
        p = tmp_path / "m_table.php"
        p.write_text("Schema::drop('t');\npublic function up() {}")
        f = self.C().check_files([p])
        assert {x.rule_id for x in f} >= {"MG001", "MG002"}

    def test_summary(self):
        f = self.C().check_content("Schema::drop('t');\nModel::all();", "t_table.php")
        s = self.C().summary(f)
        assert s["total"] == 2
        assert s["by_severity"]["critical"] == 1
        assert s["by_rule"]["MG001"] == 1

    def test_finding_to_dict(self):
        f = self._find("$t->dropColumn('c');", "MG001")[0]
        assert f.to_dict()["severity"] == "critical"


class TestLaravelLinter:
    L = LaravelPolicyLinter

    def _find(self, content, rule, fp="f.php"):
        return [f for f in self.L().lint_content(content, fp) if f.rule_id == rule]

    def test_non_php_skipped(self):
        assert self.L().lint_content("plain", "x.txt") == []

    def test_guarded_empty(self):
        assert self._find("protected $guarded = [];", "LP001")

    def test_raw_sql_interp(self):
        assert self._find("DB::select(\"SELECT * FROM u WHERE id = $id\");", "LP002")

    def test_controller_request(self):
        assert self._find("public function store(Request $request) {}", "LP003")

    def test_bypass_gate(self):
        assert self._find("->withoutAuthorization()", "LP004")
        assert self._find("Gate::any('*')", "LP004")

    def test_auth_check_truthy(self):
        code = "if (Auth::check()) { return true; }"
        assert self._find(code, "LP007")

    def test_filament_no_policy(self):
        code = "<?php class UserResource extends Resource {}"
        assert self._find(code, "LP006")
        code2 = "<?php class UserResource extends Resource { protected static $policy = X::class; }"
        assert self._find(code2, "LP006") == []

    def test_model_no_fillable(self):
        code = "<?php class User extends Model {}"
        assert self._find(code, "LP008")
        code2 = "<?php class User extends Model { protected $fillable = ['a']; }"
        assert self._find(code2, "LP008") == []

    def test_policy_missing_methods(self):
        code = "<?php class UserPolicy extends Policy { public function view() {} }"
        f = self._find(code, "LP005", "UserPolicy.php")
        assert f and "delete" in f[0].message

    def test_lint_file_and_files(self, tmp_path):
        p = tmp_path / "m.php"
        p.write_text("<?php protected $guarded = [];")
        assert self.L().lint_file(p)
        assert self.L().lint_file(tmp_path / "nope.php") == []
        assert len(self.L().lint_files([p])) >= 1

    def test_lint_file_oserror(self, tmp_path):
        p = tmp_path / "m.php"
        p.write_text("x")
        with patch.object(Path, "read_text", side_effect=OSError):
            assert self.L().lint_file(p) == []

    def test_summary(self):
        f = self.L().lint_content("<?php $guarded = [];", "x.php")
        s = self.L().summary(f)
        assert s["total"] == 1 and s["by_severity"]["error"] == 1


class TestA11yChecker:
    C = A11yChecker

    def _find(self, content, rule, fp="x.html"):
        return [f for f in self.C().check_content(content, fp) if f.rule_id == rule]

    def test_non_template_skipped(self):
        assert self.C().check_content("plain text", "x.txt") == []

    def test_img_no_alt(self):
        assert self._find('<div><img src="x.png"></div>', "A11y-001")
        assert self._find('<div><img src="x.png" alt="y"></div>', "A11y-001") == []

    def test_button_no_label(self):
        assert self._find('<div><button class="x"></button></div>', "A11y-002")
        assert self._find('<div><button aria-label="ok"></button></div>', "A11y-002") == []
        assert self._find('<div><button>Save</button></div>', "A11y-002") == []

    def test_link_no_text(self):
        assert self._find('<div><a href="/x"></a></div>', "A11y-002")

    def test_input_no_label(self):
        assert self._find('<div><input type="text"></div>', "A11y-003")
        ok = '<div><label for="e">E</label><input type="text"></div>'
        assert self._find(ok, "A11y-003") == []
        ok2 = '<div><input type="text" aria-label="e"></div>'
        assert self._find(ok2, "A11y-003") == []

    def test_animation_no_reduce(self):
        assert self._find('<div class="animate-spin"></div>', "A11y-005")
        ok = '<div class="animate-spin motion-reduce:animate-none"></div>'
        assert self._find(ok, "A11y-005") == []

    def test_inline_color(self):
        assert self._find('<div style="color: red"></div>', "A11y-006")

    def test_onclick_no_keydown(self):
        assert self._find('<div onclick="go()"></div>', "A11y-009")
        ok = '<div onclick="go()" onkeydown="k()"></div>'
        assert self._find(ok, "A11y-009") == []

    def test_tabindex_positive(self):
        assert self._find('<div tabindex="5"></div>', "A11y-010")
        assert self._find('<div tabindex="0"></div>', "A11y-010") == []

    def test_arabic_no_rtl(self):
        code = '<html lang="en"><body>مرحبا</body></html>'
        assert self._find(code, "A11y-007")
        code2 = '<html dir="rtl" lang="ar"><body>مرحبا</body></html>'
        assert self._find(code2, "A11y-007") == []

    def test_table_no_caption(self):
        assert self._find('<div><table class="x"><tr><td>1</td></tr></table></div>', "A11y-008")
        ok = '<div><table><caption>T</caption></table></div>'
        assert self._find(ok, "A11y-008") == []

    def test_check_file_and_files(self, tmp_path):
        p = tmp_path / "x.html"
        p.write_text('<img src="a.png">')
        assert self.C().check_file(p)
        assert self.C().check_file(tmp_path / "nope.html") == []
        assert self.C().check_files([p])

    def test_check_file_oserror(self, tmp_path):
        p = tmp_path / "x.html"
        p.write_text("<div></div>")
        with patch.object(Path, "read_text", side_effect=OSError):
            assert self.C().check_file(p) == []

    def test_summary(self):
        f = self.C().check_content('<div><img src="a.png"></div>', "x.html")
        s = self.C().summary(f)
        assert s["total"] >= 1 and s["by_severity"]["error"] >= 1
