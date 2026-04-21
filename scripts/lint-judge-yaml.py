"""Judge YAML linter for The Well.

Validates every data/judges/**/*.yaml against data/schema/judge.schema.json
and cross-checks data/schema/fields.yaml against the schema for enum
consistency. Exits 0 on success, 1 on any failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "data" / "schema" / "judge.schema.json"
FIELDS_PATH = REPO_ROOT / "data" / "schema" / "fields.yaml"
JUDGES_ROOT = REPO_ROOT / "data" / "judges"


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def load_fields_yaml() -> dict:
    with FIELDS_PATH.open() as f:
        return yaml.safe_load(f)


def find_yaml_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.yaml") if p.is_file())


def validate_against_schema(path: Path, schema: dict) -> tuple[dict | None, list[str]]:
    try:
        with path.open() as f:
            doc = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return None, [f"YAML parse error: {e}"]

    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"{loc}: {err.message}")
    return doc, errors


def schema_enum_for_property(spec: dict) -> list[str] | None:
    """Return the enum list for a procedural property, or None if not an enum."""
    if spec.get("type") == "string" and "enum" in spec:
        return list(spec["enum"])
    if spec.get("type") == "array":
        items = spec.get("items", {})
        if items.get("type") == "string" and "enum" in items:
            return list(items["enum"])
    return None


def cross_check_enums(schema: dict, fields: dict) -> list[str]:
    """Bidirectional consistency check between schema and fields.yaml."""
    errors: list[str] = []
    procedural_props: dict = schema["$defs"]["procedural"]["properties"]
    fields_map: dict = fields.get("fields") or {}

    for fk, spec in procedural_props.items():
        if fk not in fields_map:
            errors.append(
                f"fields.yaml is missing entry for procedural field '{fk}'"
            )
            continue

        schema_enum = schema_enum_for_property(spec)
        entry = fields_map[fk]
        entry_values = entry.get("values")

        if schema_enum is None:
            # Numeric field. fields.yaml should not declare values.
            if entry_values is not None:
                errors.append(
                    f"fields.yaml '{fk}' declares values but schema has no enum"
                )
            continue

        if entry_values is None:
            errors.append(
                f"fields.yaml '{fk}' is missing 'values' "
                f"(schema enum: {schema_enum})"
            )
            continue

        entry_list = [str(v) for v in entry_values]
        if entry_list != schema_enum:
            errors.append(
                f"fields.yaml '{fk}' values {entry_list} do not match "
                f"schema enum {schema_enum}"
            )

    for fk in fields_map:
        if fk not in procedural_props:
            errors.append(
                f"fields.yaml has entry '{fk}' that is not a procedural field in the schema"
            )

    return errors


def warn_missing_sources(doc: dict) -> list[str]:
    procedural = doc.get("procedural") or {}
    sources = doc.get("sources") or []
    sourced = {s.get("field_key") for s in sources if isinstance(s, dict)}
    return [
        f"procedural.{fk} is set but has no entry in sources[]"
        for fk in procedural
        if fk not in sourced
    ]


def warn_orphan_standing_orders(doc: dict) -> list[str]:
    standing_orders = doc.get("standing_orders") or []
    sources = doc.get("sources") or []
    referenced = {
        s.get("source_url")
        for s in sources
        if isinstance(s, dict) and s.get("source_type") == "standing_order"
    }
    warnings: list[str] = []
    for so in standing_orders:
        url = so.get("url") if isinstance(so, dict) else None
        if url not in referenced:
            title = so.get("title", "?") if isinstance(so, dict) else "?"
            warnings.append(
                f"standing_order '{title}' ({url!r}) is not referenced by "
                "any source of type 'standing_order'"
            )
    return warnings


@click.command()
@click.option(
    "--path",
    type=click.Path(exists=True, path_type=Path),
    help="Lint a single YAML file instead of the full tree.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings (missing sources, orphan standing orders) as failures.",
)
def main(path: Path | None, strict: bool) -> None:
    schema = load_schema()
    fields = load_fields_yaml()

    enum_errors = cross_check_enums(schema, fields)

    if path is not None:
        paths = [path]
    else:
        paths = find_yaml_files(JUDGES_ROOT)

    file_errors: dict[Path, list[str]] = {}
    file_warnings: dict[Path, list[str]] = {}

    for p in paths:
        doc, errs = validate_against_schema(p, schema)
        if errs:
            file_errors[p] = errs
        if doc is not None and not errs:
            warnings = warn_missing_sources(doc) + warn_orphan_standing_orders(doc)
            if warnings:
                file_warnings[p] = warnings

    total_file_errors = sum(len(v) for v in file_errors.values())
    total_warnings = sum(len(v) for v in file_warnings.values())

    if enum_errors:
        click.echo("Enum consistency errors (schema vs. fields.yaml):", err=True)
        for e in enum_errors:
            click.echo(f"  {e}", err=True)

    def display(p: Path) -> str:
        try:
            return str(p.relative_to(REPO_ROOT))
        except ValueError:
            return str(p)

    for p, errs in file_errors.items():
        click.echo(f"\n{display(p)} — {len(errs)} error(s):", err=True)
        for e in errs:
            click.echo(f"  {e}", err=True)

    for p, warnings in file_warnings.items():
        click.echo(f"\n{display(p)} — {len(warnings)} warning(s):", err=True)
        for w in warnings:
            click.echo(f"  {w}", err=True)

    click.echo(
        f"\nSummary: {len(paths)} file(s) checked, "
        f"{len(enum_errors)} enum error(s), "
        f"{total_file_errors} schema error(s), "
        f"{total_warnings} warning(s)."
    )

    failed = bool(enum_errors) or total_file_errors > 0
    if strict and total_warnings > 0:
        failed = True

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
