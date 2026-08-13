"""Tests for runtime/ast_validator.py — AST-based code validation."""

from __future__ import annotations

from pathlib import Path

from runtime.ast_validator import CodeValidator, PythonASTValidator, ValidationResult


class TestPythonASTValidator:
    """Tests for PythonASTValidator."""

    def test_parse_valid_code(self) -> None:
        v = PythonASTValidator()
        result = v.parse("x = 1\nprint(x)\n")
        assert result.valid is True
        assert len(result.errors) == 0

    def test_parse_syntax_error(self) -> None:
        v = PythonASTValidator()
        result = v.parse("def foo(:\n    pass\n")
        assert result.valid is False
        assert len(result.errors) == 1
        assert "SyntaxError" in result.errors[0]

    def test_extract_imports(self) -> None:
        v = PythonASTValidator()
        code = "import os\nfrom pathlib import Path\nfrom collections import OrderedDict\n"
        result = v.parse(code)
        assert "os" in result.imports
        assert "pathlib.Path" in result.imports
        assert "collections.OrderedDict" in result.imports

    def test_extract_symbols(self) -> None:
        v = PythonASTValidator()
        code = "def foo():\n    pass\nclass Bar:\n    pass\n"
        result = v.parse(code)
        assert "foo" in result.symbols
        assert "Bar" in result.symbols

    def test_check_imports_builtin(self) -> None:
        v = PythonASTValidator()
        result = v.check_imports("import os\nimport sys\n")
        assert result.valid is True
        assert all("may not be resolvable" not in w for w in result.warnings)

    def test_check_imports_unknown_module(self) -> None:
        v = PythonASTValidator()
        result = v.check_imports("import nonexistent_pkg_xyz\n")
        assert "nonexistent_pkg_xyz" in result.imports
        assert any("nonexistent_pkg_xyz" in w for w in result.warnings)

    def test_check_imports_with_existing(self) -> None:
        v = PythonASTValidator()
        result = v.check_imports("import myproject\n", existing_imports={"myproject"})
        assert all("myproject" not in w for w in result.warnings)

    def test_check_undefined_names_clean(self) -> None:
        v = PythonASTValidator()
        code = "x = 1\nprint(x)\n"
        result = v.check_undefined_names(code)
        assert all("undefined" not in w for w in result.warnings)

    def test_check_undefined_names_detects(self) -> None:
        v = PythonASTValidator()
        code = "print(undefined_var)\n"
        result = v.check_undefined_names(code)
        assert any("undefined_var" in w for w in result.warnings)

    def test_check_undefined_names_ignores_builtins(self) -> None:
        v = PythonASTValidator()
        code = "print(len([1, 2]))\n"
        result = v.check_undefined_names(code)
        assert all("len" not in w for w in result.warnings)


class TestCodeValidator:
    """Tests for CodeValidator dispatch."""

    def test_validate_pre_edit_valid(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "test.py"
        result = v.validate_pre_edit(f, "x = 1\n")
        assert result.valid is True

    def test_validate_pre_edit_syntax_error(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "test.py"
        result = v.validate_pre_edit(f, "def (:\n")
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_post_edit_empty_file(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "test.py"
        result = v.validate_post_edit(f, "")
        assert result.valid is False
        assert "empty" in result.errors[0].lower()

    def test_validate_post_edit_valid(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "test.py"
        result = v.validate_post_edit(f, "import os\nprint(os.getcwd())\n")
        assert result.valid is True

    def test_validate_diff_clean(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "test.py"
        old = "import os\nprint(os.getcwd())\n"
        new = "import os\nimport sys\nprint(os.getcwd(), sys.version)\n"
        result = v.validate_diff(f, old, new)
        assert result.valid is True

    def test_validate_diff_syntax_error_in_new(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "test.py"
        old = "x = 1\n"
        new = "def (:\n"
        result = v.validate_diff(f, old, new)
        assert result.valid is False

    def test_validate_diff_removed_imports_warning(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "test.py"
        old = "import os\nimport sys\nprint(os.getcwd())\n"
        new = "import os\nprint(os.getcwd())\n"
        result = v.validate_diff(f, old, new)
        assert result.valid is True
        assert any("sys" in w for w in result.warnings)

    def test_unsupported_language(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "test.js"
        result = v.validate_pre_edit(f, "console.log('hello')\n")
        assert result.valid is True
        assert any("No AST validator" in w for w in result.warnings)

    def test_extract_imports_from_file(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "test.py"
        f.write_text("import os\nfrom pathlib import Path\n", encoding="utf-8")
        imports = v.extract_imports(f)
        assert "os" in imports
        assert "pathlib" in imports

    def test_extract_imports_nonexistent_file(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "nonexistent.py"
        imports = v.extract_imports(f)
        assert imports == set()

    def test_check_dependency_guard_valid(self, tmp_path: Path) -> None:
        v = CodeValidator()
        main = tmp_path / "main.py"
        helper = tmp_path / "helper.py"
        main.write_text("import helper\n", encoding="utf-8")
        helper.write_text("x = 1\n", encoding="utf-8")
        result = v.check_dependency_guard(main, [main, helper])
        assert result.valid is True

    def test_check_dependency_guard_nonexistent_file(self, tmp_path: Path) -> None:
        v = CodeValidator()
        f = tmp_path / "nonexistent.py"
        result = v.check_dependency_guard(f, [])
        assert result.valid is False


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_merge_valid_results(self) -> None:
        r1 = ValidationResult(valid=True, imports=["os"])
        r2 = ValidationResult(valid=True, imports=["sys"])
        merged = r1.merge(r2)
        assert merged.valid is True
        assert "os" in merged.imports
        assert "sys" in merged.imports

    def test_merge_invalid_result(self) -> None:
        r1 = ValidationResult(valid=True)
        r2 = ValidationResult(valid=False, errors=["error"])
        merged = r1.merge(r2)
        assert merged.valid is False
        assert "error" in merged.errors

    def test_default_factory(self) -> None:
        r = ValidationResult(valid=True)
        assert r.errors == []
        assert r.warnings == []
        assert r.imports == []
        assert r.symbols == []
