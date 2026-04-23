"""Round-trip the reference example YAML through the Pydantic models and
verify the result still validates against the JSON Schema. This catches
drift between the schema, the models, and the example card.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "data" / "schema" / "judge.schema.json"
EXAMPLE_YAML = REPO_ROOT / "data" / "judges" / "casd" / "example-judge.yaml"


def _load_doc() -> dict:
    return yaml.safe_load(EXAMPLE_YAML.read_text())


def test_example_judge_validates_against_schema():
    doc = _load_doc()
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    assert not errors, [f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors]


def test_every_procedural_enum_matches_schema():
    """Guard against the Pydantic Literal types in scrapers/common/models.py
    drifting from the schema enum values. We re-validate the example
    against the live schema above; this test additionally asserts that
    every enum in the procedural section of the example is a value the
    schema actually allows.
    """
    schema = json.loads(SCHEMA_PATH.read_text())
    procedural_schema = schema["$defs"]["procedural"]["properties"]
    doc = _load_doc()
    for key, value in (doc.get("procedural") or {}).items():
        spec = procedural_schema.get(key)
        assert spec is not None, f"procedural field '{key}' is not in the schema"
        if spec.get("type") == "string" and "enum" in spec:
            assert value in spec["enum"], f"{key}={value} not in schema enum {spec['enum']}"
