"""JavaScript syntax verification checker using Node.js runtime."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from verification.registry import SyntaxResult


class NodeChecker:
    """Verifies JavaScript file syntax via `node --check` when Node is available."""

    def __init__(self) -> None:
        self._node_path = shutil.which("node")

    def check(self, file_path: Path | str) -> SyntaxResult:
        """Validate JavaScript syntax via node --check.

        Args:
            file_path: Path to JavaScript file.

        Returns:
            SyntaxResult indicating validity and any syntax diagnostics.
        """
        from verification.registry import SyntaxResult

        if not self._node_path:
            # Graceful degradation if Node is not installed
            return SyntaxResult(valid=True, checker_used="none", errors=[])

        target = Path(file_path).resolve()
        try:
            res = subprocess.run(
                [self._node_path, "--check", str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                return SyntaxResult(valid=True, checker_used="node", errors=[])

            err_output = res.stderr.strip() or res.stdout.strip()
            return SyntaxResult(
                valid=False,
                checker_used="node",
                errors=[err_output] if err_output else ["Syntax verification failed"],
            )
        except OSError as exc:
            return SyntaxResult(valid=False, checker_used="node", errors=[str(exc)])
