"""Reusable test fixtures for CEMP Python implementation conformance tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

import pytest
from jsonschema import Draft202012Validator


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Create an isolated, initialized git repository for file editing tests."""
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "CEMP Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@cemp.dev"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit so HEAD exists
    init_file = tmp_path / "README.md"
    init_file.write_text("# CEMP Test Repository\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


@pytest.fixture(scope="session")
def protocol_dir() -> Path:
    """Locate protocol schemas directory dynamically from workspace root."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        schemas_path = parent / "protocol" / "schemas"
        if schemas_path.is_dir():
            return parent / "protocol"
    raise FileNotFoundError("Could not locate protocol/schemas directory from test location")


@pytest.fixture(scope="session")
def schema_validator(protocol_dir: Path) -> Callable[[str, dict[str, Any]], None]:
    """Provide a schema validator loading JSON Schema Draft 2020-12 specifications."""
    schemas_dir = protocol_dir / "schemas"
    schemas: dict[str, dict[str, Any]] = {}

    for schema_file in schemas_dir.glob("*.json"):
        with schema_file.open("r", encoding="utf-8") as f:
            schemas[schema_file.stem] = json.load(f)
            schemas[schema_file.name] = schemas[schema_file.stem]

    def _run_validate(subschema: dict[str, Any], inst: dict[str, Any]) -> None:
        try:
            Draft202012Validator(subschema).validate(inst)
        except AttributeError:
            from jsonschema import Draft7Validator

            Draft7Validator(subschema).validate(inst)

    def validate(schema_name: str, instance: dict[str, Any], target: str | None = None) -> None:
        key = schema_name.removesuffix(".json")
        if "/" in key:
            main_key, def_key = key.split("/", 1)
            if main_key not in schemas:
                raise KeyError(
                    f"Schema '{main_key}' not found. Available schemas: {sorted(schemas.keys())}"
                )
            schema_def = schemas[main_key].get("definitions", {}).get(def_key, {})
            if not schema_def:
                raise KeyError(f"Definition '{def_key}' not found in schema '{main_key}'")
        else:
            if key not in schemas:
                raise KeyError(
                    f"Schema '{schema_name}' not found. Available schemas: {sorted(schemas.keys())}"
                )
            schema_def = schemas[key]

        if target:
            if target not in schema_def.get("properties", {}):
                raise KeyError(f"Target '{target}' not in schema '{schema_name}' properties")
            subschema = schema_def["properties"][target]
            _run_validate(subschema, instance)
        elif "parameters" in schema_def.get("properties", {}):
            # Default to parameters validation if instance matches parameter shape
            _run_validate(schema_def["properties"]["parameters"], instance)
        else:
            _run_validate(schema_def, instance)

    return validate


@pytest.fixture(autouse=True)
def clean_global_tx_state():
    """Reset transaction manager before and after tests across suite."""
    from core.transactions import reset_transaction_manager

    reset_transaction_manager()
    yield
    reset_transaction_manager()


@pytest.fixture
def server_instance():
    """Provide the initialized FastMCP CEMP server instance."""
    from server import mcp_server

    return mcp_server
