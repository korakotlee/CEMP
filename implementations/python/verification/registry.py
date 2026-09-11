"""Pluggable syntax verification registry and result data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from verification.node_checker import NodeChecker
from verification.python_checker import PythonChecker


@dataclass
class SyntaxResult:
    """Standardized syntax verification result conforming to protocol/schemas/syntax_check.json."""

    valid: bool
    checker_used: str
    errors: list[str] = field(default_factory=list)


class VerificationRegistry:
    """Maps file extensions and language identifiers to language syntax checkers."""

    def __init__(self) -> None:
        self._python_checker = PythonChecker()
        self._node_checker = NodeChecker()

    def check(self, file_path: Path | str, language: Optional[str] = None) -> SyntaxResult:
        """Run syntax verification against a file based on language or extension.

        Args:
            file_path: Path to file to validate.
            language: Optional explicit language identifier.

        Returns:
            SyntaxResult with validity flag and any diagnostic errors.
        """
        path = Path(file_path)
        ext = path.suffix.lower()
        lang = language.lower() if language else None

        if lang == "python" or ext == ".py":
            return self._python_checker.check(path)

        if lang in ("javascript", "js") or ext in (".js", ".mjs", ".cjs"):
            return self._node_checker.check(path)

        # Non-code or unsupported languages pass through with checker_used="none"
        return SyntaxResult(valid=True, checker_used="none", errors=[])


_DEFAULT_REGISTRY: Optional[VerificationRegistry] = None


def get_verification_registry() -> VerificationRegistry:
    """Retrieve or initialize the singleton VerificationRegistry."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = VerificationRegistry()
    return _DEFAULT_REGISTRY
