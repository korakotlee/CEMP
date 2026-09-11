"""Tests for syntax verification registry and language checkers."""

import shutil
from pathlib import Path

from verification.node_checker import NodeChecker
from verification.python_checker import PythonChecker
from verification.registry import VerificationRegistry


def test_python_checker_valid_syntax(tmp_path: Path):
    """Python checker should pass cleanly for syntactically correct Python code."""
    py_file = tmp_path / "valid.py"
    py_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    checker = PythonChecker()
    result = checker.check(py_file)
    assert result.valid is True
    assert result.checker_used == "py_compile"
    assert result.errors == []


def test_python_checker_syntax_error(tmp_path: Path):
    """Python checker should detect syntax errors and return compiler error message."""
    py_file = tmp_path / "broken.py"
    py_file.write_text("def broken(\n", encoding="utf-8")

    checker = PythonChecker()
    result = checker.check(py_file)
    assert result.valid is False
    assert result.checker_used == "py_compile"
    assert len(result.errors) > 0
    assert any("SyntaxError" in err or "was never closed" in err for err in result.errors)


def test_node_checker_valid_and_invalid(tmp_path: Path):
    """Node checker should validate JS files if node is available or skip gracefully."""
    checker = NodeChecker()
    js_valid = tmp_path / "valid.js"
    js_valid.write_text("const x = 42;\nconsole.log(x);\n", encoding="utf-8")

    result_valid = checker.check(js_valid)
    if shutil.which("node"):
        assert result_valid.valid is True
        assert result_valid.checker_used == "node"

        js_broken = tmp_path / "broken.js"
        js_broken.write_text("const x = ;\n", encoding="utf-8")
        result_broken = checker.check(js_broken)
        assert result_broken.valid is False
        assert len(result_broken.errors) > 0
    else:
        assert result_valid.valid is True
        assert result_valid.checker_used == "none"


def test_registry_routing(tmp_path: Path):
    """VerificationRegistry should route by file extension and passthrough unsupported types."""
    registry = VerificationRegistry()

    # Python routing
    py_file = tmp_path / "test.py"
    py_file.write_text("x = 10\n", encoding="utf-8")
    res_py = registry.check(py_file)
    assert res_py.valid is True
    assert res_py.checker_used == "py_compile"

    # Unsupported extension (e.g. markdown)
    md_file = tmp_path / "notes.md"
    md_file.write_text("# Notes\nSome content\n", encoding="utf-8")
    res_md = registry.check(md_file)
    assert res_md.valid is True
    assert res_md.checker_used == "none"
    assert res_md.errors == []
