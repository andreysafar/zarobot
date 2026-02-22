"""Tests for Ия (IA) personality."""

import json
from pathlib import Path

import pytest


BASE = Path(__file__).resolve().parent.parent


def test_manifest_valid():
    manifest = json.loads((BASE / "manifest.json").read_text())
    assert manifest["schema_version"] == "1.0"
    assert manifest["name"] == "ia"
    assert manifest["is_default"] is True


def test_system_prompt_exists_and_long_enough():
    text = (BASE / "prompts" / "system.txt").read_text().strip()
    assert len(text) > 500, f"System prompt too short: {len(text)} chars"


def test_system_free_prompt_exists():
    text = (BASE / "prompts" / "system_free.txt").read_text().strip()
    assert len(text) > 300


def test_greeting_has_placeholders():
    text = (BASE / "prompts" / "greeting.txt").read_text()
    assert "{user_name}" in text


def test_fallback_exists():
    text = (BASE / "prompts" / "fallback.txt").read_text().strip()
    assert len(text) > 10


def test_training_examples_count():
    lines = (BASE / "training" / "examples.jsonl").read_text().strip().splitlines()
    examples = [json.loads(line) for line in lines if line.strip()]
    assert len(examples) >= 5, f"Need at least 5 examples, got {len(examples)}"
    for ex in examples:
        assert "user" in ex and "bot" in ex


def test_all_prompt_files_referenced_in_manifest():
    manifest = json.loads((BASE / "manifest.json").read_text())
    for key, path in manifest["prompts"].items():
        full = BASE / path
        assert full.exists(), f"Prompt file missing: {path}"


def test_context_agent_prompt():
    text = (BASE / "prompts" / "context_agent.txt").read_text().strip()
    assert "mini_chat" in text
    assert "JSON" in text


def test_profile_agent_prompt():
    text = (BASE / "prompts" / "profile_agent.txt").read_text().strip()
    assert "PROFILE" in text


def test_summary_agent_prompt():
    text = (BASE / "prompts" / "summary_agent.txt").read_text().strip()
    assert "SUMMARY" in text
