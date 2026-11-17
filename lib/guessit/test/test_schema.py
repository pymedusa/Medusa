#!/usr/bin/env python
"""Tests for the machine-readable property schema."""

from __future__ import annotations

import functools
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

import yaml

from guessit import GUESSIT_SCHEMA, api
from guessit.yamlutils import OrderedDictYAMLLoader

ROOT = Path(__file__).resolve().parent.parent.parent
TEST_DIR = ROOT / "guessit" / "test"
OUTPUT_SCHEMA_JSON = ROOT / "guessit" / "data" / "output-schema.json"


def _corpus_inputs() -> list[str]:
    """Every input string from the YAML corpus, token prefixes stripped."""
    token_prefix = re.compile(r"^[ +-]+")
    inputs: list[str] = []
    for path in sorted(TEST_DIR.rglob("*.yml")) + sorted(TEST_DIR.rglob("*.yaml")):
        with open(path, encoding="utf-8") as stream:
            data = yaml.load(stream, OrderedDictYAMLLoader)
        if not isinstance(data, dict):
            continue
        for key in data:
            text = key if isinstance(key, str) else str(key)
            inputs.append(token_prefix.sub("", text))
    return inputs


@functools.lru_cache(maxsize=1)
def _load_generator() -> Any:
    """Import scripts/gen_schema.py (a standalone script, not an installed module)."""
    spec = importlib.util.spec_from_file_location("gen_schema", ROOT / "scripts" / "gen_schema.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.lru_cache(maxsize=1)
def _corpus_guesses() -> tuple[tuple[str, dict[str, Any]], ...]:
    """Guess every corpus input once; reused across the corpus-sweep tests."""
    results: list[tuple[str, dict[str, Any]]] = []
    for string in _corpus_inputs():
        try:
            results.append((string, api.guessit(string)))
        except Exception:  # a single bad input must not abort the sweep
            continue
    return tuple(results)


@functools.lru_cache(maxsize=1)
def _built_schema() -> Any:
    """Run the generator once; reused across the drift tests."""
    return _load_generator().build_schema()


def test_properties_advertises_every_schema_property() -> None:
    props = api.properties()
    for name in GUESSIT_SCHEMA:
        assert name in props, f"properties() missing {name}"
    assert len(props) == len(GUESSIT_SCHEMA)


def test_value_constrained_properties_expose_a_non_empty_enum() -> None:
    assert "Blu-ray" in GUESSIT_SCHEMA["source"]["enum"]
    assert GUESSIT_SCHEMA["type"]["enum"] == ["episode", "movie"]
    assert "H.264" in GUESSIT_SCHEMA["video_codec"]["enum"]
    assert "Web" in api.properties()["source"]


def test_enums_are_code_complete() -> None:
    # These source values are declared in the rules but absent from the corpus;
    # the enum must still list them (introspection-driven completeness).
    for value in ["Workprint", "Telecine", "Telesync", "Pay-per-view", "Video on Demand"]:
        assert value in GUESSIT_SCHEMA["source"]["enum"], f"source enum missing {value}"


def test_every_emitted_property_is_in_the_schema() -> None:
    unknown: set[str] = set()
    for _string, guess in _corpus_guesses():
        unknown.update(key for key in guess if key not in GUESSIT_SCHEMA)
    assert not unknown, f"emitted properties absent from schema: {sorted(unknown)}"


def test_every_emitted_enum_value_is_allowed() -> None:
    violations: list[str] = []
    for string, guess in _corpus_guesses():
        for key, value in guess.items():
            spec = GUESSIT_SCHEMA.get(key)
            enum = spec.get("enum") if spec else None
            if not enum:
                continue
            for item in value if isinstance(value, list) else [value]:
                if isinstance(item, str | int) and not isinstance(item, bool) and item not in enum:
                    violations.append(f"{key}={item!r} ({string[:60]})")
    assert not violations, f"emitted values not in schema enum: {violations[:10]}"


def test_output_schema_json_is_draft07_describing_all_properties() -> None:
    with open(OUTPUT_SCHEMA_JSON, encoding="utf-8") as stream:
        output_schema = json.load(stream)
    assert "draft-07" in output_schema["$schema"]
    for name in GUESSIT_SCHEMA:
        assert name in output_schema["properties"], f"JSON schema missing {name}"


def test_schema_py_is_not_stale() -> None:
    """guessit/schema.py must match what scripts/gen_schema.py produces."""
    assert _built_schema() == GUESSIT_SCHEMA


def test_output_schema_json_is_not_stale() -> None:
    """guessit/data/output-schema.json must match the generator output."""
    expected = _load_generator().build_json_schema(_built_schema())
    with open(OUTPUT_SCHEMA_JSON, encoding="utf-8") as stream:
        committed = json.load(stream)
    assert committed == expected
