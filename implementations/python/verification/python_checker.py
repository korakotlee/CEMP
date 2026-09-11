"""Python syntax verification checker using standard library py_compile."""

from __future__ import annotations

import py_compile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verification.registry import SyntaxResult


class PythonChecker:
    """Verifies Python source code syntax in sub-millisecond execution time."""

    def check(self, file_path: Path | str) -> SyntaxResult:
        """Validate Python syntax via py_compile.compile.

        Args:
            file_path: Path to the Python file to validate.

        Returns:
            SyntaxResult indicating validity and any syntax errors.
        """
        from verification.registry import SyntaxResult

        path_str = str(Path(file_path).resolve())
        try:
            py_compile.compile(path_str, doraise=True)
            return SyntaxResult(valid=True, checker_used="py_compile", errors=[])
        except py_compile.PyCompileError as exc:
            msg = exc.msg if hasattr(exc, "msg") and exc.msg else str(exc)
            return SyntaxResult(valid=False, checker_used="py_compile", errors=[msg])
        except SyntaxError as exc:
            return SyntaxResult(valid=False, checker_used="py_compile", errors=[str(exc)])
